import copy
import hashlib
import json
import math
from fractions import Fraction
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend import ddk
from tests.synthetic_ddk import signal

client=TestClient(app)
DATA,CENTERS=signal()


def events(times, labels=None):
    return [{'id':f'e{i}','time_s':t,'label':labels[i] if labels else 'unknown','restart':False} for i,t in enumerate(times)]


@pytest.mark.parametrize('times', [[],[.5],[.5,1],[.5,1,1.5],[.5,1,1.5,2],[.1,.3,.8,1.6,2.7]])
def test_independent_mathematics(times):
    es=events(times); groups=ddk.group_events(es,es[0]['id']) if es else None
    actual=ddk.calculate(es,groups,4)
    assert actual['event_count']['value']==len(times)
    if not times: assert actual['event_rate_per_s']['value'] is None
    else: assert abs(actual['event_rate_per_s']['value']-float(Fraction(len(times),4)))<=1e-9
    intervals=[Fraction(str(b))-Fraction(str(a)) for a,b in zip(times,times[1:])]
    if len(intervals)>=3:
        mean=sum(intervals)/len(intervals)
        variance=sum((x-mean)**2 for x in intervals)/(len(intervals)-1)
        sd=math.sqrt(float(variance))
        assert abs(actual['event_regularity']['sd_ms']['value']-sd*1000)<=1e-9
        assert abs(actual['event_regularity']['cv_percent']['value']-100*sd/float(mean))<=1e-9
    else: assert actual['event_regularity']['cv_percent']['value'] is None


@pytest.mark.parametrize('rhythm',[2,4,6,8,10,12])
@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('bits',[16,24,32])
def test_clean_matrix(rhythm,rate,bits):
    centers=[.25+i/rhythm for i in range(int(3.5*rhythm))]
    data,_=signal(centers,rate=rate,bits=bits,amplitudes=(.1,.3,.6))
    r=ddk.analyze_ddk(data)
    found=r['automatic_original']['detection']['events']
    assert len(found)==len(centers)
    assert max(abs(e['time_s']-t) for e,t in zip(found,centers))<=.01
    assert r['provenance']['file_sha256']==hashlib.sha256(data).hexdigest()
    assert r['automatic_original']['groups'] is None
    assert all(e['label']=='unknown' for e in found)


def test_grouping_anchor_remainder_and_rates():
    es=events([.2+i*.1 for i in range(14)])
    groups=ddk.group_events(es,'e1')
    assert [g['event_ids'] for g in groups]==[['e1','e2','e3'],['e4','e5','e6'],['e7','e8','e9'],['e10','e11','e12']]
    m=ddk.calculate(es,groups,2)
    assert m['event_rate_per_s']['value']==7 and m['group_rate_per_s']['value']==2
    assert len(m['group_regularity']['intervals_s'])==3
    with pytest.raises(ValueError):ddk.group_events(es,'missing')


def test_reviewed_cycles_are_manual_and_restart_excludes():
    es=events([.2+i*.1 for i in range(12)], ['pa','ta','ka']*4)
    es[6]['restart']=True
    gs=ddk.group_events(es,reviewed=True)
    assert len(gs)==4
    m=ddk.calculate(es,gs,2,True)
    assert len(m['excluded_event_transitions'])==1
    assert len(m['excluded_group_transitions'])==1
    assert len(m['group_regularity']['intervals_s'])==2
    assert m['group_regularity']['cv_percent']['value'] is None
    es[4]['label']='other'
    assert len(ddk.group_events(es,reviewed=True))==3


def test_review_replay_preserves_original_and_recovery():
    original=events([.1,.3,.5]);saved=copy.deepcopy(original)
    review={'operations':[{'action':'delete','id':'e1'},{'action':'add','id':'m1','time_s':.35},
        {'action':'move','id':'e2','time_s':.6},{'action':'label','id':'e0','label':'pa'},
        {'action':'label','id':'m1','label':'ta'},{'action':'label','id':'e2','label':'ka'}], 'confirmed':True}
    output,confirmed,_=ddk.apply_review(original,review,0,1)
    assert original==saved and confirmed
    assert [e['time_s'] for e in output]==[.1,.35,.6]
    assert len(ddk.group_events(output,reviewed=True))==1


@pytest.mark.parametrize('op',[{'action':'move','id':'e0','time_s':float('nan')},
    {'action':'move','id':'e0','time_s':2},{'action':'add','id':'e0','time_s':.7},
    {'action':'move','id':'e0','time_s':.3},{'action':'delete','id':'missing'},
    {'action':'label','id':'e0','label':'invalid'},{'action':'restart','id':'e0','restart':1},
    {'action':'add','id':'m1','time_s':True},{'action':'invent','id':'e0'}])
def test_invalid_operations(op):
    with pytest.raises(ValueError):ddk.apply_review(events([.1,.3]),{'operations':[op]},0,1)


@pytest.mark.parametrize('review',[{'confirmed':True},{'confirmed':'yes'}, {'confirmed':True,'confirm_absence':True}, {'operations':{}}, {'secret':'x'}])
def test_invalid_review(review):
    with pytest.raises(ValueError):ddk.apply_review(events([.1,.3]),review,0,1)


def test_empty_and_confirmed_absence():
    data,_=signal([])
    r=ddk.analyze_ddk(data)
    assert r['stages']['detection']['status']=='empty'
    assert r['automatic_original']['metrics']['event_count']['value']==0
    assert r['automatic_original']['metrics']['event_rate_per_s']['value'] is None
    reviewed=ddk.analyze_ddk(data,review={'operations':[],'confirmed':True,'confirm_absence':True},expected_hash=hashlib.sha256(data).hexdigest())
    assert reviewed['reviewed_result']['metrics']['event_rate_per_s']['value']==0
    assert reviewed['reviewed_result']['metrics']['group_count']['value']==0


def test_detector_expected_failure_partial_manual_recovery(monkeypatch):
    def fail(*args):raise ddk.DetectionError('expected')
    monkeypatch.setattr(ddk,'detect',fail)
    r=ddk.analyze_ddk(DATA)
    assert r['status']=='partial'
    assert r['stages']['grouping']['status']=='blocked'
    assert r['automatic_original']['metrics']['event_count']['value'] is None
    review={'operations':[{'action':'add','id':'m1','time_s':.5},{'action':'label','id':'m1','label':'other'}],'confirmed':True}
    r=ddk.analyze_ddk(DATA,review=review,expected_hash=hashlib.sha256(DATA).hexdigest())
    assert r['reviewed_result']['metrics']['event_count']['value']==1
    assert r['stages']['detection']['status']=='failed'


def test_unexpected_failure_http(monkeypatch):
    def fail(*args):raise RuntimeError('private')
    monkeypatch.setattr(ddk,'detect',fail)
    r=client.post('/ddk-analysis',files={'file':('x.wav',DATA)})
    assert r.status_code==503 and 'private' not in r.text


@pytest.mark.parametrize('start,end',[(-1,2),(0,20),(1,1),(float('nan'),2),(0,float('inf')),(0,.001)])
def test_invalid_interval(start,end):
    with pytest.raises(ValueError):ddk.analyze_ddk(DATA,start,end)


def test_draft_does_not_claim_reviewed_metrics():
    r=ddk.analyze_ddk(DATA,review={'operations':[],'confirmed':False},expected_hash=hashlib.sha256(DATA).hexdigest())
    assert r['stages']['review']['status']=='draft' and r['reviewed_result']['metrics'] is None
    with pytest.raises(ValueError):ddk.analyze_ddk(DATA,review={},expected_hash='wrong')


def test_http_real_analysis_review_and_assets():
    r=client.post('/ddk-analysis',files={'file':('x.wav',DATA)})
    assert r.status_code==200
    result=r.json();first=result['automatic_original']['detection']['events'][0]['id']
    grouped=client.post('/ddk-analysis',files={'file':('x.wav',DATA)},data={'anchor_id':first}).json()
    assert grouped['stages']['grouping']['status']=='completed'
    ops=[{'action':'label','id':e['id'],'label':['pa','ta','ka'][i%3]} for i,e in enumerate(result['automatic_original']['detection']['events'])]
    reviewed=client.post('/ddk-analysis',files={'file':('x.wav',DATA)},data={'review_json':json.dumps({'operations':ops,'confirmed':True}),'expected_file_sha256':result['provenance']['file_sha256']})
    assert reviewed.status_code==200 and reviewed.json()['reviewed_result']['metrics']['group_count']['value']==7
    for path in ['/ddk','/static/ddk.js','/static/ddk.css','/static/ddk-recorder.js']:assert client.get(path).status_code==200


@pytest.mark.parametrize('data,fields,code',[(b'bad',{},422),(b'x'*4000001,{},413),(DATA,{'review_json':'bad'},422),(DATA,{'review_json':'null'},422),(DATA,{'anchor_id':'missing'},422),(DATA,{'review_json':'{}','expected_file_sha256':'wrong'},422)])
def test_http_rejections(data,fields,code):
    assert client.post('/ddk-analysis',files={'file':('x.wav',data)},data=fields).status_code==code


def test_truncated_and_too_long():
    with pytest.raises(ValueError):ddk.analyze_ddk(DATA[:-20])
    long,_=signal([],duration=15.01)
    with pytest.raises(ValueError):ddk.analyze_ddk(long)


def test_pauses_not_deleted_and_regular_zero():
    m=ddk.calculate(events([.1,.2,.3,.4,1.4]),None,2)
    assert max(m['event_regularity']['intervals_s'])==pytest.approx(1)
    assert m['event_regularity']['cv_percent']['value']>0
    assert ddk.temporal([.25,.25,.25])['cv_percent']['value']==0


def test_boundary_and_flat_energy_evidence():
    data,_=signal([0,.5,1,1.5],duration=1.5)
    r=ddk.analyze_ddk(data)
    assert any(c['reason']=='boundary_incomplete' for c in r['automatic_original']['detection']['candidates'])
    # Constant digital input cannot be asserted to be repeated syllables.
    raw=bytearray(DATA);raw[44:]=b'\x00\x20'*((len(raw)-44)//2)
    r=ddk.analyze_ddk(bytes(raw))
    assert r['automatic_original']['metrics']['event_rate_per_s']['value'] is None


def test_review_size_utf8_and_boundaries():
    r=client.post('/ddk-analysis',files={'file':('x.wav',DATA)},data={'review_json':'é'*125001})
    assert r.status_code==422 and 'grande' in r.text
    r=ddk.analyze_ddk(DATA,.10001,3.90001)
    a=r['analysis_interval']
    assert a['start_sample']==math.ceil(.10001*48000)
    assert a['end_sample_exclusive']==math.ceil(3.90001*48000)
    assert a['duration_s']==(a['end_sample_exclusive']-a['start_sample'])/48000
