import copy
import pytest
from backend import ddk, ddk_v2
from tests.synthetic_ddk import signal

@pytest.mark.parametrize('rhythm',[2,4,6,8,10,12])
@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('bits',[16,24,32])
def test_clean_matrix_v2(rhythm,rate,bits):
    centers=[.25+i/rhythm for i in range(int(3.5*rhythm))]
    data,_=signal(centers,rate=rate,bits=bits,amplitudes=(.1,.3,.6))
    result=ddk_v2.compare_wav(data)
    events=result['v2']['detection']['events']
    assert len(events)==len(centers)
    assert max(abs(e['time_s']-t) for e,t in zip(events,centers))<=.01
    assert result['v1']==ddk.analyze_ddk(data)
    fine=result['v2']['detection']['candidates']
    assert all(e['time_s']==next(c['time_s'] for c in fine if c['id']==e['id']) for e in events)

def test_ineligible_maximum_fragments_basin_without_reassignment():
    frames=[{'time_s':i*.005,'energy_db':v} for i,v in enumerate([0,10,1.5,2,1,10,0])]
    maxima=[{'time_s':.005},{'time_s':.015},{'time_s':.025}]
    limits=ddk_v2.basins(frames,maxima)
    assert limits==[.01,.02]
    # Two fine maxima from one simulated source: the second falls in the weak basin.
    fine_times=[.005,.0175]
    assert [sum(t>b for b in limits) for t in fine_times]==[0,1]
    # Explicit alternative, NOT detector configuration: omit the weak maximum.
    alternative=ddk_v2.basins(frames,[maxima[0],maxima[2]])
    assert [sum(t>b for b in alternative) for t in fine_times]==[0,0]

def test_threshold_flags_do_not_reject_and_v1_config_unchanged():
    before=copy.deepcopy(ddk.CONFIG)
    data,_=signal()
    result=ddk_v2.compare_wav(data)
    assert ddk.CONFIG==before
    assert all(c['reason'] or c['accepted'] for c in result['v2']['detection']['candidates'])
    assert all('width' not in str(c['reasons']) for c in result['v2']['detection']['candidates'])

def test_empty_and_boundary_audit():
    data,_=signal([])
    r=ddk_v2.compare_wav(data)['v2']
    assert r['status']=='empty'
    assert r['measures']['event_count']['value']==0
    assert r['measures']['event_rate_per_s']['value'] is None
    assert all(not c['accepted'] for c in r['detection']['candidates'])

def test_fragmentation_affects_full_association(monkeypatch):
    fine_frames=[{'time_s':i*.005,'energy_db':10 if i==10 else 9 if i==35 else 0,'boundary':False} for i in range(61)]
    levels=[0,10,1.5,2,1,10,0]
    structural_frames=[]
    for i in range(61):
        segment=min(i//10,5);fraction=(i-segment*10)/10
        structural_frames.append({'time_s':i*.005,'energy_db':levels[segment]*(1-fraction)+levels[segment+1]*fraction,'boundary':False})
    def peak(id,t,e,reason=None):return {'id':id,'time_s':t,'energy_db':e,'dip_db':e,'boundary':False,'accepted':reason is None,'reason':reason}
    fine={'frames':fine_frames,'threshold_db':3,'candidates':[peak('f1',.05,10),peak('f2',.175,9)],'warnings':[]}
    structural={'frames':structural_frames,'threshold_db':3,'candidates':[peak('s1',.05,10),peak('s2',.15,2,'below_threshold'),peak('s3',.25,10)],'warnings':[]}
    monkeypatch.setattr(ddk_v2,'_scale_detect',lambda samples,rate,a,b,config:copy.deepcopy(fine if config['window_ms']==20 else structural))
    actual=ddk_v2.detect([0]*350,1000,0,350)
    assert [c['structure_id'] for c in actual['candidates']]==['s1','s2']
    assert actual['candidates'][1]['reason']=='structural_below_threshold'
    assert [e['id'] for e in actual['events']]==['f1']
    # Alternative association only, not applied to production detector.
    limits=ddk_v2.basins(structural_frames,[structural['candidates'][0],structural['candidates'][2]])
    assert [sum(c['time_s']>b for b in limits) for c in fine['candidates']]==[0,0]
    # Both fine maxima would compete in s1; winner remains f1, not two events.

@pytest.mark.parametrize('bits',[16,24,32])
def test_separate_output_labels_and_audit(bits):
    r=ddk_v2.compare_wav(signal(bits=bits)[0])
    d=r['v2']['detection']
    assert all(e['label']=='unknown' for e in d['events'])
    assert all(c['structure_id'] in {s['id'] for s in d['structures']} for c in d['candidates'])
    assert all((not c['accepted'])==bool(c['reasons']) for c in d['candidates'])

def test_failure_returns_null(monkeypatch):
    def fail(*args): raise ddk.DetectionError('controlled failure')
    monkeypatch.setattr(ddk_v2,'detect',fail)
    r=ddk_v2.compare_wav(signal()[0])
    assert r['v2']['status']=='failed'
    assert r['v2']['measures']['event_count']['value'] is None
    assert r['v1']['automatic_original']['detection']['events']

def test_left_boundary_tie_and_first_minimum_plateau():
    frames=[{'time_s':i*.005,'energy_db':v} for i,v in enumerate([5,1,1,3,1,5])]
    limits=ddk_v2.basins(frames,[{'time_s':0},{'time_s':.025}])
    assert limits==[.0075]
    assert sum(.0075>b for b in limits)==0

def test_physical_modulated_source_basin_fragmentation():
    from tests.synthetic_ddk_v2 import basin_fragmentation_wav
    from tests.report_ddk_v2 import eligible_only_alternative
    data=basin_fragmentation_wav();samples,rate,_=ddk.read_wav(data)
    d=ddk_v2.detect(samples,rate,0,len(samples))
    structure=next(s for s in d['structures'] if s['time_s']==.53)
    assert structure['eligibility_reasons']==['insufficient_dip']
    fine=next(c for c in d['candidates'] if c['time_s']==.53)
    assert fine['v1_scale_accepted'] and not fine['accepted']
    assert fine['structure_id']==structure['id']
    baseline=[c for c in d['candidates'] if c['v1_scale_accepted']]
    assert any(c['time_s']<structure['time_s'] for c in baseline)
    assert any(c['time_s']>structure['time_s'] for c in baseline)
    alt=eligible_only_alternative(d)
    assert all(c['structure_id'] in {s['id'] for s in d['structures']} for c in alt)
    # An alternative winner retains its own 20 ms timestamp, not the structural time.
    assert all(c['time_s'] in [f['time_s'] for f in d['candidates']] for c in alt)

@pytest.mark.parametrize('energies,expected', [([9,10,8], 'f2'), ([10,10,8], 'f2'), ([10,8,10], 'f1')])
def test_representative_energy_distance_then_earliest(monkeypatch, energies, expected):
    frames=[{'time_s':i*.005,'energy_db':0,'boundary':False} for i in range(81)]
    def peak(id,t,e):
        return dict(id=id,time_s=t,energy_db=e,dip_db=10,boundary=False,accepted=True,reason=None)
    fine=dict(frames=frames,threshold_db=3,candidates=[peak(f'f{i+1}',t,e) for i,(t,e) in enumerate(zip([.1,.125,.15],energies))],warnings=[])
    structural=dict(frames=frames,threshold_db=3,candidates=[peak('s1',.125,10)],warnings=[])
    for detection in (fine,structural):
        detection['frames']=copy.deepcopy(frames)
        for c in detection['candidates']:
            detection['frames'][round(c['time_s']/.005)]['energy_db']=c['energy_db']
    monkeypatch.setattr(ddk_v2,'_scale_detect',lambda samples,rate,a,b,config:copy.deepcopy(fine if config['window_ms']==20 else structural))
    d=ddk_v2.detect([0]*400,1000,0,400)
    assert [e['id'] for e in d['events']]==[expected]
    assert all(c['reasons']==['same_structure_secondary'] for c in d['candidates'] if c['id']!=expected)

@pytest.mark.parametrize('gap,count',[(.045,1),(.05,2),(.055,2)])
def test_separation_threshold_50ms_in_distinct_basins(monkeypatch,gap,count):
    def peak(id,t):
        return dict(id=id,time_s=t,energy_db=10,dip_db=10,boundary=False,accepted=True,reason=None)
    frames=[dict(time_s=i*.005,energy_db=0,boundary=False) for i in range(81)]
    fine=dict(frames=frames,threshold_db=3,candidates=[peak('f1',.1),peak('f2',.1+gap)],warnings=[])
    structural=dict(frames=frames,threshold_db=3,candidates=[peak('s1',.1),peak('s2',.1+gap)],warnings=[])
    for c in fine['candidates']:
        frames[round(c['time_s']/.005)]['energy_db']=c['energy_db']
    monkeypatch.setattr(ddk_v2,'_scale_detect',lambda samples,rate,a,b,config:copy.deepcopy(fine if config['window_ms']==20 else structural))
    monkeypatch.setattr(ddk_v2,'basins',lambda frames,maxima:[.1+gap/2])
    d=ddk_v2.detect([0]*400,1000,0,400)
    assert len(d['events'])==count
    assert d['candidates'][1]['reasons']==(['minimum_separation'] if count==1 else [])
