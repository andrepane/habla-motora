"""F0 only, using Praat's own interval statistics and selected frame values."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from backend.praat_runner import AnalysisError, CONFIG_PATH, MAX_BYTES, ROOT, _run, analyze_wav

SCRIPT = ROOT / 'praat/pitch_v1.praat'
MODULE_VERSION = 'pitch_v1'
OUTPUT_SCHEMA_VERSION = 'pitch_output_v1'
WARNINGS_VERSION = 'pitch_warnings_v1'


def _metric(value, reason):
    return {'value': value, 'reason': reason if value is None else None}


def _validate_and_summarize(raw, start, end):
    try:
        x = json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        frames = x['frames']
        if not isinstance(frames, list):
            raise ValueError('frames')
        previous = None
        for frame in frames:
            index, t, f = frame['frame_index'], frame['time_s'], frame['f0_hz']
            if not isinstance(index, int) or index < 1 or not math.isfinite(t) or not start <= t <= end:
                raise ValueError('frame identity')
            if previous is not None and (index <= previous['frame_index'] or t <= previous['time_s']):
                raise ValueError('frame ordering')
            if f is not None and (not math.isfinite(f) or not 0 < f < 600):
                raise ValueError('frame F0')
            previous = frame
        total = len(frames)
        voiced = sum(f['f0_hz'] is not None for f in frames)
        if x['total_frames'] != total or x['voiced_frames'] != voiced:
            raise ValueError('counts')
        mean, sd = x['f0_mean_hz'], x['f0_sd_hz']
        for value in (mean, sd):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError('statistic')
        if mean == 0 or (voiced == 0 and (mean is not None or sd is not None)) or (voiced < 2 and sd is not None):
            raise ValueError('undefined statistic contract')
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise AnalysisError('Invalid pitch output from Praat') from exc
    warnings = []
    def warn(code, message, **details):
        warnings.append({'code': code, 'message': message, **details})
    coverage = 100.0 * voiced / total if total else None
    if total == 0:
        warn('NO_ANALYSIS_FRAMES', 'No hay frames de pitch con centro en el intervalo.')
    elif voiced == 0:
        warn('F0_NOT_DETECTED', 'F0 no detectada; no permite inferir silencio ni ausencia real de sonoridad.')
    if coverage is not None and coverage < 100:
        warn('INCOMPLETE_F0_COVERAGE', 'Cobertura de F0 inferior al 100 %; sin umbral de rechazo.', coverage_percent=coverage)
    if voiced == 1:
        warn('INSUFFICIENT_VOICED_FRAMES', 'Solo un frame con F0 definida; desviación típica no calculable.')
    if voiced > 0 and mean is None:
        warn('PRAAT_MEAN_UNDEFINED', 'La consulta Get mean de Praat devolvió undefined.')
    if voiced > 1 and sd is None:
        warn('PRAAT_SD_UNDEFINED', 'La consulta Get standard deviation de Praat devolvió undefined.')
    for before, after in zip(frames, frames[1:]):
        if (after['frame_index'] == before['frame_index'] + 1
                and before['f0_hz'] is not None and after['f0_hz'] is not None):
            delta = 12 * math.log2(after['f0_hz'] / before['f0_hz'])
            if 11 <= abs(delta) <= 13:
                warn('POSSIBLE_OCTAVE_JUMP', 'Salto experimental de 11–13 semitonos; no confirma error y no se corrige.',
                     from_frame=before['frame_index'], to_frame=after['frame_index'], semitones=delta)
    reason = 'no_analysis_frames' if total == 0 else 'f0_not_detected' if voiced == 0 else 'praat_undefined'
    return {
        'acoustic': {'f0_mean_hz': _metric(mean, reason),
                     'f0_sd_hz': _metric(sd, 'insufficient_voiced_frames' if voiced == 1 else reason)},
        'quality': {'total_frames': total, 'voiced_frames': voiced,
                    'f0_coverage_percent': _metric(coverage, 'no_analysis_frames'),
                    'accepted_cycles': _metric(None, 'not_implemented'),
                    'technical_warnings': warnings},
        'tracking_frames': frames,
    }


def analyze_pitch(data: bytes, emission_start_s=0.0, emission_end_s=None,
                  *, diagnostic_interval=None, executable=None):
    # The existing, verified smoke runner validates the WAV and exact engine version.
    smoke = analyze_wav(data, executable)
    duration = smoke['temporal']['file_duration_s']
    config_bytes = CONFIG_PATH.read_bytes()
    config = json.loads(config_bytes)
    if hashlib.sha256(config_bytes).hexdigest() != smoke['provenance']['configuration_sha256']:
        raise AnalysisError('Configuration changed during analysis')
    emission_selection = 'file_assumed_as_emission' if emission_end_s is None and emission_start_s == 0 else 'explicit_emission_limits'
    if diagnostic_interval is None:
        end = duration if emission_end_s is None else emission_end_s
        start = emission_start_s
        if not all(math.isfinite(v) for v in (start, end)) or not 0 <= start < end <= duration:
            raise ValueError('Invalid emission interval')
        width = config['selection']['central_window_s']
        if end - start < width:
            raise ValueError('Selected emission must contain at least 3 seconds')
        center = (start + end) / 2
        start, end = center-width/2, center+width/2
        selection = 'central_3s_of_selected_emission'
    else:
        start, end = diagnostic_interval
        if not all(math.isfinite(v) for v in (start, end)) or not 0 <= start < end <= duration:
            raise ValueError('Invalid diagnostic interval')
        selection = 'explicit_diagnostic_interval_not_standard_protocol'
    p = config['pitch']  # scope is historical; never used as software state.
    if p['method'] != 'raw_cross_correlation':
        raise AnalysisError('Unsupported pitch method')
    args = [p['time_step_s'], p['floor_hz'], p['ceiling_hz'], p['max_candidates'],
            int(p['very_accurate']), p['silence_threshold'], p['voicing_threshold'],
            p['octave_cost'], p['octave_jump_cost'], p['voiced_unvoiced_cost']]
    script_bytes = SCRIPT.read_bytes()
    engine = executable or os.environ.get('PRAAT_EXECUTABLE', 'praat')
    with tempfile.TemporaryDirectory(prefix='habla-pitch-') as temp:
        path = Path(temp)/'input.wav'
        path.write_bytes(data)
        raw = _run([engine, '--run', str(SCRIPT), str(path), str(start), str(end), *map(str, args)])
    if SCRIPT.read_bytes() != script_bytes:
        raise AnalysisError('Pitch script changed during analysis')
    result = _validate_and_summarize(raw, start, end)
    provenance = dict(smoke['provenance'])
    provenance['duration_script_sha256'] = provenance['script_sha256']
    provenance['script_sha256'] = hashlib.sha256(script_bytes).hexdigest()
    provenance.update(module_version=MODULE_VERSION, output_schema_version=OUTPUT_SCHEMA_VERSION,
                      warnings_version=WARNINGS_VERSION)
    result.update(status='experimental_measurement', provenance=provenance,
                  analysis_interval={'start_s': start, 'end_s': end, 'selection': selection,
                                     'emission_selection': emission_selection if diagnostic_interval is None else None},
                  temporal={'file_duration_s': duration, 'analysis_interval_duration_s': end-start})
    if diagnostic_interval is not None:
        result['quality']['technical_warnings'].append({'code':'DIAGNOSTIC_INTERVAL',
            'message':'Intervalo de prueba explícito; no equivale a la ventana central del protocolo.'})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('wav', type=Path)
    parser.add_argument('--emission-start', type=float, default=0)
    parser.add_argument('--emission-end', type=float)
    args = parser.parse_args()
    if args.wav.stat().st_size > MAX_BYTES:
        parser.error('File exceeds 10 MiB')
    print(json.dumps(analyze_pitch(args.wav.read_bytes(), args.emission_start, args.emission_end), indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
