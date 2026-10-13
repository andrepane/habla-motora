"""Native HNR observations; means and frame coverage remain separate."""
import json
from tests.hnr_experiments import observation,noise_ensemble
from tests.hnr_reference import query_object
from tests.synthetic_hnr import make_wav


def make_report():
    cases={}
    for rate,hz in [(48000,100),(48000,200),(48000,400),(44100,100),(44100,200),(44100,400)]:
        data,m=make_wav(frequency=hz,rate=rate)
        c=observation(data,m)
        c['exact_period_samples']=rate/hz if (rate/hz).is_integer() else None
        c['clean_target_pass']=c['coverage_percent']==100 and c['hnr_mean_db'] is not None and c['hnr_mean_db']>=40
        cases[f'clean_{hz}Hz_{rate}']=c
    conditions=[('silence',{'kind':'silence'}),('noise_only',{'kind':'noise_only'}),
                ('tone_silence_tone',{'kind':'gap'}),('gain_0.1',{'snr_db':20,'gain':.1}),
                ('gain_2',{'snr_db':20,'gain':2}),('gain_baseline_20dB',{'snr_db':20}),
                ('low_amplitude_0.001',{'gain':.001}),('low_amplitude_0.0001',{'gain':.0001}),
                ('clipping_gain_10',{'gain':10,'clipping':True}),
                ('weak_center_without_loud_context',{'kind':'weak_center'}),
                ('weak_center_with_loud_context',{'kind':'weak_center','global_context':True}),
                ('harmonics',{'kind':'harmonics'}),('weak_fundamental',{'kind':'weak_fundamental'}),
                ('inharmonic_317Hz',{'kind':'inharmonic'})]
    conditions.extend((f'frequency_{hz}Hz',{'frequency':hz}) for hz in [50,74,76,700])
    for name,options in conditions:
        data,m=make_wav(**options);cases[name]=observation(data,m)
    native_controlled=[]
    for values in [[10]*5,[-200]*5,[10,-200,10,-200,10],[0]*5,[-10]*5,[10,20,30,40,50]]:
        for start,end in [(1.5,4.5),(2.001,2.029),(2.005,2.035)]:
            native_controlled.append({'values_db':values,'start_s':start,'end_s':end,
                'native_get_mean_db':query_object(values,start,end)['hnr_mean_db'],
                'interpretation':'constant-curve exact reference' if len(set(v for v in values if v!=-200))<=1 else 'native characterization; no frame arithmetic reference'})
    return {'module':'hnr_v1','mean_definition':'EXCLUSIVELY native Harmonicity: Get mean; coverage is a separate frame-count statistic',
            'tolerances':{'controlled_exact_reference_db':1e-8,'native_integration_db':1e-6,
                          'coverage_and_counts':'exact under operational definition','gain_change_db':.1,
                          'clean_exact_period_min_db':40,'clean_coverage_percent':100,
                          'noise_trend':'strictly increasing ensemble means at 0,10,20,30,40 dB; 20 fixed seeds, none omitted'},
            'cases':cases,'noise_ensemble':noise_ensemble(),'native_controlled_objects':native_controlled}


if __name__=='__main__':print(json.dumps(make_report(),indent=2,allow_nan=False))
