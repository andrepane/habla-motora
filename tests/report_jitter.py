"""Separate known-time mathematical checks from acoustic characterization."""
import json
from backend.jitter import analyze_jitter
from tests.jitter_reference import query_known_times
from tests.synthetic_jitter import cycle_times,pulse_wav,mathematical_reference,pulse_matching,random_cycle_times
from tests.synthetic_pitch import wav_bytes


def summarize(r):
    return {'provenance':r['provenance'],'analysis_interval':r['analysis_interval'],
            'jitter_local_percent':r['acoustic']['jitter_local_percent'],
            'f0_mean_hz':r['acoustic']['f0_mean_hz'],
            'quality':r['quality']}


def make_report():
    cases={}
    for level in [0,.5,1,2,5]:
        times=cycle_times(level); ref=mathematical_reference(times)
        r=analyze_jitter(pulse_wav(times));c=summarize(r)
        c['mathematical_reference']=ref;c['praat_known_times_no_detector']=query_known_times(times)
        value=c['jitter_local_percent']['value']; target=ref['jitter_local_percent']
        error=None if value is None or target is None else abs(value-target)
        tolerance=max(.05,.1*target) if target is not None else None
        c.update(error_pp=error,tolerance_pp=tolerance,
                 clean_accuracy_pass=error is not None and error<=tolerance,
                 pulse_matching=pulse_matching(times,r['tracking_pulses']))
        cases['jitter_'+str(level)]=c
    base=cycle_times(1)
    variations=[('long_period',cycle_times(1,anomaly='long_period'),{}),
                ('lost_pulse',cycle_times(1,anomaly='lost_pulse'),{}),
                ('added_pulse',cycle_times(1,anomaly='added_pulse'),{}),
                ('gain_0.1',base,{'gain':.1}),('gain_2',base,{'gain':2}),
                ('amplitude_0.001',base,{'gain':.001}),('amplitude_0.0001',base,{'gain':.0001}),
                ('saturation_gain_5',base,{'gain':5,'saturate':True})]
    variations.extend(('random_jitter_'+str(level),random_cycle_times(level),{}) for level in [1,2,5])
    variations.extend(('noise_'+str(db)+'dB',base,{'noise_db':db}) for db in [40,30,20,10])
    for name,times,kwargs in variations:
        r=analyze_jitter(pulse_wav(times,**kwargs));c=summarize(r)
        ref=mathematical_reference(times); value=c['jitter_local_percent']['value']
        c.update(mathematical_reference=ref,
                 error_pp=None if value is None else abs(value-ref['jitter_local_percent']),
                 pulse_matching=pulse_matching(times,r['tracking_pulses']))
        cases[name]=c
    for name,kind,hz in [('silence','silence',200),('noise_only','noise',200),
                         ('pitch_error_700','tone',700),('weak_fundamental_200','weak_fundamental',200)]:
        cases[name]=summarize(analyze_jitter(wav_bytes(kind,frequency=hz)))
    return {'module':'jitter_v1','cases':cases}

if __name__=='__main__': print(json.dumps(make_report(),indent=2,allow_nan=False))
