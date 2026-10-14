import copy
import hashlib
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import vowel
from backend.praat_runner import AnalysisError
from tests.synthetic_pitch import wav_bytes

client = TestClient(app)
DATA = wav_bytes()


def result():
    return {'provenance': {'file_sha256': hashlib.sha256(DATA).hexdigest(),
            'configuration_sha256': 'config', 'configuration_version': 'experimental_v1',
            'protocol_version': 'v1', 'praat_version': '6.4.27'},
            'analysis_interval': {'start_s': 1.5, 'end_s': 4.5},
            'acoustic': {'example': {'value': 0, 'reason': None}}}


def setup(monkeypatch, a=None, b=None):
    def module(value):
        def run(data, start, end):
            assert data == DATA and start == 0 and end == 6
            if isinstance(value, Exception): raise value
            return copy.deepcopy(value if value is not None else result())
        return run
    monkeypatch.setattr(vowel, 'analyze_shimmer', module(a))
    monkeypatch.setattr(vowel, 'analyze_hnr', module(b))


def test_complete(monkeypatch):
    setup(monkeypatch)
    r = vowel.analyze_vowel(DATA, 0, 6)
    assert r['status'] == 'completed' and r['integrity']['cross_module_verified']
    assert r['modules']['shimmer']['result']['acoustic']['example']['value'] == 0


@pytest.mark.parametrize('failed', ['shimmer', 'hnr'])
def test_partial(monkeypatch, failed):
    setup(monkeypatch, **({'a': AnalysisError('failure')} if failed == 'shimmer' else {'b': AnalysisError('failure')}))
    r = vowel.analyze_vowel(DATA, 0, 6)
    assert r['status'] == 'partial' and not r['integrity']['cross_module_verified']
    assert r['modules'][failed]['result'] is None
    assert r['modules'][failed]['error']['code'] == 'ANALYSIS_FAILED'


def test_both_fail(monkeypatch):
    setup(monkeypatch, AnalysisError('a'), AnalysisError('b'))
    with pytest.raises(AnalysisError): vowel.analyze_vowel(DATA, 0, 6)


@pytest.mark.parametrize('field', ['file_sha256', 'configuration_sha256', 'configuration_version', 'protocol_version', 'praat_version', 'interval'])
def test_mismatch(monkeypatch, field):
    b = result()
    if field == 'interval': b['analysis_interval']['start_s'] = 2
    else: b['provenance'][field] = 'different'
    setup(monkeypatch, b=b)
    with pytest.raises(AnalysisError): vowel.analyze_vowel(DATA, 0, 6)


@pytest.mark.parametrize('start,end', [(0,2),(-1,6),(float('nan'),6),(0,float('inf'))])
def test_invalid_limits(start,end):
    with pytest.raises(ValueError): vowel.analyze_vowel(DATA,start,end)


def test_null_and_negative_preserved(monkeypatch):
    b = result(); b['acoustic'] = {'hnr_mean_db': {'value': -10, 'reason': None}, 'undefined': {'value': None, 'reason': 'praat_undefined'}}
    setup(monkeypatch,b=b)
    assert vowel.analyze_vowel(DATA,0,6)['modules']['hnr']['result']['acoustic'] == b['acoustic']


def test_real_native_integration():
    data = wav_bytes()
    r = vowel.analyze_vowel(data,0,6)
    assert r['status'] == 'completed'
    assert abs(r['modules']['shimmer']['result']['acoustic']['f0_mean_hz']['value']-200)<.1
    assert r['modules']['hnr']['result']['acoustic']['hnr_mean_db']['value'] is not None
    assert r['analysis_interval']['start_s'] == 1.5


@pytest.mark.parametrize('failure,code', [(ValueError('invalid'),422),(AnalysisError('engine'),503)])
def test_http_errors(monkeypatch,failure,code):
    def fail(*args): raise failure
    monkeypatch.setattr(vowel,'analyze_vowel',fail)
    assert client.post('/vowel-analysis',files={'file':('x.wav',b'abc')}).status_code == code


def test_http_partial(monkeypatch):
    setup(monkeypatch,b=AnalysisError('failed'))
    r=client.post('/vowel-analysis',files={'file':('x.wav',DATA)},data={'emission_start_s':'0','emission_end_s':'6'})
    assert r.status_code == 200 and r.json()['status']=='partial'


def test_http_limit():
    assert client.post('/vowel-analysis',files={'file':('x.wav',b'x'*(10*1024*1024+1))}).status_code==413


@pytest.mark.parametrize('path', ['/', '/static/app.js', '/static/audio.js', '/static/recorder-worklet.js', '/static/style.css'])
def test_frontend_assets(path):
    assert client.get(path).status_code == 200


def test_unexpected_module_failure_is_partial(monkeypatch):
    setup(monkeypatch,b=RuntimeError('private implementation detail'))
    r=vowel.analyze_vowel(DATA,0,6)
    assert r['status']=='partial'
    assert r['modules']['hnr']['error']['code']=='INTERNAL_MODULE_ERROR'
    assert 'private' not in str(r['modules']['hnr']['error'])


def test_valid_input_module_valueerror_preserves_other_result(monkeypatch):
    setup(monkeypatch, b=ValueError('module cannot process valid input'))
    assert vowel.analyze_vowel(DATA, 0, 6)['status'] == 'partial'


def test_invalid_wav_no_modules(monkeypatch):
    def forbidden(*args): raise AssertionError('must not execute modules')
    monkeypatch.setattr(vowel, 'analyze_shimmer', forbidden)
    with pytest.raises(ValueError): vowel.analyze_vowel(b'invalid', 0, 6)
