"""7B.1: manual temporal review; independent of 7A arithmetic and acoustic engines."""
import copy
import json
from pathlib import Path
from backend.phrase import ROOT, analyze_phrase, canonical, digest, measure

CONFIG_BYTES = (ROOT / 'configs/phrase_pause_review_v1.json').read_bytes()
CONFIG = json.loads(CONFIG_BYTES)
DEPENDENCIES = ('file_sha256', 'context_sha256', 'review_sha256', 'config_sha256', 'engine_sha256')
METRICS = ('pause_duration_s', 'operational_speech_time_s', 'pause_percent', 'pause_count',
           'pause_mean_duration_s', 'pause_median_duration_s',
           'reviewed_syllable_articulation_rate', 'reviewed_word_articulation_rate')


def source_dependencies(source):
    return {k: source['provenance'][k] for k in DEPENDENCIES}


def validate_temporal(temporal, source):
    required = {'protocol_version', 'source_dependencies', 'status', 'reviewed_all', 'note', 'intervals'}
    if not isinstance(temporal, dict) or set(temporal) != required:
        raise ValueError('Revisión temporal incompleta.')
    if temporal['protocol_version'] != CONFIG['protocol_version']:
        raise ValueError('Protocolo temporal no admitido.')
    if temporal['source_dependencies'] != source_dependencies(source):
        raise ValueError('stale_dependency: WAV, selección o revisión 7A diferentes.')
    if temporal['status'] not in ('not_started', 'draft', 'confirmed', 'not_evaluable'):
        raise ValueError('Estado temporal inválido.')
    if type(temporal['reviewed_all']) is not bool or not isinstance(temporal['note'], str):
        raise ValueError('Confirmación temporal inválida.')
    if temporal['status'] == 'confirmed' and not temporal['reviewed_all']:
        raise ValueError('Confirmar exige revisar toda la selección.')
    if temporal['status'] == 'not_evaluable' and not temporal['note'].strip():
        raise ValueError('Indica el motivo de no evaluable.')
    intervals = temporal['intervals']
    if not isinstance(intervals, list) or len(intervals) > 1000:
        raise ValueError('Intervalos temporales inválidos.')
    if temporal['status'] == 'not_started' and (intervals or temporal['reviewed_all']):
        raise ValueError('Una revisión iniciada debe estar en borrador.')
    selection = source['selection']
    rate = source['input']['sample_rate_hz']
    ids, accepted = set(), []
    for event in intervals:
        fields = {'id', 'start_sample', 'end_sample_exclusive', 'classification', 'breath_present',
                  'within_word', 'nonarticulatory_confirmed', 'note'}
        if not isinstance(event, dict) or set(event) != fields:
            raise ValueError('Anotación temporal inválida.')
        if not isinstance(event['id'], str) or not event['id'] or event['id'] in ids:
            raise ValueError('Identificador temporal vacío o duplicado.')
        ids.add(event['id'])
        a, b = event['start_sample'], event['end_sample_exclusive']
        if (selection is None or type(a) is not int or type(b) is not int
                or not selection['start_sample'] < a < b < selection['end_sample_exclusive']):
            raise ValueError('Intervalo interno inválido: usa índices absolutos enteros [inicio, fin).')
        kind = event['classification']
        if not isinstance(kind, str) or kind not in CONFIG['classification']:
            raise ValueError('Clasificación temporal inválida.')
        if event['breath_present'] not in ('yes', 'no', 'uncertain') or not isinstance(event['note'], str):
            raise ValueError('Respiración o nota inválida.')
        if type(event['within_word']) is not bool or type(event['nonarticulatory_confirmed']) is not bool:
            raise ValueError('Declaración intrapalabra inválida.')
        minimum = (rate * CONFIG['minimum_pause_ms'] + 999) // 1000
        if kind == 'pause':
            if b - a < minimum:
                raise ValueError('Una pausa computable debe durar al menos 250 ms.')
            if event['within_word'] and not event['nonarticulatory_confirmed']:
                raise ValueError('Intrapalabra: confirma interrupción no articulatoria o clasifica uncertain.')
            accepted.append(event)
        if kind == 'below_threshold' and b - a >= minimum:
            raise ValueError('below_threshold debe durar menos de 250 ms.')
        if temporal['status'] == 'confirmed' and kind in ('uncertain', 'other_nonverbal'):
            raise ValueError('Una región incierta/no verbal impide confirmar el resumen global.')
    # Annotations occupy one timeline: no contradictory labels or hidden double subtraction.
    ordered = sorted(intervals, key=lambda e: (e['start_sample'], e['end_sample_exclusive']))
    for left, right in zip(ordered, ordered[1:]):
        if left['end_sample_exclusive'] > right['start_sample']:
            raise ValueError('Intervalos solapados: corrige las anotaciones; no se unen automáticamente.')
        if left['end_sample_exclusive'] == right['start_sample'] and left['classification'] == right['classification'] == 'pause':
            raise ValueError('Pausas contiguas: revisa y registra una sola interrupción continua.')
    return copy.deepcopy(temporal), sorted(accepted, key=lambda e: e['start_sample'])


def analyze_pauses(data, context, review, expected_file_sha256, temporal):
    # Recompute 7A without modifying it; never trust client-supplied counts/durations/results.
    source = analyze_phrase(data, context, review, expected_file_sha256)
    t, accepted = validate_temporal(temporal, source)
    reason = ('selection_unconfirmed' if source['stages']['selection']['status'] != 'completed' else
              'content_review_pending' if not source['review'] or not source['review']['confirmed'] else
              'no_production' if source['review']['production'] == 'absent' else
              'content_review_pending' if source['review']['production'] != 'present' else
              'pause_review_not_evaluable' if t['status'] == 'not_evaluable' else
              'pause_review_uncertain' if any(e['classification'] in ('uncertain', 'other_nonverbal') for e in t['intervals']) else
              'pause_review_pending' if t['status'] != 'confirmed' else None)
    metrics = {name: measure(reason=reason) for name in METRICS}
    units = dict(zip(METRICS, ('s', 's', '%', 'count', 's', 's', 'syllables/s', 'words/min')))
    for name, unit in units.items():
        metrics[name]['unit'] = unit
    pause_samples = sum(e['end_sample_exclusive'] - e['start_sample'] for e in accepted)
    selected_samples = (source['selection']['end_sample_exclusive'] - source['selection']['start_sample']
                        if source['selection'] else None)
    remaining = selected_samples - pause_samples if selected_samples is not None else None
    rate = source['input']['sample_rate_hz']
    if reason is None:
        n = len(accepted)
        durations = sorted(e['end_sample_exclusive'] - e['start_sample'] for e in accepted)
        values = {'pause_duration_s': pause_samples / rate, 'operational_speech_time_s': remaining / rate,
                  'pause_percent': 100 * pause_samples / selected_samples, 'pause_count': n,
                  'pause_mean_duration_s': pause_samples / n / rate if n else None,
                  'pause_median_duration_s': ((durations[(n-1)//2] + durations[n//2]) / (2*rate)) if n else None}
        for key, value in values.items():
            metrics[key].update(value=value, reason='no_pauses' if value is None else None)
        for kind, scale in (('syllable', 1), ('word', 60)):
            count = source['review'][f'{kind}_count']
            r = ('nonpositive_operational_speech_time' if remaining <= 0 else
                 f'{kind}_count_unconfirmed' if not count['confirmed'] else None)
            metrics[f'reviewed_{kind}_articulation_rate'].update(
                value=count['value'] * scale * rate / remaining if r is None else None,
                reason=r, numerator=count['value'] if count['confirmed'] else None,
                denominator_s=remaining / rate, count_basis='7a_confirmed_manual_production_count')
    return {
        'schema_version': 'phrase_pause_output_v1', 'protocol_version': CONFIG['protocol_version'],
        'configuration': copy.deepcopy(CONFIG),
        'status': 'completed' if all(metrics[k]['value'] is not None for k in METRICS[-2:]) else 'partial',
        'stages': {'temporal_review': t['status'], 'calculation': 'blocked' if reason else 'completed' if all(metrics[k]['value'] is not None for k in METRICS[-2:]) else 'partial'},
        'metrics': metrics, 'temporal_review': t, 'source_7a': source,
        'provenance': {'source_dependencies': source_dependencies(source),
                       'temporal_review_sha256': digest(canonical(t)), 'config_sha256': digest(CONFIG_BYTES),
                       'engine_sha256': digest(Path(__file__).read_bytes())},
        'audit': {'accepted_pause_samples_partial': pause_samples, 'selected_samples': selected_samples,
                  'accepted_interval_ids_partial': [e['id'] for e in accepted],
                  'partial_evidence_is_not_global_summary': bool(reason),
                  'formula': 'integer samples: T=(selected_samples-sum(pause_samples))/Fs',
                  'filled_pauses_fragments_restarts': 'retained in operational time and reviewed counts',
                  'automatic_detection': False, 'human_validation': 'pending'},
        'warnings': source['warnings'] + ['OPERATIONAL_NOT_PURE_ARTICULATION_TIME']
    }
