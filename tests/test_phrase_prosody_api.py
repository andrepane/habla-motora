import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import phrase_prosody_routes as api
from backend.phrase import digest
from backend.phrase_prosody import source_dependencies
from tests.test_phrase import context
from research.prosody.bank import generate, manifest

client = TestClient(app)


def sample(**updates):
    c = next(manifest('development')); c.update(frequency=200., **updates)
    return generate(c)[:2]


def request(data=None, ctx=None, expected=None):
    if data is None:
        data, selection = sample()
        ctx = context(selection=selection) if ctx is None else ctx
    if expected is None:
        frozen = api.configuration()
        _, expected = source_dependencies(data, ctx, frozen)
    return client.post('/phrase-prosody-analysis', files={'file':('a.wav',data,'audio/wav')},
                       data={'context_json':json.dumps(ctx),'expected_dependencies_json':json.dumps(expected)})


def test_exact_7a_selection_and_frozen_only(monkeypatch):
    original = api.acoustic.analyze_prosody; calls = []
    def spy(data, ctx, **kwargs):
        calls.append((copy.deepcopy(ctx), copy.deepcopy(kwargs)))
        return original(data, ctx, **kwargs)
    monkeypatch.setattr(api.acoustic, 'analyze_prosody', spy)
    data, sel = sample(); ctx = context(selection=sel)
    response = request(data, ctx); assert response.status_code == 200
    r = response.json(); assert r['status'] == 'completed'
    assert calls[0][0] == ctx and calls[0][1]['configuration'] == api.configuration()
    assert r['configuration']['selected_configuration_id'] == 'filtered_800_03__0'
    assert r['acoustic_interval'] == sel == r['context']['selection']
    assert all(sel['start_sample']/44100 <= f['time_absolute_s'] < sel['end_sample_exclusive']/44100 for f in r['frames'])
    assert r['reference_st']['value_hz'] == r['native_audit']['f0_median_hz']
    assert r['runtime']['praat_version'].startswith('Praat 6.4.27')
    assert r['protocol_version'] == 'phrase_prosody_v1'
    assert r['counts']['defined'] == len(r['frames'])
    assert not {'pause_count', 'reference_word_rate'} & r['metrics'].keys()


@pytest.mark.parametrize('key', sorted(api.DEPENDENCIES))
def test_each_dependency_mismatch_is_stale_without_frames(key):
    data, sel = sample(); ctx = context(selection=sel)
    _, deps = source_dependencies(data, ctx, api.configuration()); deps[key] = '0'*64
    r = request(data, ctx, deps).json()
    assert r['status'] == 'stale' and r['frames'] is None
    assert all(m['value'] is None and m['reason'] for m in r['metrics'].values())


@pytest.mark.parametrize('change',['selection','attempt','modality','wav','phrase_version'])
def test_context_changes_reject_old_identity(change, monkeypatch):
    data, sel = sample(); ctx = context(selection=sel)
    _, deps = source_dependencies(data, ctx, api.configuration())
    if change == 'selection':ctx['selection']['start_sample'] += 1
    elif change == 'attempt':ctx['attempt'] = 2
    elif change == 'modality':
        ctx.update(modality='auditory_model_with_text_v1',administration=dict(model_id='controlled',model_sha256='a'*64,model_presented_confirmed=True))
    elif change == 'wav':data,_ = sample(phase=1.2)
    else:
        from backend import phrase
        monkeypatch.setattr(phrase,'CONFIG_BYTES',phrase.CONFIG_BYTES+b' ')
    r = request(data,ctx,deps).json(); assert r['status'] == 'stale' and r['frames'] is None


def test_partial_null_reasons_and_zero_coverage_are_distinct():
    data,sel=sample(family='middle_only')
    r=request(data,context(selection=sel)).json()
    assert r['status']=='partial' and r['metrics']['f0_median_hz']['value'] is not None
    assert r['metrics']['robust_range_st']['value'] is None
    assert r['metrics']['robust_range_st']['reason']=='insufficient_distributional_support'
    assert r['metrics']['slope_st_s']['reason']=='insufficient_temporal_support'
    data,sel=sample(family='silence');r=request(data,context(selection=sel)).json()
    assert r['status']=='not_evaluable' and r['metrics']['coverage_percent']['value']==0
    assert r['metrics']['f0_median_hz']['value'] is None and r['metrics']['f0_median_hz']['reason']=='no_defined_f0'
    assert r['counts']['defined']==0 and r['gaps']


def test_unconfirmed_short_failed_and_integrity(monkeypatch):
    data,sel=sample();ctx=context(selection=sel,selection_confirmed=False)
    r=request(data,ctx).json(); assert r['status']=='not_evaluable' and r['reason']=='selection_unconfirmed'
    sel['end_sample_exclusive']=sel['start_sample']+10
    r=request(data,context(selection=sel)).json();assert r['reason']=='insufficient_analysis_duration'
    monkeypatch.setenv('PRAAT_EXECUTABLE','/not/a/praat')
    data,sel=sample();r=request(data,context(selection=sel)).json()
    assert r['status']=='failed' and r['runtime']['praat_version'] is None
    monkeypatch.setattr(api,'FREEZE_SHA256','0'*64)
    assert client.get('/phrase-prosody-protocol').status_code==503
    assert request(data,context(selection=sel),expected={k:'a'*64 for k in api.DEPENDENCIES}).status_code==503


@pytest.mark.parametrize('family,code',[('clipping','POSSIBLE_DIGITAL_CLIPPING'),('gap','UNDEFINED_F0_REGIONS'),('fade','UNDEFINED_F0_REGIONS')])
def test_existing_warnings_are_transported(family,code):
    data,sel=sample(family=family,gap=1.,position=.5)
    r=request(data,context(selection=sel)).json()
    assert any(w['code']==code for w in r['warnings'])


@pytest.mark.parametrize('body',['null','[]','{}','{"phrase_id":"unsupported"}'])
def test_invalid_requests_are_422(body):
    data,_=sample()
    r=client.post('/phrase-prosody-analysis',files={'file':('a.wav',data)},
                  data={'context_json':body,'expected_dependencies_json':'{}'})
    assert r.status_code==422


def test_protocol_matches_module_identity_and_frozen_bytes():
    data,sel=sample();_,deps=source_dependencies(data,context(selection=sel),api.configuration())
    p=client.get('/phrase-prosody-protocol').json()
    assert p['engine_sha256']==deps['engine_sha256'] and p['config_sha256']==deps['config_sha256']
    assert digest(Path('research/prosody/freeze.json').read_bytes())==api.FREEZE_SHA256
