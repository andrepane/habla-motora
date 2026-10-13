import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.jitter import SCRIPT, _parse, analyze_jitter
from backend.praat_runner import AnalysisError, CONFIG_PATH, _run
from tests.jitter_reference import query_known_times
from tests.synthetic_jitter import cycle_times,pulse_wav,mathematical_reference,pulse_matching,random_cycle_times
from tests.synthetic_pitch import wav_bytes


@pytest.mark.parametrize('level',[0,.5,1,2,5])
def test_mathematical_reference_without_acoustic_detector(level):
    times=cycle_times(level)
    mathematical=mathematical_reference(times)
    praat=query_known_times(times)
    assert abs(praat['jitter_local_percent']-mathematical['jitter_local_percent'])<=1e-8
    assert praat['accepted_periods']==mathematical['accepted_periods']


@pytest.mark.parametrize('anomaly',['long_period','lost_pulse','added_pulse'])
def test_mathematical_exclusions_without_acoustic_detector(anomaly):
    times=cycle_times(1,anomaly=anomaly)
    mathematical=mathematical_reference(times);praat=query_known_times(times)
    assert abs(praat['jitter_local_percent']-mathematical['jitter_local_percent'])<=1e-8
    assert praat['accepted_periods']==mathematical['accepted_periods']


@pytest.mark.parametrize('times,expected',[
    ([2,2.005,2.01],0),
    ([2,2.005,2.01005],100*0.00005/0.005025),
    ([2,2.005,2.015,2.020,2.025],0),
    ([2,2.005],None),
    ([2],None),
    ([2,2.005,2.015],None),
])
def test_small_analytically_solved_pointprocesses(times,expected):
    ref=mathematical_reference(times);p=query_known_times(times)
    if expected is None:
        assert ref['jitter_local_percent'] is None and p['jitter_local_percent'] is None
    else:
        assert ref['jitter_local_percent']==pytest.approx(expected,abs=1e-8)
        assert p['jitter_local_percent']==pytest.approx(expected,abs=1e-8)


@pytest.mark.parametrize('level',[
    0,.5,1,
    pytest.param(2,marks=pytest.mark.xfail(strict=True,raises=AssertionError,reason='Alternating waveform: v1 tracks every second source pulse')),
    pytest.param(5,marks=pytest.mark.xfail(strict=True,raises=AssertionError,reason='Alternating waveform: v1 tracks every second source pulse')),
])
def test_clean_known_jitter_accuracy_target(level):
    times=cycle_times(level);r=analyze_jitter(pulse_wav(times))
    reference=mathematical_reference(times)['jitter_local_percent']
    value=r['acoustic']['jitter_local_percent']['value']
    assert value is not None
    assert abs(value-reference)<=max(.05,.1*reference)
    match=pulse_matching(times,r['tracking_pulses'])
    assert match['missing']==match['extra']==0


@pytest.mark.parametrize('hz',[100,200,400])
def test_zero_jitter_target(hz):
    r=analyze_jitter(pulse_wav(cycle_times(0,frequency=hz)))
    assert r['acoustic']['jitter_local_percent']['value']<=.05


@pytest.mark.parametrize('gain',[.1,2])
def test_constant_gain_robustness_target(gain):
    times=cycle_times(1)
    before=analyze_jitter(pulse_wav(times));after=analyze_jitter(pulse_wav(times,gain=gain))
    assert abs(before['acoustic']['jitter_local_percent']['value']-after['acoustic']['jitter_local_percent']['value'])<=.01
    match=pulse_matching(times,after['tracking_pulses'])
    assert match['missing']==match['extra']==0


@pytest.mark.parametrize('db',[40,30,20,10])
def test_noise_characterization_no_unproven_accuracy_claim(db):
    r=analyze_jitter(pulse_wav(cycle_times(1),noise_db=db))
    assert r['quality']['pulse_audit']['accepted_periods_praat']<=r['quality']['pulse_audit']['candidate_periods']
    assert 'PULSE_RELIABILITY_UNVERIFIED' in [w['code'] for w in r['quality']['technical_warnings']]
    json.dumps(r,allow_nan=False)


@pytest.mark.parametrize('gain',[.001,.0001])
def test_low_amplitude_characterization_keeps_finite_praat_value(gain):
    r=analyze_jitter(pulse_wav(cycle_times(1),gain=gain))
    assert r['acoustic']['jitter_local_percent']['value'] is not None
    assert r['acoustic']['jitter_local_percent']['status']=='experimental_pulse_reliability_unverified'


def test_saturation_warning():
    r=analyze_jitter(pulse_wav(cycle_times(1),gain=5,saturate=True))
    assert r['quality']['digital_rail_samples']>0
    assert 'POSSIBLE_DIGITAL_CLIPPING' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('kind',['silence','noise'])
def test_undefined_keeps_null(kind):
    r=analyze_jitter(wav_bytes(kind))
    assert r['acoustic']['jitter_local_percent']['value'] is None
    assert r['acoustic']['jitter_local_percent']['reason']=='praat_undefined'
    assert r['quality']['pulse_audit']['pulses_in_interval']==0


@pytest.mark.parametrize('anomaly',['long_period','lost_pulse','added_pulse'])
def test_abnormal_pulse_acoustic_characterization(anomaly):
    r=analyze_jitter(pulse_wav(cycle_times(1,anomaly=anomaly)))
    a=r['quality']['pulse_audit']
    assert a['candidate_periods']==max(0,a['pulses_in_interval']-1)
    if a['accepted_periods_praat']<a['candidate_periods']:
        assert 'PERIODS_EXCLUDED_BY_PRAAT' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('kind,hz',[('tone',700),('weak_fundamental',200)])
def test_pitch_error_characterization(kind,hz):
    r=analyze_jitter(wav_bytes(kind,frequency=hz))
    assert r['acoustic']['jitter_local_percent']['value'] is not None
    assert 'PULSE_RELIABILITY_UNVERIFIED' in [w['code'] for w in r['quality']['technical_warnings']]


def test_same_engine_reference_integration():
    data=pulse_wav(cycle_times(1));r=analyze_jitter(data)
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
j = Get jitter (local): 1.5,4.5,0.8/600,1.25/75,1.3
n = Get number of periods: 1.5,4.5,0.8/600,1.25/75,1.3
writeInfoLine: fixed$(100*j,17)," ",n
''')
        output=_run([os.environ.get('PRAAT_EXECUTABLE','praat'),'--run',str(script),str(wav)]).split()
    assert r['acoustic']['jitter_local_percent']['value']==pytest.approx(float(output[0]),abs=1e-6)
    assert r['quality']['pulse_audit']['accepted_periods_praat']==int(output[1])


def test_provenance_pulses_periods_and_optional_pairs():
    data=pulse_wav(cycle_times(1));r=analyze_jitter(data);p=r['provenance']
    assert p['configuration_sha256']==hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()=='94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729'
    assert p['file_sha256']==hashlib.sha256(data).hexdigest()
    assert p['script_sha256']==hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert (p['module_version'],p['output_schema_version'],p['warnings_version'])==('jitter_v1','jitter_output_v1','jitter_warnings_v1')
    assert r['quality']['pulse_audit']['jitter_pairs_used']=={'value':None,'reason':'not_implemented'}
    assert r['quality']['accepted_cycles']['value']==r['quality']['pulse_audit']['accepted_periods_praat']
    assert len(r['tracking_periods'])==r['quality']['pulse_audit']['candidate_periods']
    assert r['tracking_pulses'][0]['time_s']<r['analysis_interval']['start_s']


def test_finite_praat_value_is_not_overwritten_for_few_pulses():
    raw=json.dumps({'pulses':[{'pulse_index':1,'time_s':2},{'pulse_index':2,'time_s':2.005},{'pulse_index':3,'time_s':2.01}],
                    'pulses_in_interval':3,'accepted_periods_praat':2,'jitter_local_ratio':0.0})
    x,inside,n=_parse(raw,1.5,4.5)
    assert x['jitter_local_ratio']==0 and n==2


def test_invalid_praat_numeric_output_rejected():
    with pytest.raises(AnalysisError): _parse('{"jitter_local_ratio":NaN}',1.5,4.5)


def test_jitter_api():
    with TestClient(app) as client:
        response=client.post('/jitter',files={'file':('known.wav',pulse_wav(cycle_times(.5)),'audio/wav')},
                             data={'emission_start_s':'0','emission_end_s':'6'})
    assert response.status_code==200
    assert abs(response.json()['acoustic']['jitter_local_percent']['value']-.5)<=.05


@pytest.mark.parametrize('level',[1,2,5])
def test_random_known_times_mathematical_reference(level):
    times=random_cycle_times(level)
    ref=mathematical_reference(times);praat=query_known_times(times)
    assert abs(ref['jitter_local_percent']-praat['jitter_local_percent'])<=1e-8
    assert ref['accepted_periods']==praat['accepted_periods']


@pytest.mark.parametrize('level',[1,2,pytest.param(5,marks=pytest.mark.xfail(strict=True,raises=AssertionError,
    reason='Random 5% source exceeds the unchanged clean jitter accuracy target and loses pulses'))])
def test_random_source_clean_accuracy_target(level):
    times=random_cycle_times(level);r=analyze_jitter(pulse_wav(times))
    expected=mathematical_reference(times)['jitter_local_percent']
    assert abs(r['acoustic']['jitter_local_percent']['value']-expected)<=max(.05,.1*expected)
    match=pulse_matching(times,r['tracking_pulses'])
    assert match['missing']==match['extra']==0
