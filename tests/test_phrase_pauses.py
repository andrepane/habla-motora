"""Manual 7B.1 contract, mathematical oracle, integrity and HTTP tests."""
import copy
from fractions import Fraction
import json
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.phrase import analyze_phrase, digest
from backend.phrase_pauses import analyze_pauses, source_dependencies, METRICS
from tests.synthetic_phrase import wav


def fixture(rate=48000, bits=16, counts=(14,25), match='exact_once'):
    data = wav(rate=rate, bits=bits)
    context = {'phrase_id':'phrase_es_01_v1','modality':'direct_reading_v1','attempt':1,
               'selection':{'start_sample':0,'end_sample_exclusive':8*rate},
               'selection_confirmed':True,'recording_limit_reached':False,'administration':{}}
    initial = analyze_phrase(data,context)
    review = {'context_sha256':initial['provenance']['context_sha256'],'confirmed':True,
              'production':'present','target_match':match,
              'word_count':{'value':counts[0],'confirmed':counts[0] is not None},
              'syllable_count':{'value':counts[1],'confirmed':counts[1] is not None},
              'events':[],'notes':''}
    source = analyze_phrase(data,context,review,digest(data))
    temporal = {'protocol_version':'phrase_pause_review_v1','source_dependencies':source_dependencies(source),
                'status':'confirmed','reviewed_all':True,'note':'Revisión completa manual.','intervals':[]}
    return data,context,review,temporal


def event(a=48000,b=72000,kind='pause',id='p1',**extra):
    return dict(id=id,start_sample=a,end_sample_exclusive=b,classification=kind,
                breath_present='no',within_word=False,nonarticulatory_confirmed=False,note='',**extra)


def run(f):
    d,c,r,t=f
    return analyze_pauses(d,c,r,digest(d),t)


@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('bits',[16,24,32])
def test_integer_samples_fraction_oracle_and_source_unchanged(rate,bits):
    f=fixture(rate,bits); d,c,r,t=f
    t['intervals']=[event(rate,rate+rate//2),event(3*rate,3*rate+3*rate//2,id='p2')]
    before=copy.deepcopy(f)
    out=run(f); m=out['metrics']
    assert f == before
    assert out['source_7a']==analyze_phrase(d,c,r,digest(d))
    assert m['pause_duration_s']['value']==2
    assert m['operational_speech_time_s']['value']==6
    assert m['pause_percent']['value']==25
    assert m['pause_count']['value']==2
    assert m['pause_mean_duration_s']['value']==1
    assert m['pause_median_duration_s']['value']==1
    assert m['reviewed_word_articulation_rate']['value']==140
    assert abs(m['reviewed_syllable_articulation_rate']['value']-float(Fraction(25,6)))<1e-9
    assert digest(d)==out['provenance']['source_dependencies']['file_sha256']


@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('offset',[-1,0,1])
def test_threshold_by_one_sample(rate,offset):
    f=fixture(rate); f[3]['intervals']=[event(rate,rate+rate//4+offset)]
    if offset<0:
        with pytest.raises(ValueError,match='250'):run(f)
        f[3]['intervals'][0]['classification']='below_threshold'
        assert run(f)['metrics']['pause_count']['value']==0
    else: assert run(f)['metrics']['pause_count']['value']==1


def test_zero_pauses_not_zero_mean_or_median_and_pending_list_is_not_zero():
    f=fixture(); m=run(f)['metrics']
    for k in ['pause_duration_s','pause_count','pause_percent']:assert m[k]['value']==0
    for k in ['pause_mean_duration_s','pause_median_duration_s']:assert m[k]['reason']=='no_pauses' and m[k]['value'] is None
    assert m['operational_speech_time_s']['value']==8
    f[3].update(status='draft',reviewed_all=False)
    assert all(x['value'] is None for x in run(f)['metrics'].values())


@pytest.mark.parametrize('kind',['uncertain','other_nonverbal'])
@pytest.mark.parametrize('status',['draft','not_evaluable','confirmed'])
def test_uncertain_or_interference_blocks_every_global_metric(kind,status):
    f=fixture();f[3].update(status=status,reviewed_all=status=='confirmed')
    f[3]['intervals']=[event(),event(100000,124000,kind=kind,id='p2')]
    if status=='confirmed':
        with pytest.raises(ValueError,match='impide confirmar'):run(f)
    else:
        out=run(f)
        assert set(out['metrics'])==set(METRICS)
        assert all(m['value'] is None for m in out['metrics'].values())
        assert out['audit']['accepted_pause_samples_partial']==24000
        assert out['audit']['partial_evidence_is_not_global_summary']


def test_intrapalabra_needs_explicit_nonarticulatory_confirmation():
    f=fixture(); e=event();e['within_word']=True;f[3]['intervals']=[e]
    with pytest.raises(ValueError,match='Intrapalabra'):run(f)
    e['nonarticulatory_confirmed']=True
    assert run(f)['metrics']['pause_count']['value']==1
    e['classification']='consonantal_closure';e['nonarticulatory_confirmed']=False
    assert run(f)['metrics']['pause_count']['value']==0
    e['classification']='uncertain'
    with pytest.raises(ValueError):run(f)


@pytest.mark.parametrize('kind',['consonantal_closure','below_threshold'])
def test_excluded_events_retained_in_operational_time(kind):
    f=fixture();f[3]['intervals']=[event(48000,52000 if kind=='below_threshold' else 80000,kind=kind)]
    assert run(f)['metrics']['operational_speech_time_s']['value']==8


def test_breath_attribute_does_not_double_subtract():
    f=fixture();e=event();e['breath_present']='yes';f[3]['intervals']=[e]
    assert run(f)['metrics']['pause_duration_s']['value']==.5
    assert run(f)['metrics']['pause_count']['value']==1


@pytest.mark.parametrize('deviation,counts',[('omission',(13,22)),('repetition',(15,27)),('substitution',(14,26)),('fragment',(0,2)),('restart',(18,32)),('filled_pause',(0,1))])
def test_deviation_counts_and_time_reused_from_7a(deviation,counts):
    f=fixture(counts=counts,match='different');f[2]['events']=[{'id':'e1','type':deviation,'note':''}]
    src=analyze_phrase(f[0],f[1],f[2],digest(f[0]));f[3]['source_dependencies']=source_dependencies(src)
    f[3]['intervals']=[event()]
    out=run(f);m=out['metrics']
    assert m['reviewed_word_articulation_rate']['value']==counts[0]*60/7.5
    assert m['reviewed_syllable_articulation_rate']['value']==counts[1]/7.5
    assert src['rates']['reference_word_rate']['value'] is None
    assert out['source_7a']==src


@pytest.mark.parametrize('counts',[(None,None),(14,None),(None,25)])
def test_independent_counts_and_no_reference_fallback(counts):
    m=run(fixture(counts=counts))['metrics']
    for i,k in enumerate(['word','syllable']):
        assert (m[f'reviewed_{k}_articulation_rate']['value'] is None)==(counts[i] is None)
    assert m['pause_count']['value']==0


@pytest.mark.parametrize('name',['file_sha256','context_sha256','review_sha256','config_sha256','engine_sha256'])
def test_stale_dependencies(name):
    f=fixture();f[3]['source_dependencies'][name]='old'
    with pytest.raises(ValueError,match='stale_dependency'):run(f)


@pytest.mark.parametrize('change',['wav','bounds','modality','review','attempt'])
def test_recomputed_7a_rejects_stale_source(change):
    f=list(fixture());d,c,r,t=f
    if change=='wav':f[0]=d[:-2]+b'\x01\x00'
    elif change=='bounds':c['selection']['start_sample']=1
    elif change=='modality':c.update(modality='auditory_model_with_text_v1',administration={'model_id':'m','model_sha256':'a'*64,'model_presented_confirmed':True})
    elif change=='review':r['notes']='Edited'
    else:c['attempt']=2
    with pytest.raises(ValueError):run(f)


@pytest.mark.parametrize('a,b',[(0,20000),(48000,384000),(-1,20000),(48000,48000),(60000,48000),(1.1,20000),(True,20000),(None,20000)])
def test_invalid_bounds(a,b):
    f=fixture();f[3]['intervals']=[event(a,b)]
    with pytest.raises(ValueError):run(f)


@pytest.mark.parametrize('a,b',[(60000,84000),(72000,96000),(48000,72000)])
def test_overlaps_duplicates_contiguous_rejected(a,b):
    f=fixture();f[3]['intervals']=[event(),event(a,b,id='p2')]
    with pytest.raises(ValueError):run(f)


def test_unordered_input_not_mutated_and_odd_median():
    f=fixture();f[3]['intervals']=[event(200000,248000,id='p3'),event(),event(100000,136000,id='p2')]
    before=copy.deepcopy(f[3]);m=run(f)['metrics']
    assert m['pause_median_duration_s']['value']==.75
    assert f[3]==before


@pytest.mark.parametrize('state',['pending','absent'])
def test_no_production_is_not_all_pause(state):
    f=fixture(counts=(0,0),match='different');f[2]['production']=state
    src=analyze_phrase(f[0],f[1],f[2],digest(f[0]));f[3]['source_dependencies']=source_dependencies(src)
    out=run(f)
    assert all(m['value'] is None for m in out['metrics'].values())
    assert out['metrics']['pause_count']['reason']==('no_production' if state=='absent' else 'content_review_pending')


def test_recording_cap_warning_manual_fragment_still_available():
    f=fixture();f[1]['recording_limit_reached']=True
    f[2]['context_sha256']=analyze_phrase(f[0],f[1])['provenance']['context_sha256']
    src=analyze_phrase(f[0],f[1],f[2],digest(f[0]));f[3]['source_dependencies']=source_dependencies(src)
    assert run(f)['metrics']['reviewed_syllable_articulation_rate']['value']==3.125
    assert 'RECORDING_LIMIT_REACHED_REFERENCE_RATES_BLOCKED' in run(f)['warnings']


def test_http_recomputation_validation_and_private_failure(monkeypatch):
    f=fixture();d,c,r,t=f
    client=TestClient(app)
    def post():return client.post('/phrase-pause-analysis',files={'file':('x.wav',d,'audio/wav')},data={'context_json':json.dumps(c),'review_json':json.dumps(r),'temporal_json':json.dumps(t),'expected_file_sha256':digest(d)})
    assert client.get('/phrase-pause-protocol').json()['minimum_pause_ms']==250
    assert post().json()==run(f)
    t['intervals']=[event(0,20000)]
    assert post().status_code==422
    t['intervals']=[]
    def fail(*args):raise RuntimeError('private-path')
    monkeypatch.setattr('backend.phrase_pause_routes.analyze_pauses',fail)
    response=post();assert response.status_code==503 and 'private-path' not in response.text


@pytest.mark.parametrize('update',[
    {'reviewed_all':False}, {'protocol_version':'other'},
    {'status':'not_evaluable','note':''}, {'status':'not_started'},
])
def test_invalid_confirmation_protocol_and_status(update):
    f=fixture();f[3]['intervals']=[event()];f[3].update(update)
    with pytest.raises(ValueError):run(f)


@pytest.mark.parametrize('field,value',[
    ('classification','automatic_pause'),('classification',[]),('breath_present','auto'),
    ('within_word',1),('nonarticulatory_confirmed',None),('start_sample',float('nan')),
])
def test_malformed_interval_metadata_rejected(field,value):
    f=fixture();e=event();e[field]=value;f[3]['intervals']=[e]
    with pytest.raises(ValueError):run(f)


def test_duplicate_id_and_below_threshold_misclassification():
    f=fixture();f[3]['intervals']=[event(),event(100000,124000)]
    with pytest.raises(ValueError,match='duplicado'):run(f)
    f[3]['intervals']=[event(kind='below_threshold')]
    with pytest.raises(ValueError,match='below_threshold'):run(f)


def test_http_bad_json_overlimit_and_missing_review_are_distinct():
    client=TestClient(app);d,c,r,t=fixture()
    response=client.post('/phrase-pause-analysis',files={'file':('x.wav',d)},data={'context_json':'{','temporal_json':'{}'})
    assert response.status_code==422
    response=client.post('/phrase-pause-analysis',files={'file':('x.wav',b'x'*4000001)},data={'context_json':'{}','temporal_json':'{}'})
    assert response.status_code==413
    source=analyze_phrase(d,c);t['source_dependencies']=source_dependencies(source)
    response=client.post('/phrase-pause-analysis',files={'file':('x.wav',d)},data={'context_json':json.dumps(c),'temporal_json':json.dumps(t)})
    assert response.status_code==200
    assert all(m['reason']=='content_review_pending' for m in response.json()['metrics'].values())
