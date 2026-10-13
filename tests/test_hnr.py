import hashlib
import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.hnr import SCRIPT,_parse,analyze_hnr
from backend.praat_runner import AnalysisError,CONFIG_PATH
from tests.hnr_reference import query_object,query_sound
from tests.synthetic_hnr import make_wav,SEEDS,SNR_LEVELS,fixed_lag_reference
from tests.hnr_experiments import noise_ensemble as run_noise_ensemble


@pytest.mark.parametrize('value',[-150,-10,0,10,150])
@pytest.mark.parametrize('bounds',[(1.5,4.5),(2.001,2.029)])
def test_constant_controlled_harmonicity_native_semantics(value,bounds):
    # Constant curves have unambiguous temporal means, even at displaced interval boundaries.
    native=query_object([value]*5,*bounds)
    assert native['hnr_mean_db']==pytest.approx(value,abs=1e-8)


@pytest.mark.parametrize('values,expected',[([-200]*5,None),([10,-200,10,-200,10],10),([-200,0,-200,0,-200],0)])
def test_controlled_marker_exclusion_with_constant_remainder(values,expected):
    native=query_object(values)['hnr_mean_db']
    if expected is None:assert native is None
    else:assert native==pytest.approx(expected,abs=1e-8)


@pytest.mark.parametrize('rate,hz',[
    pytest.param(48000,100,marks=pytest.mark.xfail(strict=True,raises=AssertionError,
        reason='Frozen clean >=40 dB target unmet: native cc at 100 Hz/48000 reports about 33.74 dB')),
    (48000,200),(48000,400),
    pytest.param(44100,100,marks=pytest.mark.xfail(strict=True,raises=AssertionError,
        reason='Frozen clean >=40 dB target unmet: native cc at 100 Hz/44100 reports about 33.25 dB')),
])
def test_exact_period_clean_target(rate,hz):
    data,_=make_wav(frequency=hz,rate=rate);r=analyze_hnr(data)
    assert r['quality']['hnr_coverage_percent']['value']==100
    assert r['acoustic']['hnr_mean_db']['value']>=40


@pytest.mark.parametrize('kind,snr',[('tone',20),('silence',None),('gap',None),('noise_only',None)])
def test_separate_native_script_integration(kind,snr):
    data,_=make_wav(kind=kind,snr_db=snr)
    r=analyze_hnr(data);native=query_sound(data)
    actual=r['acoustic']['hnr_mean_db']['value'];expected=native['hnr_mean_db']
    if expected is None:assert actual is None
    else:assert abs(actual-expected)<=1e-6
    frames=r['tracking_hnr_frames']
    assert len(frames)==len(native['frames'])
    for a,b in zip(frames,native['frames']):
        assert a['frame_index']==b['frame_index'] and a['time_s']==b['time_s']
        if b['praat_raw_hnr_db'] is None:assert a['praat_raw_hnr_db'] is None
        else:assert abs(a['praat_raw_hnr_db']-b['praat_raw_hnr_db'])<=1e-6
        assert a['valid']==(b['praat_raw_hnr_db'] is not None and b['praat_raw_hnr_db']!=-200)


@pytest.mark.parametrize('kind',['tone','gap','silence','noise_only'])
def test_operational_counts_and_coverage_exact(kind):
    data,_=make_wav(kind=kind);r=analyze_hnr(data)
    frames=r['tracking_hnr_frames'];q=r['quality'];start,end=r['analysis_interval']['start_s'],r['analysis_interval']['end_s']
    assert all(start<=f['time_s']<=end for f in frames)
    assert q['hnr_total_frames']==len(frames)
    grid=q['hnr_object_grid']
    expected_indices=[i for i in range(1,grid['object_frames']+1)
                      if start <= grid['first_frame_center_s']+(i-1)*grid['time_step_s'] <= end]
    assert [f['frame_index'] for f in frames]==expected_indices
    valid=sum(f['praat_raw_hnr_db'] is not None and f['praat_raw_hnr_db']!=-200 for f in frames)
    assert q['hnr_valid_frames']==valid and q['hnr_excluded_frames']==len(frames)-valid
    assert q['hnr_coverage_percent']['value']==100.0*valid/len(frames)


@pytest.mark.parametrize('gain',[.1,2])
def test_gain_invariance_fixed_target(gain):
    data,_=make_wav(snr_db=20);scaled,_=make_wav(snr_db=20,gain=gain)
    before=analyze_hnr(data);after=analyze_hnr(scaled)
    assert abs(before['acoustic']['hnr_mean_db']['value']-after['acoustic']['hnr_mean_db']['value'])<=.1
    assert [f['valid'] for f in before['tracking_hnr_frames']]==[f['valid'] for f in after['tracking_hnr_frames']]


@pytest.fixture(scope='module')
def ensemble():return run_noise_ensemble()


def test_twenty_seed_noise_trend_fixed_target(ensemble):
    assert SEEDS==tuple(range(5000,5020))
    means=[]
    for level in SNR_LEVELS:
        observations=ensemble[str(level)]
        assert len(observations['runs'])==20
        assert observations['all_realizations_defined']
        assert [r['source']['seed'] for r in observations['runs']]==list(SEEDS)
        means.append(observations['mean_hnr_db'])
    assert all(a<b for a,b in zip(means,means[1:]))


@pytest.mark.parametrize('level',SNR_LEVELS)
def test_known_component_snr_construction(level,ensemble):
    # This validates signal construction, NOT equality between acoustic HNR and SNR.
    for r in ensemble[str(level)]['runs']:
        assert abs(r['source']['generated_component_snr_db']-level)<=1e-8
        assert r['provenance']['module_version']=='hnr_v1'


@pytest.mark.parametrize('gain',[.001,.0001])
def test_low_amplitude_characterization_no_rejection(gain):
    data,_=make_wav(gain=gain);r=analyze_hnr(data)
    assert r['acoustic']['hnr_mean_db']['status']=='experimental_periodicity_reliability_unverified'
    # The lower gain should warn; gain .001 can still exceed ten PCM steps for a sinusoid.
    rms=r['quality']['amplitude_diagnostics']['rms_quantization_steps']
    assert ('LOW_DIGITAL_AMPLITUDE' in [w['code'] for w in r['quality']['technical_warnings']])==(rms<10)
    json.dumps(r,allow_nan=False)


def test_clipping_warning_not_rejection():
    data,_=make_wav(gain=10,clipping=True);r=analyze_hnr(data)
    assert r['quality']['digital_rail_samples_full_file']>0
    assert r['quality']['amplitude_diagnostics']['digital_rail_samples_in_interval']>0
    assert 'POSSIBLE_DIGITAL_CLIPPING' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('hz',[50,74,76,700])
def test_frequency_characterization_no_f0_ceiling(hz):
    data,_=make_wav(frequency=hz);r=analyze_hnr(data)
    assert len(r['tracking_hnr_frames'])==r['quality']['hnr_total_frames']
    assert 'HNR_PERIODICITY_RELIABILITY_UNVERIFIED' in [w['code'] for w in r['quality']['technical_warnings']]


@pytest.mark.parametrize('kind',['harmonics','weak_fundamental','inharmonic'])
def test_spectral_characterization(kind):
    data,_=make_wav(kind=kind);r=analyze_hnr(data)
    assert r['acoustic']['hnr_mean_db']['status']=='experimental_periodicity_reliability_unverified'
    json.dumps(r,allow_nan=False)


def test_global_silence_threshold_context_characterization():
    data,_=make_wav(kind='weak_center');context,_=make_wav(kind='weak_center',global_context=True)
    before=analyze_hnr(data);after=analyze_hnr(context)
    # Exact query comparisons, without prescribing that the two contexts must match.
    for data,r in [(data,before),(context,after)]:
        native=query_sound(data)['hnr_mean_db'];actual=r['acoustic']['hnr_mean_db']['value']
        if native is None:assert actual is None
        else:assert abs(native-actual)<=1e-6


def test_silence_marker_is_not_measured_minus_200_or_zero():
    data,_=make_wav(kind='silence');r=analyze_hnr(data)
    assert r['acoustic']['hnr_mean_db']['value'] is None
    assert r['quality']['hnr_coverage_percent']['value']==0
    assert all(f['praat_raw_hnr_db']==-200 and f['hnr_db'] is None and not f['valid'] for f in r['tracking_hnr_frames'])


def test_noise_can_return_finite_negative_value():
    data,_=make_wav(kind='noise_only');r=analyze_hnr(data)
    assert r['acoustic']['hnr_mean_db']['value'] is not None
    assert r['acoustic']['hnr_mean_db']['value']<0
    assert r['quality']['hnr_coverage_percent']['value']>0


def payload(frames,mean=0,start=1.5,end=4.5):
    return json.dumps({'hnr_mean_db':mean,'frames':frames,'total_frames':len(frames),
                       'valid_frames':sum(f['praat_raw_hnr_db'] is not None and f['praat_raw_hnr_db']!=-200 for f in frames),
                       'object_frames':max([f['frame_index'] for f in frames],default=1),
                       'time_step_s':.01,'first_frame_center_s':2})


def test_native_mean_is_not_overwritten_or_compared_to_frame_arithmetic():
    frames=[{'frame_index':1,'time_s':2,'praat_raw_hnr_db':10},{'frame_index':2,'time_s':2.01,'praat_raw_hnr_db':20}]
    x=_parse(payload(frames,mean=12.345),1.5,4.5)
    assert x['hnr_mean_db']==12.345


def test_zero_negative_undefined_and_numeric_limits_are_preserved():
    frames=[{'frame_index':i+1,'time_s':2+i*.01,'praat_raw_hnr_db':v} for i,v in enumerate([0,-10,None,-200,150,-150])]
    x=_parse(payload(frames,mean=-3),1.5,4.5)
    assert x['hnr_mean_db']==-3
    assert [f['hnr_db'] for f in x['frames']]==[0,-10,None,None,150,-150]
    assert sum(f['numerical_limit'] for f in x['frames'])==2


@pytest.mark.parametrize('raw',['{"hnr_mean_db":NaN}','{"hnr_mean_db":Infinity}','{}'])
def test_corrupt_native_output_rejected(raw):
    with pytest.raises(AnalysisError):_parse(raw,1.5,4.5)


def test_no_frames_diagnostic_interval():
    data,_=make_wav();r=analyze_hnr(data,diagnostic_interval=(.001,.002))
    assert r['tracking_hnr_frames']==[]
    assert r['quality']['hnr_coverage_percent']['value'] is None
    assert r['acoustic']['hnr_mean_db']['value'] is None


def test_provenance_independent_route_and_no_other_acoustic_metrics(monkeypatch):
    import backend.pitch,backend.jitter,backend.shimmer
    def forbidden(*args,**kwargs):raise AssertionError('HNR must not run Pitch or pulse-dependent modules')
    monkeypatch.setattr(backend.pitch,'analyze_pitch',forbidden)
    monkeypatch.setattr(backend.jitter,'analyze_jitter',forbidden)
    monkeypatch.setattr(backend.shimmer,'analyze_shimmer',forbidden)
    data,_=make_wav();r=analyze_hnr(data);p=r['provenance']
    assert list(r['acoustic'])==['hnr_mean_db']
    assert p['configuration_sha256']==hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()=='94b976f9c3e1f21d965df9ce547422953c6d780df64988cf2562cc8594520729'
    assert p['file_sha256']==hashlib.sha256(data).hexdigest()
    assert p['script_sha256']==hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    assert p['duration_script_sha256']==hashlib.sha256(Path('praat/smoke_test.praat').read_bytes()).hexdigest()
    assert (p['module_version'],p['output_schema_version'],p['warnings_version'])==('hnr_v1','hnr_output_v1','hnr_warnings_v1')
    assert p['praat_version']=='6.4.27'
    assert r['quality']['accepted_cycles']['value'] is None


def test_api_hnr_and_short_emission():
    data,_=make_wav(snr_db=20)
    with TestClient(app) as client:
        response=client.post('/hnr',files={'file':('tone.wav',data,'audio/wav')})
        short=client.post('/hnr',files={'file':('short.wav',Path('tests/fixtures/tone_2s.wav').read_bytes(),'audio/wav')})
    assert response.status_code==200 and short.status_code==422
    assert response.json()['provenance']['module_version']=='hnr_v1'
