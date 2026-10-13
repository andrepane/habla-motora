"""Exact observations; mathematical, imposed-pulse and full-route results are separate."""
import json
from backend.shimmer import analyze_shimmer
from tests.shimmer_reference import query_sound,query_tier
from tests.synthetic_shimmer import source,wav_from_cycles,source_reference,independently_extract_pcm
from tests.synthetic_jitter import pulse_matching
from tests.synthetic_pitch import wav_bytes


def summarize(data,times=None,amplitudes=None,clean=False):
    r=analyze_shimmer(data)
    value=r['acoustic']['shimmer_local_percent']['value']
    out={'provenance':r['provenance'],'analysis_interval':r['analysis_interval'],
         'shimmer_local_percent':value,'f0_mean_hz':r['acoustic']['f0_mean_hz']['value'],
         'f0_coverage_percent':r['quality']['f0_coverage_percent']['value'],
         'pulse_audit':r['quality']['pulse_audit'],'shimmer_audit':r['quality']['shimmer_audit'],
         'amplitude_diagnostics':r['quality']['amplitude_diagnostics'],
         'digital_rail_samples_full_file':r['quality']['digital_rail_samples'],
         'warnings':r['quality']['technical_warnings']}
    if times is not None:
        reference=source_reference(times,amplitudes)
        target=reference['shimmer_local_percent']
        imposed=query_sound(data,times)
        independent=independently_extract_pcm(data,times)
        match=pulse_matching(times,r['tracking_pulses'])
        inside=[(t,a) for t,a in zip(times,amplitudes) if 1.5<=t<=4.5][1:-1]
        # Tier-only query is used for clean constant-period source amplitude sequences.
        if clean:
            tier=query_tier([t for t,a in inside],[a for t,a in inside])['shimmer_local_percent']
            out['tier_known_amplitudes_percent']=tier
            out['tier_error_pp']=abs(tier-target)
        out.update(mathematical_reference=reference,
                   error_pp=abs(value-target) if value is not None and target is not None else None,
                   imposed_pulses_shimmer_percent=imposed['shimmer_local_percent'],
                   imposed_pulses_amplitude_count=len(imposed['amplitudes']),
                   independent_pcm_shimmer_percent=independent['shimmer_local_percent'],
                   imposed_vs_independent_pcm_error_pp=abs(imposed['shimmer_local_percent']-independent['shimmer_local_percent']) if imposed['shimmer_local_percent'] is not None and independent['shimmer_local_percent'] is not None else None,
                   pulse_matching=match)
        if clean:
            tolerance=max(.05,.1*abs(target))
            out.update(full_route_tolerance_pp=tolerance,
                       full_route_accuracy_pass=value is not None and abs(value-target)<=tolerance and match['missing']==match['extra']==0,
                       imposed_clean_tolerance_pp=max(.01,.01*abs(target)),
                       imposed_clean_error_pp=abs(imposed['shimmer_local_percent']-target))
    return out


def make_report():
    cases={}
    for level in [0,.5,1,2,5]:
        t,a=source(level);cases['shimmer_'+str(level)]=summarize(wav_from_cycles(t,a),t,a,clean=True)
    for level in [1,2,5]:
        t,a=source(level,random_amplitudes=True)
        cases['random_'+str(level)]=summarize(wav_from_cycles(t,a),t,a,clean=True)
    t,a=source(1)
    variations=[('gain_0.1',{'gain':.1}),('gain_2',{'gain':2}),
                ('low_amplitude_0.001',{'gain':.001}),('low_amplitude_0.0001',{'gain':.0001}),
                ('clipping_gain_5',{'gain':5,'clipping':True})]
    variations.extend(('noise_'+str(db)+'dB',{'noise_db':db}) for db in [40,30,20,10])
    for name,options in variations:
        cases[name]=summarize(wav_from_cycles(t,a,**options),t,a)
    for anomaly in ['lost_pulse','added_pulse','shifted_pulse','long_period','amplitude_spike']:
        t,a=source(1,anomaly=anomaly);cases[anomaly]=summarize(wav_from_cycles(t,a),t,a)
    for name,kind,hz in [('silence','silence',200),('noise_only','noise',200),
                         ('pitch_error_700','tone',700),('weak_fundamental_200','weak_fundamental',200)]:
        cases[name]=summarize(wav_bytes(kind,frequency=hz))
    wrong_pulses={}
    true_times,base_amplitudes=source(1);unchanged=wav_from_cycles(true_times,base_amplitudes)
    for error in ['lost_pulse','added_pulse','shifted_pulse']:
        times,_=source(1,anomaly=error)
        p=query_sound(unchanged,times);ind=independently_extract_pcm(unchanged,times)
        wrong_pulses[error]={'shimmer_local_percent':p['shimmer_local_percent'],
            'pulses_in_interval':p['pulses_in_interval'],'accepted_periods_praat':p['accepted_periods_praat'],
            'amplitudes_extracted_praat':len(p['amplitudes']),
            'independent_pcm_shimmer_percent':ind['shimmer_local_percent']}
    boundaries={}
    for factor in [1.3-1e-6,1.3,1.3+1e-6]:
        t=[2,2.005,2.005+.005*factor,2.010+.005*factor,2.015+.005*factor]
        a=[1,1.01,1,1.01,1];data=wav_from_cycles(t,a)
        p=query_sound(data,t);ind=independently_extract_pcm(data,t)
        boundaries['period_factor_'+str(factor)]={'native_amplitudes':len(p['amplitudes']),
            'independent_amplitudes':len(ind['points']),'native_shimmer_percent':p['shimmer_local_percent'],
            'independent_shimmer_percent':ind['shimmer_local_percent']}
    for factor in [1.6-1e-6,1.6,1.6+1e-6]:
        boundaries['amplitude_factor_'+str(factor)]=query_tier([2,2.005],[1,factor])
    for period in [.8/600-1e-8,.8/600,.8/600+1e-8,1.25/75-1e-8,1.25/75,1.25/75+1e-8]:
        t=[2+i*period for i in range(5)];data=wav_from_cycles(t,[1,1.01,1,1.01,1])
        p=query_sound(data,t);ind=independently_extract_pcm(data,t)
        boundaries['period_'+str(period)]={'native_amplitudes':len(p['amplitudes']),
            'independent_amplitudes':len(ind['points']),'native_shimmer_percent':p['shimmer_local_percent'],
            'independent_shimmer_percent':ind['shimmer_local_percent']}
    return {'module':'shimmer_v1','tolerances_pp':{
        'mathematical':1e-8,'integration':'1e-6 * max(1, abs(reference_percent))',
        'imposed_clean':'max(0.01, 0.01 * abs(reference_percent))',
        'full_clean':'max(0.05, 0.10 * abs(reference_percent))','gain_change':.01},
        'cases':cases,'boundaries':boundaries,'wrong_imposed_pulses_unchanged_wav':wrong_pulses}


if __name__=='__main__':
    print(json.dumps(make_report(),indent=2,allow_nan=False))
