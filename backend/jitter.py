"""Experimental jitter local; Praat alone determines whether the value is defined."""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile
import wave

from backend.pitch import analyze_pitch
from backend.praat_runner import AnalysisError, CONFIG_PATH, MAX_BYTES, ROOT, _run

SCRIPT = ROOT/'praat/jitter_v1.praat'


def _rail_samples(data):
    with wave.open(io.BytesIO(data), 'rb') as wav:
        width = wav.getsampwidth()
        raw = wav.readframes(wav.getnframes())
    lo, hi = -(1 << (8*width-1)), (1 << (8*width-1))-1
    return sum(int.from_bytes(raw[i:i+width],'little',signed=True) in (lo,hi)
               for i in range(0,len(raw),width))


def _parse(raw,start,end):
    try:
        x = json.loads(raw, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        pulses=x['pulses']; previous=-math.inf
        for index,p in enumerate(pulses,1):
            if p['pulse_index']!=index or not math.isfinite(p['time_s']) or p['time_s']<=previous:
                raise ValueError('pulse ordering')
            previous=p['time_s']
        inside=[p for p in pulses if start<=p['time_s']<=end]
        candidates=max(0,len(inside)-1)
        accepted=x['accepted_periods_praat']
        if (x['pulses_in_interval']!=len(inside) or not isinstance(accepted,int)
                or not 0<=accepted<=candidates):
            raise ValueError('counts')
        ratio=x['jitter_local_ratio']
        if ratio is not None and (not math.isfinite(ratio) or ratio<0):
            raise ValueError('jitter numeric integrity')
        return x,inside,candidates
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        raise AnalysisError('Invalid jitter output from Praat') from exc


def analyze_jitter(data,emission_start_s=0.0,emission_end_s=None,*,diagnostic_interval=None,executable=None):
    r=analyze_pitch(data,emission_start_s,emission_end_s,
                    diagnostic_interval=diagnostic_interval,executable=executable)
    cfg_bytes=CONFIG_PATH.read_bytes(); cfg=json.loads(cfg_bytes)
    if hashlib.sha256(cfg_bytes).hexdigest()!=r['provenance']['configuration_sha256']:
        raise AnalysisError('Configuration changed during analysis')
    start,end=r['analysis_interval']['start_s'],r['analysis_interval']['end_s']
    p=cfg['pitch']; q=cfg['perturbation']
    if cfg['pulses']['method']!='Sound & Pitch: To PointProcess (cc)' or q['jitter_variant']!='local_percent':
        raise AnalysisError('Unsupported jitter configuration')
    params=[p['time_step_s'],p['floor_hz'],p['ceiling_hz'],p['max_candidates'],int(p['very_accurate']),
            p['silence_threshold'],p['voicing_threshold'],p['octave_cost'],p['octave_jump_cost'],
            p['voiced_unvoiced_cost'],q['period_floor_s'],q['period_ceiling_s'],q['maximum_period_factor']]
    script_bytes=SCRIPT.read_bytes()
    with tempfile.TemporaryDirectory(prefix='habla-jitter-') as temp:
        wav=Path(temp)/'input.wav'; wav.write_bytes(data)
        raw=_run([executable or os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(SCRIPT),str(wav),
                  str(start),str(end),*map(str,params)])
    if SCRIPT.read_bytes()!=script_bytes:
        raise AnalysisError('Jitter script changed during analysis')
    x,inside,candidates=_parse(raw,start,end)
    ratio=x['jitter_local_ratio']; value=ratio*100 if ratio is not None else None
    if value is not None and not math.isfinite(value):
        raise AnalysisError('Jitter percent overflow')
    r['acoustic']['jitter_local_percent']={'value':value,'reason':'praat_undefined' if value is None else None,
        'status':'experimental_pulse_reliability_unverified'}
    quality=r['quality']
    quality['accepted_cycles']={'value':x['accepted_periods_praat'],'reason':None,
                               'definition':'PointProcess: Get number of periods with experimental_v1 parameters'}
    quality['pulse_audit']={'pulses_full_sound':len(x['pulses']), 'pulses_in_interval':len(inside),
                           'candidate_periods':candidates, 'accepted_periods_praat':x['accepted_periods_praat'],
                           'jitter_pairs_used':{'value':None,'reason':'not_implemented'}}
    r['tracking_pulses']=x['pulses']
    r['tracking_periods']=[{'left_pulse_index':a['pulse_index'],'right_pulse_index':b['pulse_index'],
                           'start_s':a['time_s'],'end_s':b['time_s'],'duration_s':b['time_s']-a['time_s']}
                          for a,b in zip(inside,inside[1:])]
    warnings=quality['technical_warnings']
    warnings.append({'code':'PULSE_RELIABILITY_UNVERIFIED',
                     'message':'Fiabilidad de pulsos no verificada; jitter experimental, sin interpretación clínica.'})
    if candidates>x['accepted_periods_praat']:
        warnings.append({'code':'PERIODS_EXCLUDED_BY_PRAAT','message':'Praat excluye períodos; un jitter bajo puede reflejar solo el subconjunto admitido.',
                         'excluded_periods':candidates-x['accepted_periods_praat']})
    if value is None:
        warnings.append({'code':'JITTER_NOT_CALCULABLE','message':'Get jitter (local) devolvió undefined; no se convierte en cero.'})
    rails=_rail_samples(data)
    quality['digital_rail_samples']=rails
    if rails:
        warnings.append({'code':'POSSIBLE_DIGITAL_CLIPPING','message':'Muestras en los límites digitales; posible saturación.', 'rail_samples':rails})
    r['provenance'].update(pitch_script_sha256=r['provenance']['script_sha256'],
                          script_sha256=hashlib.sha256(script_bytes).hexdigest(),module_version='jitter_v1',
                          output_schema_version='jitter_output_v1',warnings_version='jitter_warnings_v1',
                          pitch_warnings_version='pitch_warnings_v1')
    return r


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('wav',type=Path)
    parser.add_argument('--emission-start',type=float,default=0)
    parser.add_argument('--emission-end',type=float)
    args=parser.parse_args()
    if args.wav.stat().st_size>MAX_BYTES: parser.error('File exceeds 10 MiB')
    print(json.dumps(analyze_jitter(args.wav.read_bytes(),args.emission_start,args.emission_end),indent=2,allow_nan=False))

if __name__=='__main__': main()
