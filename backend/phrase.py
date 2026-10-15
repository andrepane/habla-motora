"""7A: manually delimited/reviewed phrase. No acoustic content inference."""
import copy
import hashlib
import io
import json
import struct
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_BYTES = (ROOT / 'configs/phrase_7a_v1.json').read_bytes()
CONFIG = json.loads(CONFIG_BYTES)
MAX_BYTES = CONFIG['max_bytes']
EVENTS = {'omission', 'repetition', 'substitution', 'fragment', 'restart', 'addition',
          'filled_pause', 'uncertain'}
MATCHES = {'pending', 'exact_once', 'different', 'uncertain'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode()


def measure(value=None, reason=None, **extra):
    return {'value': value, 'reason': reason, **extra}


def read_wav(data):
    """Independent limits: do not reuse/modify the 15 s DDK reader."""
    if not data or len(data) > MAX_BYTES:
        raise ValueError('Frase admite de 1 a 4.000.000 bytes.')
    if len(data) < 44 or data[:4] != b'RIFF' or data[8:12] != b'WAVE' or int.from_bytes(data[4:8], 'little') + 8 != len(data):
        raise ValueError('Cabecera RIFF/WAV incompleto o incoherente.')
    position = 12
    fmt = None
    data_size = None
    while position + 8 <= len(data):
        kind = data[position:position+4]
        size = int.from_bytes(data[position+4:position+8], 'little')
        at = position + 8
        if at + size > len(data):
            raise ValueError('Chunk WAV truncado.')
        if kind == b'fmt ':
            if fmt is not None or size < 16:
                raise ValueError('Formato WAV ambiguo.')
            fmt = struct.unpack_from('<HHIIHH', data, at)
        if kind == b'data':
            if data_size is not None:
                raise ValueError('Datos WAV ambiguos.')
            data_size = size
        position = at + size + size % 2
    if fmt is None or data_size is None:
        raise ValueError('Formato o datos WAV ausentes.')
    encoding, channels, rate, byte_rate, alignment, bits = fmt
    if (encoding != 1 or channels != 1 or bits not in CONFIG['pcm_bits']
            or rate not in CONFIG['sample_rates'] or alignment != bits // 8
            or byte_rate != rate * alignment or data_size % alignment):
        raise ValueError('Cabecera PCM mono incoherente o no admitida.')
    try:
        with wave.open(io.BytesIO(data), 'rb') as w:
            rate, width, channels, n = w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getnframes()
            if (rate not in CONFIG['sample_rates'] or width * 8 not in CONFIG['pcm_bits']
                    or channels != 1 or w.getcomptype() != 'NONE' or not n):
                raise ValueError('Se necesita WAV mono PCM16/24/32 a 44.100/48.000 Hz.')
            if n > CONFIG['max_duration_s'] * rate:
                raise ValueError('Frase admite hasta 20 segundos.')
            raw = w.readframes(n)
            if len(raw) != n * width:
                raise ValueError('WAV truncado.')
    except (wave.Error, EOFError) as exc:
        raise ValueError('WAV PCM inválido.') from exc
    return {'sample_rate_hz': rate, 'pcm_bits': width * 8, 'channels': channels,
            'sample_count': n, 'duration_s': n / rate, 'byte_count': len(data)}


def validate_context(context, wav):
    fields = {'phrase_id', 'modality', 'attempt', 'selection', 'selection_confirmed',
              'recording_limit_reached', 'administration'}
    if not isinstance(context, dict) or set(context) - fields:
        raise ValueError('Contexto de frase inválido.')
    c = copy.deepcopy(context)
    if c.get('phrase_id') != CONFIG['stimulus']['id']:
        raise ValueError('Identificador de frase no admitido.')
    if c.get('modality') not in CONFIG['modalities']:
        raise ValueError('Modalidad no admitida.')
    if type(c.get('attempt')) is not int or c['attempt'] not in (1, 2):
        raise ValueError('Intento debe ser 1 o 2.')
    for name in ('selection_confirmed', 'recording_limit_reached'):
        if type(c.get(name)) is not bool:
            raise ValueError(f'{name} debe ser booleano.')
    selection = c.get('selection')
    if selection is not None:
        if (not isinstance(selection, dict) or set(selection) != {'start_sample', 'end_sample_exclusive'}
                or any(type(v) is not int for v in selection.values())
                or not 0 <= selection['start_sample'] < selection['end_sample_exclusive'] <= wav['sample_count']):
            raise ValueError('Selección inválida: índices enteros [inicio, fin).')
    elif c['selection_confirmed']:
        raise ValueError('No se puede confirmar una selección ausente.')
    admin = c.get('administration')
    if not isinstance(admin, dict) or set(admin) - {'model_id', 'model_sha256', 'model_presented_confirmed', 'notes'}:
        raise ValueError('Administración inválida.')
    if len(canonical(admin)) > 5000:
        raise ValueError('Administración demasiado grande.')
    if c['modality'] != 'direct_reading_v1':
        sha = admin.get('model_sha256', '')
        if (not isinstance(admin.get('model_id'), str) or not admin['model_id'].strip()
                or not isinstance(sha, str) or len(sha) != 64 or any(x not in '0123456789abcdef' for x in sha)
                or admin.get('model_presented_confirmed') is not True):
            raise ValueError('La variante auditiva requiere identificar y confirmar el modelo presentado.')
    elif admin.get('model_id') or admin.get('model_sha256') or admin.get('model_presented_confirmed'):
        raise ValueError('Lectura directa no debe contener modelo auditivo.')
    return c


def validate_review(review, context_sha):
    if review is None:
        return None
    allowed = {'context_sha256', 'confirmed', 'production', 'target_match', 'word_count',
               'syllable_count', 'events', 'notes'}
    if not isinstance(review, dict) or set(review) != allowed:
        raise ValueError('Revisión inválida o incompleta.')
    if review['context_sha256'] != context_sha:
        raise ValueError('Revisión desactualizada: WAV, límites, frase, modalidad o intento diferentes.')
    if type(review['confirmed']) is not bool:
        raise ValueError('Confirmación de revisión inválida.')
    if review['production'] not in ('pending', 'present', 'absent') or not isinstance(review['target_match'], str) or review['target_match'] not in MATCHES:
        raise ValueError('Estado de contenido inválido.')
    for key in ('word_count', 'syllable_count'):
        count = review[key]
        if not isinstance(count, dict) or set(count) != {'value', 'confirmed'} or type(count['confirmed']) is not bool:
            raise ValueError('Recuento inválido.')
        value = count['value']
        if value is not None and (type(value) is not int or not 0 <= value <= 10000):
            raise ValueError('Recuento debe ser entero no negativo, nunca NaN, infinito o booleano.')
        if count['confirmed'] and value is None:
            raise ValueError('Un recuento confirmado requiere valor explícito.')
    if not isinstance(review['events'], list) or len(review['events']) > 1000:
        raise ValueError('Lista de acontecimientos inválida.')
    ids = set()
    for event in review['events']:
        if (not isinstance(event, dict) or set(event) != {'id', 'type', 'note'}
                or not isinstance(event['id'], str) or not event['id'] or event['id'] in ids
                or not isinstance(event['type'], str) or event['type'] not in EVENTS or not isinstance(event['note'], str)):
            raise ValueError('Acontecimiento inválido o duplicado.')
        ids.add(event['id'])
    if not isinstance(review['notes'], str):
        raise ValueError('Notas inválidas.')
    if review['target_match'] == 'exact_once':
        if review['production'] != 'present' or review['events']:
            raise ValueError('Coincidencia exacta incompatible con ausencia o desviaciones.')
        if review['word_count']['confirmed'] and review['word_count']['value'] != CONFIG['stimulus']['canonical_words']:
            raise ValueError('Coincidencia textual exacta incompatible con recuento de palabras.')
    if review['production'] == 'absent':
        if any(review[k]['value'] not in (None, 0) for k in ('word_count', 'syllable_count')) or review['events']:
            raise ValueError('Ausencia incompatible con recuentos positivos o acontecimientos.')
    return copy.deepcopy(review)


def calculate(duration, context, review):
    """Pure arithmetic from separately confirmed manual statements, never from audio."""
    selection_ready = duration is not None and context['selection_confirmed']
    reviewed = review is not None and review['confirmed']
    production = review['production'] if reviewed else 'pending'
    match = review['target_match'] if reviewed else 'pending'
    general = ('selection_unconfirmed' if not selection_ready else
               'pending_content_review' if not reviewed or production == 'pending' else
               'no_production' if production == 'absent' else None)
    reference_reason = (general or ('recording_limit_reached' if context['recording_limit_reached'] else
                                   'target_mismatch' if match == 'different' else
                                   'target_match_uncertain' if match == 'uncertain' else
                                   'pending_content_review' if match == 'pending' else None))
    rates = {}
    for kind, unit, scale, reference_count in (('word', 'words/min', 60, CONFIG['stimulus']['canonical_words']), ('syllable', 'syllables/s', 1, CONFIG['stimulus']['canonical_syllables'])):
        rates[f'reference_{kind}_rate'] = measure(
            None if reference_reason else reference_count * scale / duration,
            reference_reason, unit=unit, numerator=reference_count,
            count_basis='versioned_stimulus_not_acoustic_detection', denominator_s=duration)
        count = review[f'{kind}_count'] if review else {'value': None, 'confirmed': False}
        reason = general or (f'{kind}_count_unconfirmed' if not count['confirmed'] else None)
        rates[f'reviewed_{kind}_rate'] = measure(
            None if reason else count['value'] * scale / duration, reason,
            unit=unit, numerator=count['value'] if count['confirmed'] else None,
            count_basis='manual_production_count', denominator_s=duration)
    return rates


def analyze_phrase(data, context, review=None, expected_file_sha256=None):
    wav = read_wav(data)
    c = validate_context(context, wav)
    file_sha = digest(data)
    if review is not None and expected_file_sha256 != file_sha:
        raise ValueError('Hash WAV de revisión incorrecto.')
    identity = {'file_sha256': file_sha, 'context': c, 'config_sha256': digest(CONFIG_BYTES)}
    context_sha = digest(canonical(identity))
    r = validate_review(review, context_sha)
    selection = c['selection']
    duration = ((selection['end_sample_exclusive'] - selection['start_sample']) / wav['sample_rate_hz']
                if selection is not None else None)
    rates = calculate(duration, c, r)
    count = sum(x['value'] is not None for x in rates.values())
    selection_status = 'not_requested' if selection is None else 'completed' if c['selection_confirmed'] else 'draft'
    calculation_status = 'blocked' if selection_status != 'completed' else 'completed' if count == 4 else 'partial'
    reviewed_present = r and r['confirmed'] and r['production'] == 'present' and c['selection_confirmed']
    return {
        'schema_version': 'phrase_output_v1', 'protocol_version': CONFIG['protocol_version'],
        'status': 'completed' if calculation_status == 'completed' else 'partial',
        'stages': {'selection': {'status': selection_status},
                   'review': {'status': 'not_requested' if r is None else 'completed' if r['confirmed'] else 'draft'},
                   'calculation': {'status': calculation_status}},
        'stimulus': copy.deepcopy(CONFIG['stimulus']), 'context': c,
        'input': wav, 'selection': copy.deepcopy(selection),
        'selected_duration_s': measure(duration, 'selection_not_requested' if duration is None else None),
        'production_duration_s': measure(duration if reviewed_present else None,
                                       None if reviewed_present else 'no_production' if r and r['confirmed'] and r['production'] == 'absent' else 'pending_content_review'),
        'rates': rates, 'review': r,
        'out_of_scope': {k: measure(reason='not_implemented') for k in
                         ('pause_count', 'pause_duration_s', 'speech_time_s', 'articulation_rate')},
        'provenance': {**identity, 'context_sha256': context_sha,
                       'engine_sha256': digest(Path(__file__).read_bytes()),
                       'review_sha256': digest(canonical(r)) if r is not None else None},
        'audit': {'original_wav_preserved': True, 'acoustic_content_inference': False,
                  'duration_definition': '(end_sample_exclusive - start_sample) / sample_rate_hz; internal pauses retained',
                  'reference_match_definition': 'manual exact lexical sequence once; not phonetic matching',
                  'reviewed_words': 'complete orthographic lexical tokens; repetitions included; fragments excluded',
                  'reviewed_syllables': 'manually confirmed produced syllables including fragments/repetitions/filled-pause syllables',
                  'human_validation': 'pending',
                  'reading_confound': 'Reading/decoding and visual tracking may affect timing; not a pure motor measure',
                  'attempt_aggregation': 'none; modalities/model identities/attempts are never pooled'},
        'warnings': ['TECHNICAL_VALIDATION_ONLY_HUMAN_VALIDATION_PENDING'] +
                    (['RECORDING_LIMIT_REACHED_REFERENCE_RATES_BLOCKED'] if c['recording_limit_reached'] else [])
    }
