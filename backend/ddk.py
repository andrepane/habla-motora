"""DDK 6A: deterministic acoustic candidates, never automatic phonetic identity."""
from pathlib import Path
import copy
import hashlib
import io
import json
import math
import statistics
import wave

ROOT = Path(__file__).resolve().parents[1]
CONFIG_BYTES = (ROOT / 'configs/ddk_experimental_v1.json').read_bytes()
CONFIG = json.loads(CONFIG_BYTES)
MAX_BYTES = CONFIG['max_bytes']


class DetectionError(Exception):
    """Expected detector failure; only this failure supports partial evidence."""


def measure(value=None, reason=None):
    return {'value': value, 'reason': reason}


def percentile(values, p):
    ordered = sorted(values)
    at = (len(ordered)-1)*p/100
    lo = math.floor(at); hi = math.ceil(at)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(at-lo)


def read_wav(data):
    if not data or len(data) > MAX_BYTES:
        raise ValueError('DDK admite hasta 4.000.000 bytes.')
    try:
        with wave.open(io.BytesIO(data), 'rb') as wav:
            rate, width, channels, n = wav.getframerate(), wav.getsampwidth(), wav.getnchannels(), wav.getnframes()
            if rate not in (44100, 48000) or width not in (2, 3, 4) or channels != 1 or wav.getcomptype() != 'NONE' or not n:
                raise ValueError('Se necesita WAV PCM mono 16/24/32 bits a 44100/48000 Hz.')
            if n/rate > CONFIG['max_file_duration_s']:
                raise ValueError('DDK admite archivos de hasta 15 segundos.')
            raw = wav.readframes(n)
            if len(raw) != n*width:
                raise ValueError('WAV truncado.')
    except (wave.Error, EOFError) as exc:
        raise ValueError('WAV PCM inválido.') from exc
    scale = 2**(8*width-1)
    samples = [int.from_bytes(raw[i:i+width], 'little', signed=True)/scale for i in range(0, len(raw), width)]
    return samples, rate, width


def detect(samples, rate, a, b):
    window = round(rate*CONFIG['window_ms']/1000)
    hop = round(rate*CONFIG['hop_ms']/1000)
    weights = [0.5-0.5*math.cos(2*math.pi*i/(window-1)) for i in range(window)]
    total = sum(weights)
    frames = []
    for center in range(a, b, hop):
        left = center-window//2
        energy = sum(samples[j]**2*weights[k] for k, j in enumerate(range(left, left+window)) if 0 <= j < len(samples))/total
        frames.append({'frame_index': len(frames), 'time_s': center/rate,
                       'energy_db': max(CONFIG['digital_floor_db'], 10*math.log10(max(energy, 1e-12))),
                       'boundary': left < a or left+window > b})
    if not frames:
        raise DetectionError('No hay frames para analizar.')
    vals = [f['energy_db'] for f in frames]
    threshold = max(percentile(vals, CONFIG['noise_percentile'])+CONFIG['noise_margin_db'],
                    percentile(vals, CONFIG['signal_percentile'])-CONFIG['signal_margin_db'])
    candidates = []
    i = 0
    while i < len(vals):
        end = i
        while end+1 < len(vals) and vals[end+1] == vals[i]:
            end += 1
        if (i == 0 or vals[i] > vals[i-1]) and (end == len(vals)-1 or vals[end] > vals[end+1]):
            peak = vals[i]
            left = i
            while left > 0 and vals[left-1] <= peak:
                left -= 1
            right = end
            while right+1 < len(vals) and vals[right+1] <= peak:
                right += 1
            dip = min(peak-min(vals[left:i+1]), peak-min(vals[end:right+1]))
            boundary = any(f['boundary'] for f in frames[i:end+1]) or i == 0 or end == len(vals)-1
            reason = ('boundary_incomplete' if boundary else 'below_threshold' if peak < threshold
                      else 'insufficient_dip' if dip < CONFIG['minimum_dip_db'] else None)
            candidates.append({'id': f'c{len(candidates)+1}', 'time_s': (frames[i]['time_s']+frames[end]['time_s'])/2,
                               'energy_db': peak, 'dip_db': dip, 'boundary': boundary,
                               'accepted': reason is None, 'reason': reason})
        i = end+1
    kept = []
    for c in sorted((c for c in candidates if c['accepted']), key=lambda c: (-c['energy_db'], c['time_s'])):
        if any(abs(c['time_s']-k['time_s']) < CONFIG['minimum_separation_ms']/1000 for k in kept):
            c['accepted'] = False; c['reason'] = 'minimum_separation'
        else:
            kept.append(c)
    events = [{'id': c['id'], 'time_s': c['time_s'], 'label': 'unknown', 'restart': False}
              for c in candidates if c['accepted']]
    return {'frames': frames, 'threshold_db': threshold, 'candidates': candidates, 'events': events,
            'warnings': ['ACOUSTIC_CANDIDATES_NOT_PHONETIC_RECOGNITION'] + (['POSSIBLE_DIGITAL_CLIPPING'] if any(abs(x) >= .999 for x in samples[a:b]) else [])}


def temporal(intervals):
    if not intervals:
        return {'mean_ms': measure(reason='no_intervals'), 'sd_ms': measure(reason='insufficient_intervals'),
                'cv_percent': measure(reason='insufficient_intervals'), 'intervals_s': [], 'n_intervals': 0}
    mean = statistics.mean(intervals)
    enough = len(intervals) >= CONFIG['minimum_intervals']
    sd = statistics.stdev(intervals) if enough else None
    return {'mean_ms': measure(mean*1000), 'sd_ms': measure(sd*1000) if enough else measure(reason='insufficient_intervals'),
            'cv_percent': measure(100*sd/mean) if enough and mean > 0 else measure(reason='insufficient_intervals'),
            'intervals_s': intervals, 'n_intervals': len(intervals)}


def calculate(events, groups, duration, zero_confirmed=False):
    intervals, excluded = [], []
    for prev, curr in zip(events, events[1:]):
        transition = {'from_id': prev['id'], 'to_id': curr['id'], 'duration_s': curr['time_s']-prev['time_s']}
        if curr.get('restart'):
            excluded.append({**transition, 'reason': 'manual_restart'})
        else:
            intervals.append(transition['duration_s'])
    cycle_intervals, excluded_cycles = [], []
    index = {e['id']: i for i, e in enumerate(events)}
    for prev, curr in zip(groups or [], (groups or [])[1:]):
        delta = curr['time_s']-prev['time_s']
        start, end = index[prev['event_ids'][0]], index[curr['event_ids'][0]]
        if end == start+3 and not any(e.get('restart') for e in events[start+1:end+1]):
            cycle_intervals.append(delta)
        else:
            excluded_cycles.append({'from_id': prev['id'], 'to_id': curr['id'], 'duration_s': delta, 'reason': 'nonconsecutive_or_restart'})
    return {'event_count': measure(len(events)),
            'event_rate_per_s': measure(len(events)/duration) if events or zero_confirmed else measure(reason='no_evidence'),
            'group_count': measure(len(groups)) if groups is not None else measure(reason='anchor_not_requested'),
            'group_rate_per_s': measure(len(groups)/duration) if groups is not None and (groups or zero_confirmed) else measure(reason='no_groups' if groups is not None else 'anchor_not_requested'),
            'event_regularity': temporal(intervals), 'group_regularity': temporal(cycle_intervals),
            'excluded_event_transitions': excluded, 'excluded_group_transitions': excluded_cycles}


def group_events(events, anchor=None, reviewed=False):
    if reviewed:
        groups = []; i = 0
        while i+2 < len(events):
            triple = events[i:i+3]
            if [e['label'] for e in triple] == ['pa', 'ta', 'ka'] and not any(e.get('restart') for e in triple[1:]):
                groups.append({'id': f'g{len(groups)+1}', 'event_ids': [e['id'] for e in triple], 'time_s': triple[0]['time_s']}); i += 3
            else:
                i += 1
        return groups
    if anchor is None:
        return None
    ids = [e['id'] for e in events]
    if anchor not in ids:
        raise ValueError('Anclaje debe ser un núcleo candidato aceptado.')
    groups = []
    for i in range(ids.index(anchor), len(events)-2, 3):
        triple = events[i:i+3]
        groups.append({'id': f'g{len(groups)+1}', 'event_ids': [e['id'] for e in triple], 'time_s': triple[0]['time_s']})
    return groups


def apply_review(events, review, start, end):
    if not isinstance(review, dict) or set(review)-{'operations', 'confirmed', 'confirm_absence'}:
        raise ValueError('Revisión inválida.')
    operations = review.get('operations', [])
    if not isinstance(operations, list) or len(operations) > 1000:
        raise ValueError('Operaciones de revisión inválidas.')
    if type(review.get('confirmed', False)) is not bool or type(review.get('confirm_absence', False)) is not bool:
        raise ValueError('Confirmación debe ser booleana.')
    output = copy.deepcopy(events)
    used = {e['id'] for e in output}
    for op in operations:
        if not isinstance(op, dict) or set(op)-{'action', 'id', 'time_s', 'label', 'restart'}:
            raise ValueError('Operación inválida.')
        action, eid = op.get('action'), op.get('id')
        if not isinstance(eid, str) or not 1 <= len(eid) <= 80:
            raise ValueError('Identificador inválido.')
        event = next((e for e in output if e['id'] == eid), None)
        if action == 'add':
            if eid in used:
                raise ValueError('Identificador repetido.')
            used.add(eid)
            event = {'id': eid, 'time_s': op.get('time_s'), 'label': 'unknown', 'restart': False}
            output.append(event)
        elif not event:
            raise ValueError('Acontecimiento desconocido.')
        if action == 'delete':
            output.remove(event)
        elif action in ('add', 'move'):
            t = op.get('time_s')
            if type(t) not in (int, float) or not math.isfinite(t) or not start <= t < end:
                raise ValueError('Tiempo fuera del intervalo.')
            event['time_s'] = t
        elif action == 'label':
            if op.get('label') not in ('pa', 'ta', 'ka', 'other', 'unknown'):
                raise ValueError('Etiqueta de revisión inválida.')
            event['label'] = op['label']
        elif action == 'restart':
            if type(op.get('restart')) is not bool:
                raise ValueError('Reinicio inválido.')
            event['restart'] = op['restart']
        else:
            raise ValueError('Acción de revisión inválida.')
    output.sort(key=lambda e: e['time_s'])
    if len({e['time_s'] for e in output}) != len(output):
        raise ValueError('Tiempos coincidentes no permitidos.')
    confirmed = review.get('confirmed', False)
    absence = review.get('confirm_absence', False)
    if absence and (output or not confirmed):
        raise ValueError('Ausencia incompatible con acontecimientos o revisión sin confirmar.')
    if confirmed and (any(e['label'] == 'unknown' for e in output) or (not output and not absence)):
        raise ValueError('Revisa todas las etiquetas o confirma explícitamente ausencia.')
    return output, confirmed, absence


def analyze_ddk(data, start=0.0, end=None, anchor=None, review=None, expected_hash=None):
    samples, rate, width = read_wav(data)
    duration = len(samples)/rate
    end = duration if end is None else end
    if type(start) not in (int, float) or type(end) not in (int, float) or not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= duration:
        raise ValueError('Intervalo inválido.')
    # Explicit sample-grid selection; no hidden resampling or duration formatting.
    a, b = math.ceil(start*rate), min(len(samples), math.ceil(end*rate))
    if b-a < round(rate*.02):
        raise ValueError('El tramo debe contener al menos 20 ms.')
    start_eff, end_eff = a/rate, b/rate
    digest = hashlib.sha256(data).hexdigest()
    if review is not None and expected_hash != digest:
        raise ValueError('La revisión no corresponde al hash del WAV.')
    detector_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    stages = {}
    try:
        detection = detect(samples, rate, a, b)
        state = 'completed' if detection['events'] else 'empty'
        stages['detection'] = {'status': state, 'reason': None if state == 'completed' else 'no_evidence'}
    except DetectionError as exc:
        detection = {'events': [], 'candidates': [], 'frames': [], 'threshold_db': None, 'warnings': []}
        stages['detection'] = {'status': 'failed', 'reason': 'detector_failed', 'message': str(exc)}
    failed = stages['detection']['status'] == 'failed'
    events = detection['events']
    groups = None if failed else group_events(events, anchor)
    stages['grouping'] = {'status': 'blocked' if failed else 'completed' if groups is not None else 'not_requested',
                          'reason': 'detector_failed' if failed else 'anchor_not_requested' if groups is None else None}
    automatic = calculate(events, groups, end_eff-start_eff)
    if failed:
        for key in ('event_count', 'event_rate_per_s', 'group_count', 'group_rate_per_s'):
            automatic[key] = measure(reason='detector_failed')
    stages['calculation'] = {'status': 'blocked' if failed else 'partial' if not events or automatic['event_regularity']['cv_percent']['value'] is None or (groups is not None and automatic['group_regularity']['cv_percent']['value'] is None) else 'completed'}
    reviewed = None
    if review is None:
        stages['review'] = {'status': 'not_requested'}
    else:
        corrected, confirmed, absence = apply_review(events, review, start_eff, end_eff)
        stages['review'] = {'status': 'completed' if confirmed else 'draft'}
        reviewed = {'events': corrected, 'groups': group_events(corrected, reviewed=True) if confirmed else None,
                    'metrics': None, 'confirmed': confirmed, 'confirm_absence': absence}
        if confirmed:
            reviewed['metrics'] = calculate(corrected, reviewed['groups'], end_eff-start_eff, zero_confirmed=True)
            reviewed['calculation_status'] = 'partial' if any(reviewed['metrics'][key]['cv_percent']['value'] is None for key in ('event_regularity', 'group_regularity')) else 'completed'
    return {'schema_version': 'ddk_output_v1', 'status': 'partial' if stages['detection']['status'] != 'completed' or stages['calculation']['status'] != 'completed' else 'completed',
            'validation': {'technical': 'experimental_6a_pending_final_review', 'human_speech': 'pending_6b', 'phonetic_recognition': False},
            'provenance': {'file_sha256': digest, 'configuration_sha256': hashlib.sha256(CONFIG_BYTES).hexdigest(),
                           'configuration_version': CONFIG['version'], 'module_version': 'ddk_v1', 'detector_sha256': detector_hash,
                           'algorithm': 'hann_rms_candidate_peaks', 'runtime': 'python_stdlib'},
            'input': {'file_duration_s': duration, 'sample_rate': rate, 'bits': width*8, 'requested_start_s': start, 'requested_end_s': end},
            'analysis_interval': {'start_s': start_eff, 'end_s': end_eff, 'start_sample': a, 'end_sample_exclusive': b, 'duration_s': (b-a)/rate},
            'configuration': CONFIG, 'stages': stages,
            'automatic_original': {'detection': detection, 'anchor_id': anchor, 'groups': groups, 'metrics': automatic},
            'manual_modifications': copy.deepcopy(review) if review is not None else None, 'reviewed_result': reviewed}
