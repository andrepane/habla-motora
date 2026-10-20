"""Technical/synthetic validation only. No human prosodic labels."""
import copy
import json
import os
from pathlib import Path
import numpy as np
import pytest
from backend import phrase_prosody as module
from research.prosody.bank import manifest,generate,trajectory
from research.prosody.engine import extract_many,summarize,support,independent_concordance
from research.prosody.profiles import PROFILES,RANGE_RULES
from research.prosody.evaluate import quantile,evaluate
from tests.test_phrase import context

EXE=os.environ.get('PRAAT_EXECUTABLE','praat')

def case(**updates):
    c=next(manifest('development'));c.update(frequency=200.,**updates);return c

def configuration():return dict(profile=PROFILES[3],context_s=0.,range_rule=RANGE_RULES[1],jump_limit_s=.01)

def frame(t,f,i):return dict(frame_index=i,time_absolute_s=t,time_relative_s=t,sample_position_float=t*48000,f0_hz=f,defined=f is not None,undefined_reason=None if f else 'praat_unvoiced_or_unresolved')

def record(fs,native=None):
    values=[f['f0_hz'] for f in fs if f['defined']]
    m=dict(f0_mean_hz=np.mean(values) if values else None,f0_median_hz=quantile(values,.5),f0_sd_hz=0 if len(values)>1 else None,f0_sd_st=0 if len(values)>1 else None,p10_hz=quantile(values,.1),p90_hz=quantile(values,.9),f0_min_hz=min(values) if values else None,f0_max_hz=max(values) if values else None)
    return dict(frames=fs,profile=PROFILES[3],native=native or m)

@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('bits',[16,24,32])
def test_native_concordance_exact_selection_and_formats(rate,bits):
    data,s,_=generate(case(rate=rate,bits=bits));original=bytes(data)
    records=extract_many(data,s,[PROFILES[0],PROFILES[3]],[0.,.25],EXE)
    for r in records.values():
        assert all(s['start_sample']/rate<=f['time_absolute_s']<s['end_sample_exclusive']/rate for f in r['frames'])
        oracle=independent_concordance(r,s,rate,EXE)
        assert oracle['defined_frames']==sum(f['defined'] for f in r['frames'])
        for k,v in r['native'].items():assert oracle[k]==pytest.approx(v,abs=1e-10) if v is not None else oracle[k] is None
        out=summarize(r,s,rate,RANGE_RULES[1],.01)
        assert abs(out['metrics']['f0_median_hz']['value']-200)<.1
        assert out['metrics']['selection_duration_s']['value']==4
    assert data==original

@pytest.mark.parametrize('slope',[-2.,0.,2.])
def test_mathematical_semitones_ols_real_time(slope):
    times=np.arange(.01,3.99,.005);fs=[frame(float(t),float(200*2**(slope*t/12)),i) for i,t in enumerate(times)]
    r=record(fs);o=summarize(r,{'start_sample':0,'end_sample_exclusive':192000},48000,RANGE_RULES[1],.01)
    assert o['metrics']['slope_st_s']['value']==pytest.approx(slope,abs=1e-10)
    assert o['frames_sha256']
    assert fs[10]['f0_st']==pytest.approx(12*np.log2(fs[10]['f0_hz']/r['native']['f0_median_hz']))

@pytest.mark.parametrize('dt',[.005,.010,.020,.050,.500])
@pytest.mark.parametrize('direction',[1,-1])
def test_jump_has_time_direction_and_gap_evidence(dt,direction):
    count=round(dt/.005);fs=[frame(0.,200.,1)]+[frame(i*.005,None,i+1) for i in range(1,count)]+[frame(dt,200*2**direction,count+1)]
    o=summarize(record(fs),{'start_sample':0,'end_sample_exclusive':48000},48000,RANGE_RULES[0],.010)
    jumps=[w for w in o['warnings'] if w['code']=='POSSIBLE_OCTAVE_JUMP']
    assert bool(jumps)==(dt<=.010)
    t=o['transitions'][0];assert t['delta_st']==pytest.approx(12*direction);assert t['delta_t_s']==pytest.approx(dt)
    assert t['gap_duration_s']==pytest.approx(max(0,dt-.005));assert t['direction']==('up' if direction>0 else 'down')

def test_frames_not_independent_distributional_support():
    fs=[frame(float(t),200.,i) for i,t in enumerate(np.arange(1.9,2.1,.005))]
    assert support(fs,4,RANGE_RULES[0])['eligible']
    assert not support(fs,4,RANGE_RULES[1])['eligible']
    o=summarize(record(fs),{'start_sample':0,'end_sample_exclusive':192000},48000,RANGE_RULES[1],.01)
    assert o['metrics']['robust_range_st']['value'] is None
    assert o['metrics']['p10_hz']['reason']=='insufficient_distributional_support'

def test_zero_null_and_no_f0_are_distinct():
    fs=[frame(i*.005,200.,i+1) for i in range(800)]
    out=summarize(record(fs),{'start_sample':0,'end_sample_exclusive':192000},48000,RANGE_RULES[1],.01)
    assert out['metrics']['robust_range_st']['value']==0
    assert out['metrics']['slope_st_s']['value']==0
    fs=[frame(i*.005,None,i+1) for i in range(800)]
    out=summarize(record(fs),{'start_sample':0,'end_sample_exclusive':192000},48000,RANGE_RULES[1],.01)
    assert out['metrics']['coverage_percent']['value']==0 and out['metrics']['f0_median_hz']['value'] is None
    assert out['status']=='not_evaluable'

def test_praat_quantile_oracle_not_numpy_default():
    assert quantile([15,20,32,60],.25)==17.5
    assert quantile([15,20,32,60],.5)==26
    assert quantile([15,20,32,60],.75)==46
    assert quantile([15,20,32,60],.1)==14.5

def test_context_cannot_enter_native_statistics():
    data,s,_=generate(case(family='exterior_different'));r=extract_many(data,s,[PROFILES[3]],[.25],EXE)
    r=next(iter(r.values()));assert abs(r['native']['f0_median_hz']-200)<.1
    assert all(s['start_sample']/44100<=f['time_absolute_s']<s['end_sample_exclusive']/44100 for f in r['frames'])

@pytest.mark.parametrize('field',['file_sha256','context_sha256','selection_sha256','config_sha256','engine_sha256'])
def test_dependency_invalidation_and_immutable_history(field):
    state=module.ProsodyHistory();d={k:'a' for k in ['file_sha256','context_sha256','selection_sha256','config_sha256','engine_sha256']}
    original=dict(dependencies=d,metrics={'x':{'value':1,'reason':None}},frames=[1],status='completed')
    state.accept(original);changed=dict(d);changed[field]='b';state.invalidate(changed)
    assert state.current['status']=='stale' and all(m['value'] is None for m in state.current['metrics'].values())
    assert state.history[0]==original and original['frames']==[1]

@pytest.mark.parametrize('attempt',[1,2])
def test_module_contract_no_changes_to_7a(attempt):
    data,s,_=generate(case());c=context(attempt=attempt,selection=s);original=copy.deepcopy(c)
    out=module.analyze_prosody(data,c,configuration=configuration(),executable=EXE)
    assert out['protocol_version']=='phrase_prosody_v1' and out['status']=='completed'
    assert out['context']['attempt']==attempt and out['frames'] and out['native_audit']
    assert not {'pause_duration_s','pause_count','reference_word_rate'} & out['metrics'].keys()
    assert c==original
    again=module.analyze_prosody(data,c,configuration=configuration(),executable=EXE)
    assert out==again

def test_failed_not_evaluable_stale_and_clipping(monkeypatch):
    data,s,_=generate(case());c=context(selection=s)
    out=module.analyze_prosody(data,c,configuration=configuration(),executable='/not/praat')
    assert out['status']=='failed' and all(m['value'] is None and m['reason'] for m in out['metrics'].values())
    out=module.analyze_prosody(data,context(selection=s,selection_confirmed=False),configuration=configuration(),executable=EXE)
    assert out['status']=='not_evaluable' and out['reason']=='selection_unconfirmed'
    out=module.analyze_prosody(data,c,configuration=configuration(),expected_dependencies={'wrong':1},executable=EXE)
    assert out['status']=='stale'
    data,s,_=generate(case(family='clipping'));out=module.analyze_prosody(data,context(selection=s),configuration=configuration(),executable=EXE)
    assert any(w['code']=='POSSIBLE_DIGITAL_CLIPPING' for w in out['warnings'])

def test_long_gap_null_slope_preserves_original_frames():
    fs=[frame(i*.005,200. if i<80 or i>720 else None,i+1) for i in range(800)]
    out=summarize(record(fs),{'start_sample':0,'end_sample_exclusive':192000},48000,RANGE_RULES[1],.01)
    assert out['metrics']['slope_st_s']['value'] is None and len(fs)==800
    assert out['gaps'][0]['duration_s']>3

@pytest.mark.parametrize('change',['wav','selection','attempt','modality','configuration'])
def test_actual_dependency_hash_changes(change):
    data,s,_=generate(case());c=context(selection=s);cfg=configuration()
    _,before=module.source_dependencies(data,c,cfg)
    if change=='wav':data,_,_=generate(case(phase=1.2))
    elif change=='selection':c['selection']=dict(s,start_sample=s['start_sample']+1)
    elif change=='attempt':c['attempt']=2
    elif change=='modality':
        c['modality']='auditory_model_with_text_v1';c['administration']={'model_id':'controlled','model_sha256':'a'*64,'model_presented_confirmed':True}
    else:cfg['context_s']=.25
    _,after=module.source_dependencies(data,c,cfg)
    assert before!=after


def test_blocked_manifest_is_distinct_and_complete_without_generation():
    dev=list(manifest('development'));blocked=list(manifest('blocked'))
    assert len(dev)==len(blocked)==450
    assert not {r['seed'] for r in dev}&{r['seed'] for r in blocked}
    assert all(a['phase']!=b['phase'] for a,b in zip(dev,blocked))
    assert {c['bits'] for c in dev}=={16,24,32} and {c['rate'] for c in dev}=={44100,48000}
    assert {c['duration'] for c in dev}>={2.,4.,8.,12.,20.}


def test_oracle_exponential_pitch_and_long_gap_metrics():
    c=case(family='linear_st',slope=2.);t=np.array([0.,1.,2.]);freq,_=trajectory(c,t)
    assert np.diff(12*np.log2(freq))==pytest.approx([2.,2.])


def test_frozen_code_guard_and_acceptance_not_silently_revised(tmp_path,monkeypatch):
    import research.prosody.run as runner
    monkeypatch.setattr(runner,'HERE',tmp_path)
    (tmp_path/'freeze.json').write_text(json.dumps({'code_sha256':'wrong'}))
    monkeypatch.setattr(runner,'code_hash',lambda:'actual')
    with pytest.raises(ValueError,match='Code changed'):runner.run('blocked',tmp_path/'out',EXE)


def test_very_short_selection_is_not_execution_failure():
    data,s,_=generate(case());s['end_sample_exclusive']=s['start_sample']+10
    out=module.analyze_prosody(data,context(selection=s),configuration=configuration(),executable=EXE)
    assert out['status']=='not_evaluable' and out['reason']=='insufficient_analysis_duration'
    assert all(m['value'] is None and m['reason'] for m in out['metrics'].values())

@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('bits',[16,24,32])
def test_twenty_second_wav_context_clips_without_exceeding_7a(rate,bits):
    from backend.phrase import read_wav
    data,s,_=generate(case(family='duration',duration=20.,rate=rate,bits=bits))
    assert read_wav(data)['sample_count']==20*rate
    assert s==dict(start_sample=0,end_sample_exclusive=20*rate)
