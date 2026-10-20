import copy
import io
import wave
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.phrase import analyze_phrase, digest
from backend import phrase_candidate_routes as api
from tests.test_phrase import context
from tests.synthetic_phrase import wav

client=TestClient(app)

def activity(gap=True):
    rate=48000
    x=.2*np.sin(2*np.pi*200*np.arange(rate*8)/rate)
    if gap:
        x[rate*2:rate*3]=0
        x[rate*5:rate*6]=0
    f=io.BytesIO()
    with wave.open(f,'wb') as w:
        w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes((x*32767).astype('<i2').tobytes())
    return f.getvalue()

def request(data=None,c=None,expected=None):
    data=activity() if data is None else data;c=context() if c is None else c
    p=client.get('/phrase-candidate-protocol').json()
    expected=expected or {**{k:p[k] for k in ['config_sha256','engine_sha256']},'file_sha256':digest(data),'context_sha256':analyze_phrase(data,c)['provenance']['context_sha256']}
    import json
    return client.post('/phrase-candidates',files={'file':('a.wav',data,'audio/wav')},data={'context_json':json.dumps(c),'expected_dependencies_json':json.dumps(expected)})

def test_exact_frozen_energy_response_and_no_manual_metrics(monkeypatch):
    original=api.engine.detect; calls=[]
    def detect(*args,**kwargs):
        calls.append(kwargs);return original(*args,**kwargs)
    monkeypatch.setattr(api.engine,'detect',detect)
    r=request().json()
    assert r['status']=='completed' and r['automatic_candidates']
    assert calls==[{'variant':'energy','include_frames':False}]
    assert r['automatic_candidates']==r['original_execution']['automatic_candidates']
    assert not {'metrics','pause_count','pause_duration_s'} & r.keys()
    assert r['original_execution']['manual_final_result'] is None
    assert r['dependencies']['context']['attempt']==1
    assert all(c['duration_samples']==c['end_sample_exclusive']-c['start_sample'] for c in r['automatic_candidates'])

@pytest.mark.parametrize('key',['file_sha256','context_sha256','engine_sha256','config_sha256'])
def test_stale_hashes(key):
    d=activity();p=client.get('/phrase-candidate-protocol').json()
    expected={**{k:p[k] for k in ['engine_sha256','config_sha256']},'file_sha256':digest(d),'context_sha256':analyze_phrase(d,context())['provenance']['context_sha256']};expected[key]='0'*64
    r=request(d,expected=expected).json()
    assert r['status']=='stale' and r['automatic_candidates'] is None

def test_not_evaluable_is_null():
    r=request(wav()).json();assert r['status']=='not_evaluable' and r['automatic_candidates'] is None

def test_completed_empty_is_not_manual_zero():
    r=request(activity(False)).json()
    assert r['status']=='completed' and r['automatic_candidates']==[]
    assert r['original_execution']['manual_final_result'] is None

def test_failed_is_null(monkeypatch):
    def fail(*a,**k):raise RuntimeError('private')
    monkeypatch.setattr(api.engine,'detect',fail)
    r=request().json();assert r['status']=='failed' and r['automatic_candidates'] is None and 'private' not in str(r)

@pytest.mark.parametrize('c',[context(selection_confirmed=False),context(selection={'start_sample':-1,'end_sample_exclusive':42}),context(attempt=3)])
def test_invalid_context(c):
    # No pre-analysis helper for invalid input.
    import json
    r=client.post('/phrase-candidates',files={'file':('a.wav',activity())},data={'context_json':json.dumps(c),'expected_dependencies_json':'{}'})
    assert r.status_code==422

def test_attempts_and_selection_bound_to_identity():
    a=request().json();b=request(c=context(attempt=2)).json()
    assert a['original_execution']['run_id']!=b['original_execution']['run_id']
    assert a['dependencies']['context_sha256']!=b['dependencies']['context_sha256']


def test_energy_algorithm_and_parameters_remain_frozen():
    from pathlib import Path
    assert digest(Path(api.engine.__file__).read_bytes()) == '0c837e11109915202a700c27e9c225627d6d6cc09ca977eab5857a7ea6190629'
    assert api.engine.config('energy')[1] == '09100457fd44b3d474dc5b0e60e81233ac85ae8d96dda58fc2a75eb633048c6e'
