"""Experimental native shimmer local, with native amplitude extraction for audit."""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import wave

from backend.jitter import analyze_jitter, _parse as parse_pulses
from backend.praat_runner import AnalysisError, CONFIG_PATH, MAX_BYTES, ROOT, _run

SCRIPT = ROOT / 'praat/shimmer_v1.praat'
LOW_RMS_QUANTIZATION_STEPS = 10  # experimental warning, never a rejection rule


def amplitude_diagnostics(data, start, end):
    with wave.open(io.BytesIO(data), 'rb') as wav:
        width, rate, n = wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        raw = wav.readframes(n)
    lo, hi = -(1 << (8 * width - 1)), (1 << (8 * width - 1)) - 1
    selected = range(max(0, math.ceil(start * rate - .5)), min(n, math.floor(end * rate - .5) + 1))
    squares = rails = count = 0
    for i in selected:
        value = int.from_bytes(raw[i*width:(i+1)*width], 'little', signed=True)
        squares += value * value
        rails += value in (lo, hi)
        count += 1
    rms_steps = math.sqrt(squares/count) if count else None
    return {'sample_width_bytes': width, 'sample_count': count,
            'rms_quantization_steps': rms_steps,
            'rms_full_scale': rms_steps / (-lo) if rms_steps is not None else None,
            'low_rms_threshold_quantization_steps': LOW_RMS_QUANTIZATION_STEPS,
            'digital_rail_samples_in_interval': rails}


def _parse(raw, start, end):
    # Reuse proven pulse ordering/count validation; do not calculate shimmer here.
    try:
        x = json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        pulse_payload = dict(x, jitter_local_ratio=0.0)
        _, inside, candidates = parse_pulses(json.dumps(pulse_payload, allow_nan=False), start, end)
        for key in ('shimmer_local_ratio', 'tier_shimmer_ratio'):
            value = x[key]
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError('shimmer numeric integrity')
        previous = -math.inf
        interior = {p['time_s'] for p in inside[1:-1]}
        amplitudes = x['amplitudes']
        if len(amplitudes) > max(0, len(inside)-2):
            raise ValueError('amplitude count')
        for index, point in enumerate(amplitudes, 1):
            t, value = point['time_s'], point['amplitude_rms']
            if (point['amplitude_index'] != index or not math.isfinite(t) or t <= previous
                    or t not in interior or not math.isfinite(value) or value <= 0):
                raise ValueError('amplitude identity')
            previous = t
        return x, inside, candidates
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        raise AnalysisError('Invalid shimmer output from Praat') from exc


def analyze_shimmer(data, emission_start_s=0.0, emission_end_s=None, *, diagnostic_interval=None, executable=None):
    result = analyze_jitter(data, emission_start_s, emission_end_s,
                            diagnostic_interval=diagnostic_interval, executable=executable)
    config_bytes = CONFIG_PATH.read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != result['provenance']['configuration_sha256']:
        raise AnalysisError('Configuration changed during analysis')
    config = json.loads(config_bytes)
    p, q = config['pitch'], config['perturbation']
    if q['shimmer_variant'] != 'local_percent':
        raise AnalysisError('Unsupported shimmer configuration')
    start, end = result['analysis_interval']['start_s'], result['analysis_interval']['end_s']
    params = [p['time_step_s'], p['floor_hz'], p['ceiling_hz'], p['max_candidates'], int(p['very_accurate']),
              p['silence_threshold'], p['voicing_threshold'], p['octave_cost'], p['octave_jump_cost'],
              p['voiced_unvoiced_cost'], q['period_floor_s'], q['period_ceiling_s'],
              q['maximum_period_factor'], q['maximum_amplitude_factor']]
    script_bytes = SCRIPT.read_bytes()
    with tempfile.TemporaryDirectory(prefix='habla-shimmer-') as temp:
        path = Path(temp)/'input.wav'
        path.write_bytes(data)
        raw = _run([executable or os.environ.get('PRAAT_EXECUTABLE', 'praat'), '--run', str(SCRIPT),
                    str(path), str(start), str(end), *map(str, params)])
    if SCRIPT.read_bytes() != script_bytes:
        raise AnalysisError('Shimmer script changed during analysis')
    x, inside, _ = _parse(raw, start, end)
    # A repeated native route must describe exactly the same pulse sequence and accepted periods.
    if (x['pulses'] != result['tracking_pulses'] or
            x['accepted_periods_praat'] != result['quality']['pulse_audit']['accepted_periods_praat']):
        raise AnalysisError('Pulse audit differs between native analyses')
    ratio = x['shimmer_local_ratio']
    value = ratio * 100 if ratio is not None else None
    if value is not None and not math.isfinite(value):
        raise AnalysisError('Shimmer percent overflow')
    result['acoustic']['shimmer_local_percent'] = {
        'value': value, 'reason': 'praat_undefined' if value is None else None,
        'status': 'experimental_pulse_reliability_unverified'}
    amplitudes = x['amplitudes']
    possible = max(0, len(inside)-2)
    # Optional simple screening of adjacent exported values; NOT native pair-usage accounting.
    over_factor = sum(max(a['amplitude_rms'], b['amplitude_rms']) /
                     min(a['amplitude_rms'], b['amplitude_rms']) > q['maximum_amplitude_factor']
                     for a, b in zip(amplitudes, amplitudes[1:]))
    quality = result['quality']
    quality['shimmer_audit'] = {
        'interior_pulses_candidate_for_amplitude': possible,
        'amplitudes_extracted_praat': len(amplitudes),
        'amplitudes_not_extracted': possible-len(amplitudes),
        'boundary_pulses_without_amplitude': min(2, len(inside)),
        'adjacent_amplitude_ratios_over_factor': over_factor,
        'shimmer_pairs_used': {'value': None, 'reason': 'not_implemented'},
        'tier_shimmer_local_percent': x['tier_shimmer_ratio'] * 100 if x['tier_shimmer_ratio'] is not None else None,
        'amplitude_definition': 'Praat 6.4.27 Hann-windowed RMS; widths 0.2 times each adjacent period',
        'amplitude_units': 'Praat Sound sample units; recording is not calibrated to physical sound pressure'}
    result['tracking_amplitudes'] = amplitudes
    warnings = quality['technical_warnings']
    # Reuse the hito 3 warning code, but describe both perturbation measures.
    for warning in warnings:
        if warning['code'] == 'PULSE_RELIABILITY_UNVERIFIED':
            warning['message'] = 'Fiabilidad de pulsos no verificada; jitter y shimmer experimentales, sin interpretación clínica.'
    if value is None:
        warnings.append({'code': 'SHIMMER_NOT_CALCULABLE',
                         'message': 'Get shimmer (local) devolvió undefined; no se convierte en cero.'})
    if possible > len(amplitudes):
        warnings.append({'code': 'AMPLITUDES_NOT_EXTRACTED',
                         'message': 'Praat no extrajo amplitudes para todos los pulsos interiores; filtros temporales, RMS o muestras disponibles pueden intervenir.',
                         'count': possible-len(amplitudes)})
    if over_factor:
        warnings.append({'code': 'AMPLITUDE_FACTOR_EXCLUSIONS_POSSIBLE',
                         'message': 'Hay razones de amplitud superiores a 1.6; este recuento no identifica los pares finalmente utilizados.',
                         'adjacent_ratios_over_factor': over_factor})
    diagnostics = amplitude_diagnostics(data, start, end)
    quality['amplitude_diagnostics'] = diagnostics
    if diagnostics['rms_quantization_steps'] is not None and diagnostics['rms_quantization_steps'] < LOW_RMS_QUANTIZATION_STEPS:
        warnings.append({'code': 'LOW_DIGITAL_AMPLITUDE',
                         'message': 'RMS inferior a 10 pasos PCM; aviso experimental de cuantificación, sin rechazo del resultado.'})
    if quality['digital_rail_samples']:
        for warning in warnings:
            if warning['code'] == 'POSSIBLE_DIGITAL_CLIPPING':
                warning['rail_samples_in_interval'] = diagnostics['digital_rail_samples_in_interval']
                warning['scope'] = 'full_file_and_analysis_interval'
    provenance = result['provenance']
    provenance.update(jitter_script_sha256=provenance['script_sha256'],
                      script_sha256=hashlib.sha256(script_bytes).hexdigest(), module_version='shimmer_v1',
                      output_schema_version='shimmer_output_v1', warnings_version='shimmer_warnings_v1',
                      jitter_warnings_version='jitter_warnings_v1')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('wav', type=Path)
    parser.add_argument('--emission-start', type=float, default=0)
    parser.add_argument('--emission-end', type=float)
    args = parser.parse_args()
    if args.wav.stat().st_size > MAX_BYTES:
        parser.error('File exceeds 10 MiB')
    print(json.dumps(analyze_shimmer(args.wav.read_bytes(), args.emission_start, args.emission_end), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
