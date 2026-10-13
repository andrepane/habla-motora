"""Machine-readable observations; characterization cases are not acceptance claims."""
import hashlib
import json
import math
from backend.pitch import analyze_pitch
from tests.synthetic_pitch import wav_bytes


def make_report():
    cases = [('tone_100','tone',100),('tone_200','tone',200),('tone_400','tone',400),
             ('modulated','modulated',200),('tone_silence_tone','gap',200),
             ('silence','silence',200),('noise_seed_20261013','noise',200),
             ('below_range_50','tone',50),('above_range_700','tone',700),
             ('weak_fundamental_200','weak_fundamental',200)]
    report = {'module':'pitch_v1','cases':{}}
    for name,kind,hz in cases:
        r = analyze_pitch(wav_bytes(kind,frequency=hz))
        summary = {k:r[k] for k in ('provenance','analysis_interval','acoustic','quality')}
        if kind=='modulated':
            errors = [f['f0_hz']-(200+20*math.sin(2*math.pi*2*f['time_s']))
                      for f in r['tracking_frames'] if f['f0_hz'] is not None]
            summary['known_signal_comparison'] = {
                'mean_reference_hz':200,'sd_continuous_reference_hz':math.sqrt(200),
                'max_absolute_frame_error_hz':max(map(abs,errors)),
                'rmse_frame_hz':math.sqrt(sum(e*e for e in errors)/len(errors)),
                'pointwise_exploratory_limit_hz':0.5,
                'pointwise_exploratory_pass':max(map(abs,errors))<=0.5}
        report['cases'][name] = summary
    return report


if __name__=='__main__':
    print(json.dumps(make_report(),indent=2,allow_nan=False))
