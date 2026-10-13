"""Native HNR mean; frame coverage is separate from the native temporal statistic."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from backend.praat_runner import AnalysisError, CONFIG_PATH, MAX_BYTES, ROOT, _run, analyze_wav
from backend.jitter import _rail_samples
from backend.shimmer import amplitude_diagnostics

SCRIPT = ROOT / 'praat/hnr_v1.praat'


def _parse(raw, start, end):
    try:
        x = json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        mean = x['hnr_mean_db']
        if mean is not None and (isinstance(mean,bool) or not math.isfinite(mean)):
            raise ValueError('mean numeric integrity')
        frames = x['frames']
        if not isinstance(frames,list):
            raise ValueError('frames')
        previous_index = 0;previous_time = -math.inf;valid = 0
        for frame in frames:
            i,t,v = frame['frame_index'],frame['time_s'],frame['praat_raw_hnr_db']
            if (type(i) is not int or i <= previous_index or not math.isfinite(t)
                    or not start <= t <= end or t <= previous_time):
                raise ValueError('frame identity/order')
            if v is not None and (isinstance(v,bool) or not math.isfinite(v)):
                raise ValueError('frame numeric integrity')
            good = v is not None and v != -200
            frame.update(hnr_db=v if good else None,valid=good,
                         reason=None if good else 'praat_non_sounding' if v == -200 else 'praat_undefined',
                         numerical_limit=bool(good and v in (-150,150)))
            valid += good;previous_index=i;previous_time=t
        if (type(x['total_frames']) is not int or type(x['valid_frames']) is not int
                or x['total_frames'] != len(frames) or x['valid_frames'] != valid
                or type(x['object_frames']) is not int or x['object_frames'] < len(frames)
                or previous_index > x['object_frames'] or not math.isfinite(x['time_step_s'])
                or x['time_step_s'] <= 0 or not math.isfinite(x['first_frame_center_s'])):
            raise ValueError('counts/grid')
        # No frame-based mean is computed or used to validate/replace Get mean.
        return x
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        raise AnalysisError('Invalid HNR output from Praat') from exc


def analyze_hnr(data, emission_start_s=0.0, emission_end_s=None, *, diagnostic_interval=None, executable=None):
    smoke = analyze_wav(data, executable)
    duration = smoke['temporal']['file_duration_s']
    config_bytes = CONFIG_PATH.read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != smoke['provenance']['configuration_sha256']:
        raise AnalysisError('Configuration changed during analysis')
    config = json.loads(config_bytes)
    if diagnostic_interval is None:
        start,end = emission_start_s,duration if emission_end_s is None else emission_end_s
        if not all(math.isfinite(v) for v in (start,end)) or not 0 <= start < end <= duration:
            raise ValueError('Invalid emission interval')
        width = config['selection']['central_window_s']
        if end-start < width:
            raise ValueError('Selected emission must contain at least 3 seconds')
        center = (start+end)/2;start,end = center-width/2,center+width/2
        selection = 'central_3s_of_selected_emission'
        emission_selection = 'file_assumed_as_emission' if emission_end_s is None and emission_start_s == 0 else 'explicit_emission_limits'
    else:
        start,end = diagnostic_interval
        if not all(math.isfinite(v) for v in (start,end)) or not 0 <= start < end <= duration:
            raise ValueError('Invalid diagnostic interval')
        selection = 'explicit_diagnostic_interval_not_standard_protocol';emission_selection=None
    h = config['harmonicity']
    if h['method'] != 'cc' or h['aggregation'] != 'mean_db_valid_frames':
        raise AnalysisError('Unsupported HNR configuration')
    # The frozen aggregation label is historical shorthand; official mean is always Get mean.
    params = [h['time_step_s'],h['minimum_pitch_hz'],h['silence_threshold'],h['periods_per_window']]
    script_bytes = SCRIPT.read_bytes()
    with tempfile.TemporaryDirectory(prefix='habla-hnr-') as temp:
        path = Path(temp)/'input.wav';path.write_bytes(data)
        raw = _run([executable or os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(SCRIPT),str(path),
                    str(start),str(end),*map(str,params)])
    if SCRIPT.read_bytes() != script_bytes:
        raise AnalysisError('HNR script changed during analysis')
    x = _parse(raw,start,end)
    total,valid = x['total_frames'],x['valid_frames']
    coverage = 100.0*valid/total if total else None
    warnings = [{'code':'HNR_PERIODICITY_RELIABILITY_UNVERIFIED',
                 'message':'HNR experimental; fiabilidad de periodicidad no verificada en voz humana. HNR alto no descarta distorsión.'}]
    if not total:
        warnings.append({'code':'NO_HNR_ANALYSIS_FRAMES','message':'No hay centros de frames HNR dentro del intervalo.'})
    if coverage is not None and coverage < 100:
        warnings.append({'code':'INCOMPLETE_HNR_COVERAGE','message':'Cobertura HNR inferior al 100 %; sin umbral de rechazo.',
                         'coverage_percent':coverage})
    if total > valid:
        warnings.append({'code':'HNR_FRAMES_EXCLUDED','message':'Frames no válidos de Praat; no permiten inferir automáticamente silencio.',
                         'excluded_frames':total-valid})
    if x['hnr_mean_db'] is None:
        warnings.append({'code':'HNR_NOT_CALCULABLE','message':'Harmonicity: Get mean devolvió undefined; no se sustituye por una media de frames ni por cero.'})
    limits = sum(f['numerical_limit'] for f in x['frames'])
    if limits:
        warnings.append({'code':'HNR_NUMERICAL_LIMIT','message':'Frames en límite numérico +/-150 dB de Praat; no expresa precisión acústica demostrada.',
                         'frame_count':limits})
    diagnostics = amplitude_diagnostics(data,start,end)
    rails = _rail_samples(data)
    if rails:
        warnings.append({'code':'POSSIBLE_DIGITAL_CLIPPING','message':'Muestras en los límites digitales; posible saturación.',
                         'rail_samples_full_file':rails,'rail_samples_in_interval':diagnostics['digital_rail_samples_in_interval']})
    if diagnostics['rms_quantization_steps'] is not None and diagnostics['rms_quantization_steps'] < diagnostics['low_rms_threshold_quantization_steps']:
        warnings.append({'code':'LOW_DIGITAL_AMPLITUDE','message':'RMS inferior a 10 pasos PCM; aviso experimental de cuantificación, sin rechazo.'})
    if diagnostic_interval is not None:
        warnings.append({'code':'DIAGNOSTIC_INTERVAL','message':'Intervalo de prueba explícito; no equivale a la ventana central del protocolo.'})
    provenance = dict(smoke['provenance'])
    provenance.update(duration_script_sha256=provenance['script_sha256'],
                      script_sha256=hashlib.sha256(script_bytes).hexdigest(),module_version='hnr_v1',
                      output_schema_version='hnr_output_v1',warnings_version='hnr_warnings_v1')
    return {'status':'experimental_measurement','provenance':provenance,
            'analysis_interval':{'start_s':start,'end_s':end,'selection':selection,'emission_selection':emission_selection},
            'temporal':{'file_duration_s':duration,'analysis_interval_duration_s':end-start},
            'acoustic':{'hnr_mean_db':{'value':x['hnr_mean_db'],'reason':'praat_undefined' if x['hnr_mean_db'] is None else None,
                                     'status':'experimental_periodicity_reliability_unverified',
                                     'definition':'Praat 6.4.27 Harmonicity: Get mean; native temporal semantics'}},
            'quality':{'hnr_total_frames':total,'hnr_valid_frames':valid,'hnr_excluded_frames':total-valid,
                       'hnr_coverage_percent':{'value':coverage,'reason':None if total else 'no_analysis_frames'},
                       'f0_coverage':{'value':None,'reason':'not_computed_in_hnr_module'},
                       'accepted_cycles':{'value':None,'reason':'not_computed_in_hnr_module'},
                       'hnr_object_grid':{'object_frames':x['object_frames'],'time_step_s':x['time_step_s'],
                                          'first_frame_center_s':x['first_frame_center_s']},
                       'amplitude_diagnostics':diagnostics,'digital_rail_samples_full_file':rails,
                       'technical_warnings':warnings},
            'tracking_hnr_frames':x['frames']}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('wav',type=Path)
    parser.add_argument('--emission-start',type=float,default=0);parser.add_argument('--emission-end',type=float)
    args=parser.parse_args()
    if args.wav.stat().st_size > MAX_BYTES: parser.error('File exceeds 10 MiB')
    print(json.dumps(analyze_hnr(args.wav.read_bytes(),args.emission_start,args.emission_end),indent=2,allow_nan=False))


if __name__=='__main__': main()
