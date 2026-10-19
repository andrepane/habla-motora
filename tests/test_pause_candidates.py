"""Technical candidate invariants; no human pause validation."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from research.pause_candidates.bank import manifest,generate,encode,FREQUENCIES
from research.pause_candidates.engine import detect,decode,config
from research.pause_candidates.metrics import evaluate,matching
from research.pause_candidates.praat_comparator import detect_praat


def case(**updates):
    c=next(manifest('development'));c.update(updates);return c


@pytest.mark.parametrize('variant',['energy','multifeature'])
@pytest.mark.parametrize('rate',[44100,48000])
@pytest.mark.parametrize('bits',[16,24,32])
def test_contract_reproducibility_no_final_metrics_and_wav_immutable(variant,rate,bits):
    d,s,t=generate(case(rate=rate,bits=bits,duration_ms=500));original=bytes(d);selection=copy.deepcopy(s)
    a=detect(d,s,'context',variant);b=detect(d,s,'context',variant)
    assert a==b and d==original and s==selection
    assert a['status']=='completed' and a['automatic_candidates']
    assert a['manual_final_result'] is None and not a['manual_annotations'] and not a['candidate_decisions']
    assert not {'pause_duration_s','pause_count','operational_speech_time_s','pause_percent','f0'}&a.keys()
    for c in a['automatic_candidates']:
        assert c['status']=='unreviewed'
        assert c['duration_s']==c['duration_samples']/rate
        assert c['duration_samples']*1000>=80*rate
        assert c['config_sha256']==a['config_sha256']
        assert c['features'] and c['technical_evidence'] and c['proposal_reasons']
    m=evaluate(a['automatic_candidates'],t['region_references'],rate,4*rate)
    assert m['recall']==1


@pytest.mark.parametrize('frequency',FREQUENCIES)
def test_high_frequency_periodicity_evidence_not_f0(frequency):
    d,s,_=generate(case(frequency_hz=frequency,family='no_pause'))
    a=detect(d,s,'context','multifeature')
    assert a['configuration']['periodicity_ceiling_hz']==700
    values=[f['periodicity'] for f in a['frame_trace'] if f['periodicity'] is not None]
    assert values and all(0<=p<=1 for p in values)
    assert not any('f0' in f for f in a['frame_trace'])


def test_energy_uses_only_A_multifeature_is_superset_without_merging():
    d,s,_=generate(case(family='low_energy_present',duration_ms=500))
    a=detect(d,s,'context','energy');b=detect(d,s,'context','multifeature')
    bounds=lambda r:{(c['start_sample'],c['end_sample_exclusive']) for c in r['automatic_candidates']}
    assert bounds(a)<=bounds(b)
    assert all(c['proposal_reasons']==['A_energy_depression'] for c in a['automatic_candidates'])
    assert all('periodicity' not in f for f in a['frame_trace'])
    assert a['config_sha256']!=b['config_sha256']


@pytest.mark.parametrize('duration',[100,200,249,250,251,300,500,1000])
def test_candidates_do_not_use_manual_250_threshold(duration):
    d,s,t=generate(case(duration_ms=duration))
    a=detect(d,s,'context')
    assert a['automatic_candidates']
    assert all(c['status']=='unreviewed' for c in a['automatic_candidates'])
    assert bool(t['pause_proxy_references'])==(duration>=250)


@pytest.mark.parametrize('bits',[16,24,32])
def test_signed_pcm_decode(bits):
    x=np.array([-.9,-.2,0,.1,.9]*9000,dtype=float)
    d=encode(x,44100,bits);decoded,_=decode(d)
    assert np.max(np.abs(decoded-x))<=2/2**(bits-1)


def test_no_proposals_not_equal_no_pauses_and_failures_not_empty():
    d,s,_=generate(case(family='all_silence'));a=detect(d,s,'context')
    assert a['status']=='not_evaluable' and a['automatic_candidates'] is None
    d,s,_=generate(case(family='no_pause'));a=detect(d,s,'context')
    assert a['status']=='completed' and a['automatic_candidates']==[]
    assert a['manual_final_result'] is None
    failed=detect_praat(d,s,'context',executable='/not-a-praat')
    assert failed['status']=='failed' and failed['automatic_candidates'] is None


def test_selection_hash_invalidation_and_absolute_coordinates():
    d,s,_=generate(case(duration_ms=500));a=detect(d,s,'one')
    s['start_sample']=1000;b=detect(d,s,'one');c=detect(d,s,'two')
    assert len({a['run_id'],b['run_id'],c['run_id']})==3
    assert b['automatic_candidates'][0]['start_sample']>44100
    s['confirmed']=False
    with pytest.raises(ValueError):detect(d,s,'one')


def test_two_regions_not_joined_across_brief_activity():
    d,s,t=generate(case(family='two_close',duration_ms=500,gap_between_s=.05))
    a=detect(d,s,'context')
    assert len(a['automatic_candidates'])==2
    assert evaluate(a['automatic_candidates'],t['region_references'],44100,4*44100)['fusion_count']==0


def test_metrics_exact_matching_and_null_denominators():
    interval=lambda a,b:dict(start_sample=a,end_sample_exclusive=b)
    refs=[interval(100,200),interval(240,340)]
    candidates=[interval(90,210),interval(240,340),interval(500,600)]
    m=evaluate(candidates,refs,1000,4000)
    assert m['tp']==2 and m['fp']==1 and m['false_candidates_per_minute']==15
    assert m['start_error_ms']==[-10,0] and m['end_error_ms']==[10,0]
    assert evaluate([],[],1000,4000)['recall'] is None
    assert evaluate([],[],1000,4000)['precision'] is None
    # A wide interval can match either reference; narrower one must keep its only match.
    assert len(matching([interval(100,340),interval(100,200)],refs,.3))==2
    assert evaluate([interval(100,340)],refs,1000,4000)['fusion_count']==1
    assert evaluate([interval(100,160),interval(160,200)],refs[:1],1000,4000)['fragmentation_count']==1


def test_manifests_disjoint_balanced_and_reference_durations_actual_samples():
    dev=list(manifest('development'));blocked=list(manifest('blocked'))
    assert len(dev)==len(blocked)==3264
    assert not {c['case_id'] for c in dev}&{c['case_id'] for c in blocked}
    assert {c['seed'] for c in dev}.isdisjoint(c['seed'] for c in blocked)
    for rate in (44100,48000):
        _,_,t=generate(case(rate=rate,duration_ms=249))
        assert t['duration_samples']==round(.249*rate)


def test_blocked_runner_requires_frozen_gate(tmp_path):
    from research.pause_candidates.run_bank import run
    with pytest.raises(ValueError,match='frozen gate'):run('blocked',tmp_path)
