import hashlib
import json
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.shimmer import SCRIPT, _parse, amplitude_diagnostics, analyze_shimmer
from backend.praat_runner import AnalysisError, CONFIG_PATH, _run
from tests.shimmer_reference import query_sound, query_tier
from tests.synthetic_shimmer import (source, wav_from_cycles, shimmer_formula,
                                     source_reference, independently_extract_pcm)
from tests.synthetic_jitter import pulse_matching
from tests.synthetic_pitch import wav_bytes

LEVELS = [0, .5, 1, 2, 5]


@pytest.mark.parametrize('times,amplitudes,expected', [
    ([2,2.005],[1,1],0),
    ([2,2.005,2.01],[1,1.01,1],100*.01/1.005),
    ([2,2.005,2.01],[1,1.6,1],100*.6/1.3),
    ([2,2.005,2.01],[1,2,2],0), # excluded pair, denominator still includes amplitude 1
    ([2,2.005],[1,2],None),
    ([2],[1],None),
    ([2,2.025],[1,1.01],None),
    ([2,2.005,2.030,2.035],[1,1.01,2,2.01],100*.01/(4.01/3)),
])
def test_small_analytical_formula(times, amplitudes, expected):
    independent = shimmer_formula(times, amplitudes)['shimmer_local_percent']
    native = query_tier(times, amplitudes)['shimmer_local_percent']
    if expected is None:
        assert independent is None and native is None
    else:
        assert independent == pytest.approx(expected, abs=1e-8)
        assert native == pytest.approx(expected, abs=1e-8)


@pytest.mark.parametrize('level', LEVELS)
def test_known_amplitude_tier_no_detector(level):
    times, amplitudes = source(level)
    selected = [(t,a) for t,a in zip(times,amplitudes) if 1.5<=t<=4.5][1:-1]
    mathematical = source_reference(times, amplitudes)['shimmer_local_percent']
    native = query_tier([t for t,a in selected],[a for t,a in selected])['shimmer_local_percent']
    assert abs(native-mathematical) <= 1e-8


@pytest.mark.parametrize('level', [1,2,5])
def test_random_amplitude_tier_no_detector(level):
    times, amplitudes = source(level,random_amplitudes=True)
    selected = [(t,a) for t,a in zip(times,amplitudes) if 1.5<=t<=4.5][1:-1]
    native = query_tier([t for t,a in selected],[a for t,a in selected])['shimmer_local_percent']
    assert abs(native-source_reference(times,amplitudes)['shimmer_local_percent']) <= 1e-8


@pytest.mark.parametrize('level', LEVELS)
def test_imposed_pulses_clean_extraction_accuracy(level):
    times, amplitudes = source(level);data=wav_from_cycles(times,amplitudes)
    native = query_sound(data,times)
    independent = independently_extract_pcm(data,times)
    value = native['shimmer_local_percent']
    reference = source_reference(times,amplitudes)['shimmer_local_percent']
    assert abs(value-reference) <= max(.01,.01*abs(reference))
    assert abs(value-independent['shimmer_local_percent']) <= 1e-8
    assert len(native['amplitudes']) == len(independent['points'])
    for a,b in zip(native['amplitudes'],independent['points']):
        assert a['time_s'] == b['time_s']
        assert a['amplitude_rms'] == pytest.approx(b['amplitude_rms'],abs=1e-12)
    assert abs(100*native['tier_shimmer_ratio']-value) <= 1e-6*max(1,abs(value))


@pytest.mark.parametrize('level', LEVELS)
def test_clean_full_route_accuracy(level):
    times, amplitudes=source(level);r=analyze_shimmer(wav_from_cycles(times,amplitudes))
    expected=source_reference(times,amplitudes)['shimmer_local_percent']
    value=r['acoustic']['shimmer_local_percent']['value']
    assert value is not None
    assert abs(value-expected) <= max(.05,.10*abs(expected))
    match=pulse_matching(times,r['tracking_pulses'])
    assert match['missing']==match['extra']==0


@pytest.mark.parametrize('level', [1,2,5])
def test_random_full_route_accuracy(level):
    times,amplitudes=source(level,random_amplitudes=True)
    r=analyze_shimmer(wav_from_cycles(times,amplitudes))
    expected=source_reference(times,amplitudes)['shimmer_local_percent']
    assert abs(r['acoustic']['shimmer_local_percent']['value']-expected)<=max(.05,.10*abs(expected))
    match=pulse_matching(times,r['tracking_pulses'])
    assert match['missing']==match['extra']==0


@pytest.mark.parametrize('gain', [.1,2])
def test_gain_invariance_target(gain):
    times,a=source(1)
    before=analyze_shimmer(wav_from_cycles(times,a));after=analyze_shimmer(wav_from_cycles(times,a,gain=gain))
    assert abs(before['acoustic']['shimmer_local_percent']['value']-after['acoustic']['shimmer_local_percent']['value'])<=.01
    match=pulse_matching(times,after['tracking_pulses'])
    assert match['missing']==match['extra']==0


@pytest.mark.parametrize('db', [40,30])
def test_noise_high_snr_accuracy_target(db):
    times,a=source(1);r=analyze_shimmer(wav_from_cycles(times,a,noise_db=db))
    expected=source_reference(times,a)['shimmer_local_percent']
    assert abs(r['acoustic']['shimmer_local_percent']['value']-expected)<=max(.05,.10*abs(expected))


@pytest.mark.parametrize('db',[20,10])
def test_noise_low_snr_characterization(db):
    times,a=source(1);data=wav_from_cycles(times,a,noise_db=db)
    r=analyze_shimmer(data);known=query_sound(data,times)
    assert r['acoustic']['shimmer_local_percent']['status']=='experimental_pulse_reliability_unverified'
    assert known['shimmer_local_percent'] is not None
    json.dumps(r,allow_nan=False)


@pytest.mark.parametrize('gain', [.001,.0001])
def test_low_amplitude_warning_and_finite_preservation(gain):
    times,a=source(1);r=analyze_shimmer(wav_from_cycles(times,a,gain=gain))
    assert r['acoustic']['shimmer_local_percent']['value'] is not None
    assert 'LOW_DIGITAL_AMPLITUDE' in [w['code'] for w in r['quality']['technical_warnings']]


def test_clipping_warning():
    times,a=source(1);r=analyze_shimmer(wav_from_cycles(times,a,gain=5,clipping=True))
    assert r['quality']['amplitude_diagnostics']['digital_rail_samples_in_interval']>0
    assert r['quality']['digital_rail_samples']>=r['quality']['amplitude_diagnostics']['digital_rail_samples_in_interval']
    assert 'POSSIBLE_DIGITAL_CLIPPING' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('anomaly',['lost_pulse','added_pulse','shifted_pulse','long_period','amplitude_spike'])
def test_imposed_pulse_and_amplitude_anomalies(anomaly):
    times,a=source(1,anomaly=anomaly);data=wav_from_cycles(times,a)
    known=query_sound(data,times);independent=independently_extract_pcm(data,times)
    assert len(known['amplitudes'])==len(independent['points'])
    assert abs(known['shimmer_local_percent']-independent['shimmer_local_percent'])<=1e-8
    r=analyze_shimmer(data)
    assert 'PULSE_RELIABILITY_UNVERIFIED' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('factor', [1.6-1e-6,1.6,1.6+1e-6])
def test_amplitude_factor_boundary(factor):
    times=[2,2.005];amplitudes=[1,factor]
    native=query_tier(times,amplitudes)['shimmer_local_percent']
    independent=shimmer_formula(times,amplitudes)['shimmer_local_percent']
    if factor>1.6:
        assert native is None and independent is None
    else:
        assert abs(native-independent)<=1e-8


@pytest.mark.parametrize('factor', [1.3-1e-6,1.3,1.3+1e-6])
def test_period_factor_boundary_no_detector(factor):
    # Exported decimal times are evaluated as binary64 by both extractors; at-boundary result is recorded.
    times=[2,2.005,2.005+.005*factor,2.010+.005*factor,2.015+.005*factor]
    data=wav_from_cycles(times,[1,1.01,1,1.01,1])
    native=query_sound(data,times);independent=independently_extract_pcm(data,times)
    assert len(native['amplitudes'])==len(independent['points'])
    if independent['shimmer_local_percent'] is None:
        assert native['shimmer_local_percent'] is None
    else:
        assert abs(native['shimmer_local_percent']-independent['shimmer_local_percent'])<=1e-8


@pytest.mark.parametrize('period',[.8/600-1e-8,.8/600,.8/600+1e-8,1.25/75-1e-8,1.25/75,1.25/75+1e-8])
def test_period_bounds_no_detector(period):
    times=[2+i*period for i in range(5)]
    data=wav_from_cycles(times,[1,1.01,1,1.01,1])
    native=query_sound(data,times);independent=independently_extract_pcm(data,times)
    assert len(native['amplitudes'])==len(independent['points'])
    if independent['shimmer_local_percent'] is None:
        assert native['shimmer_local_percent'] is None
    else:
        assert abs(native['shimmer_local_percent']-independent['shimmer_local_percent'])<=1e-8


@pytest.mark.parametrize('kind',['silence','noise'])
def test_undefined_not_zero(kind):
    r=analyze_shimmer(wav_bytes(kind))
    assert r['acoustic']['shimmer_local_percent']['value'] is None
    assert r['acoustic']['shimmer_local_percent']['reason']=='praat_undefined'
    assert r['tracking_amplitudes']==[]
    assert 'SHIMMER_NOT_CALCULABLE' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('kind,hz',[('tone',700),('weak_fundamental',200)])
def test_pitch_errors_cannot_certify_low_shimmer(kind,hz):
    r=analyze_shimmer(wav_bytes(kind,frequency=hz))
    assert r['acoustic']['shimmer_local_percent']['status']=='experimental_pulse_reliability_unverified'
    assert 'PULSE_RELIABILITY_UNVERIFIED' in [w['code'] for w in r['quality']['technical_warnings']]


def test_separate_native_script_integration():
    times,a=source(1);data=wav_from_cycles(times,a);result=analyze_shimmer(data)
    with tempfile.TemporaryDirectory() as temp:
        wav=Path(temp)/'input.wav';wav.write_bytes(data)
        script=Path(temp)/'reference.praat'
        script.write_text('''form Reference
 sentence Wav
endform
Read from file: wav$
s = selected("Sound")
To Pitch (raw cross-correlation): 0.005,75,600,15,"no",0.03,0.45,0.01,0.35,0.14
p = selected("Pitch")
selectObject: s,p
To PointProcess (cc)
pp = selected("PointProcess")
selectObject: s,pp
v = Get shimmer (local): 1.5,4.5,0.8/600,1.25/75,1.3,1.6
writeInfoLine: fixed$(100*v,17)
''')
        expected=float(_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(script),str(wav)]))
    value=result['acoustic']['shimmer_local_percent']['value']
    assert abs(value-expected)<=1e-6*max(1,abs(expected))


def test_provenance_and_native_audit():
    times,a=source(1);data=wav_from_cycles(times,a);r=analyze_shimmer(data);p=r['provenance']
    assert p['configuration_sha256']==hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()=='94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729'
    assert p['file_sha256']==hashlib.sha256(data).hexdigest()
    assert p['script_sha256']==hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert (p['module_version'],p['output_schema_version'],p['warnings_version'])==('shimmer_v1','shimmer_output_v1','shimmer_warnings_v1')
    assert p['praat_version']=='6.4.27'
    for name in ['jitter','pitch','duration']:
        assert p[name+'_script_sha256']==hashlib.sha256(Path('praat',{'duration':'smoke_test','pitch':'pitch_v1','jitter':'jitter_v1'}[name]+'.praat').read_bytes()).hexdigest()
    audit=r['quality']['shimmer_audit']
    assert audit['shimmer_pairs_used']=={'value':None,'reason':'not_implemented'}
    assert audit['amplitudes_extracted_praat']==len(r['tracking_amplitudes'])
    assert audit['amplitudes_not_extracted']==audit['interior_pulses_candidate_for_amplitude']-len(r['tracking_amplitudes'])
    assert audit['tier_shimmer_local_percent']==pytest.approx(r['acoustic']['shimmer_local_percent']['value'],abs=1e-6)


def test_preserve_finite_output_with_minimal_pulses():
    pulses=[{'pulse_index':i+1,'time_s':2+i*.005} for i in range(4)]
    payload={'pulses':pulses,'pulses_in_interval':4,'accepted_periods_praat':3,'shimmer_local_ratio':0.0,
             'tier_shimmer_ratio':0.0,'amplitudes':[{'amplitude_index':i+1,'time_s':pulses[i+1]['time_s'],'amplitude_rms':.1} for i in range(2)]}
    x,_,_=_parse(json.dumps(payload),1.5,4.5)
    assert x['shimmer_local_ratio']==0


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1])
def test_invalid_numeric_output_rejected(value):
    with pytest.raises(AnalysisError):
        _parse(json.dumps({'shimmer_local_ratio':value}),1.5,4.5)


def test_shimmer_api_and_short_emission():
    times,a=source(.5)
    with TestClient(app) as client:
        response=client.post('/shimmer',files={'file':('known.wav',wav_from_cycles(times,a),'audio/wav')})
        short=client.post('/shimmer',files={'file':('short.wav',Path("tests/fixtures/tone_2s.wav").read_bytes(),'audio/wav')})
    assert response.status_code==200
    assert abs(response.json()['acoustic']['shimmer_local_percent']['value']-.5)<=.05
    assert short.status_code==422


@pytest.mark.parametrize('width',[2,3,4])
def test_pcm_quantization_warning_diagnostics(width):
    import io, wave
    data=io.BytesIO()
    with wave.open(data,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(width);wav.setframerate(44100)
        wav.writeframes((3).to_bytes(width,'little',signed=True)*441)
    diag=amplitude_diagnostics(data.getvalue(),0,.01)
    assert diag['sample_count']==441 and diag['rms_quantization_steps']==3
    assert diag['digital_rail_samples_in_interval']==0


@pytest.mark.parametrize('error',['lost_pulse','added_pulse','shifted_pulse'])
def test_wrong_imposed_pulses_on_unchanged_wav(error):
    true_times,a=source(1);data=wav_from_cycles(true_times,a)
    wrong_times,_=source(1,anomaly=error)
    native=query_sound(data,wrong_times);independent=independently_extract_pcm(data,wrong_times)
    assert len(native['amplitudes'])==len(independent['points'])
    if independent['shimmer_local_percent'] is None:
        assert native['shimmer_local_percent'] is None
    else:
        assert abs(native['shimmer_local_percent']-independent['shimmer_local_percent'])<=1e-8
