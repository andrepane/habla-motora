import test from 'node:test';
import assert from 'node:assert/strict';
import {project,FIELDS,pointer,compareMetadata,assertPhraseBinding,assertAssets} from '../frontend/motor-profile.js';
import {createEvaluation,addAttempt,bind,attach,invalidateAttempt} from '../frontend/motor-profile-store.js';
const m=(value,reason=null)=>({value,reason});
const context={attempt:1,selection_confirmed:true,selection:{start_sample:0,end_sample_exclusive:48000},modality:'direct_reading_v1',phrase_id:'phrase_es_01_v1',administration:{}};
const phrase=()=>({schema_version:'phrase_output_v1',status:'partial',context,selected_duration_s:m(1),production_duration_s:m(1),
  stages:{selection:{status:'completed'},review:{status:'completed'}},review:{confirmed:true,production:'present'},
  rates:{reviewed_word_rate:m(0),reviewed_syllable_rate:m(4),reference_word_rate:m(null,'target_mismatch'),reference_syllable_rate:m(null,'target_mismatch')},
  provenance:{file_sha256:'wav',context_sha256:'ctx',review_sha256:'review'}});
function setup(){
  const e=createEvaluation(),ids={};for(const task of ['vowel','ddk','phrase']){ids[task]=addAttempt(e,task);bind(e,task,ids[task]);}
  const protocol={sources:Object.fromEntries(['vowel','ddk','phrase','pauses','prosody','candidates'].map(k=>[k,{schema_version:k==='vowel'?'vowel_analysis_v1':k==='ddk'?'ddk_output_v1':k==='phrase'?'phrase_output_v1':k==='pauses'?'phrase_pause_output_v1':k==='prosody'?'phrase_prosody_output_v1':'phrase_candidate_execution_v1',checks:[]}]))};
  const sources={};
  const put=(kind,payload)=>{const task=['pauses','prosody','candidates'].includes(kind)?'phrase':kind,id=crypto.randomUUID();
    const s={result_id:id,evaluation_id:e.evaluation_id,attempt_id:ids[task],task,kind,payload,compatibility:['method'],artifact_ref:'artifact.json'};
    attach(e,ids[task],s,payload,Object.fromEntries(Object.entries(sources).map(([k,v])=>[k,v.payload])),protocol);sources[id]=s;return s;
  };return {e,ids,protocol,sources,put,get:()=>project(e,sources,protocol)};
}
test('empty evaluation has five quantitative domains and explicit unassessed intelligibility',()=>{
  const s=setup(),p=s.get();assert.equal(p.completeness.required_domains,5);assert.equal(p.completeness.not_started,5);
  assert.equal(p.intelligibility.status,'not_evaluated');assert.equal(p.snapshot_status,'empty');
});
test('attempt binding is explicit and cannot cross evaluations/tasks',()=>{
  const e=createEvaluation(),id=addAttempt(e,'vowel');assert.equal(e.bindings.vowel,null);
  assert.throws(()=>bind(e,'ddk',id));assert.throws(()=>bind(createEvaluation(),'vowel',id));bind(e,'vowel',id);assert.equal(e.bindings.vowel,id);
});
test('selection never defaults to fastest or latest attempt',()=>{
  const s=setup(),selected=s.e.bindings.phrase;addAttempt(s.e,'phrase');assert.equal(s.e.bindings.phrase,selected);
});
test('closed content review may complete speed while reference rates remain null',()=>{
  const s=setup();s.put('phrase',phrase());const d=s.get().domains.speed;
  assert.equal(d.status,'completed');assert.equal(d.metrics.reference_word_rate.value,null);assert.equal(d.metrics.reference_word_rate.reason,'target_mismatch');
  assert.equal(d.metrics.reviewed_word_rate.value,0);assert.equal(d.metrics.reviewed_word_rate.reason,null);
});
test('unconfirmed selection duration is withheld, despite a numeric source field',()=>{
  const s=setup(),p=phrase();p.stages.selection.status='draft';s.put('phrase',p);
  assert.equal(s.get().domains.speed.metrics.selected_duration_s.reason,'selection_unconfirmed');
});
test('DDK manual closure with insufficient intervals is completed, never substitutes automatic candidates',()=>{
  const s=setup(),r={event_rate_per_s:m(3),group_rate_per_s:m(1),event_count:m(3),group_count:m(1),
    event_regularity:{mean_ms:m(250),sd_ms:m(null,'insufficient_intervals'),cv_percent:m(null,'insufficient_intervals')},
    group_regularity:{mean_ms:m(null,'no_intervals'),sd_ms:m(null,'insufficient_intervals'),cv_percent:m(null,'insufficient_intervals')}};
  const p={schema_version:'ddk_output_v1',status:'partial',stages:{review:{status:'completed'},detection:{status:'completed'}},
    reviewed_result:{confirmed:true,metrics:r},automatic_original:{metrics:{event_rate_per_s:m(999)},detection:{warnings:[]}}};
  s.put('ddk',p);let d=s.get().domains.ddk;assert.equal(d.status,'completed');assert.equal(d.metrics.event_rate_per_s.value,3);
  assert.equal(d.metrics['event_regularity.cv_percent'].reason,'insufficient_intervals');
  p.reviewed_result=null;p.stages.review.status='draft';s.put('ddk',p);d=s.get().domains.ddk;
  assert.equal(d.status,'partial');assert.equal(d.metrics.event_rate_per_s.value,null);assert.equal(d.metrics.event_rate_per_s.reason,'review_pending');
});
test('phonation closes without HNR; pulse measures and HNR remain experimental',()=>{
  const s=setup();s.put('vowel',{schema_version:'vowel_analysis_v1',status:'partial',input:{},modules:{
    shimmer:{status:'completed',result:{acoustic:{f0_mean_hz:m(200),f0_sd_hz:m(0),jitter_local_percent:m(null,'praat_undefined'),shimmer_local_percent:m(null,'praat_undefined')}}},
    hnr:{status:'failed',result:null,error:{message:'controlled'}}}});
  const d=s.get().domains.phonation;assert.equal(d.status,'completed');assert.equal(d.metrics.f0_sd_hz.value,0);
  for(const k of ['hnr_mean_db','jitter_local_percent','shimmer_local_percent'])assert.equal(d.metrics[k].experimental,true);
});
test('confirmed pause review completes with null mean/median and unconfirmed optional count',()=>{
  const s=setup();s.put('phrase',phrase());s.put('pauses',{schema_version:'phrase_pause_output_v1',status:'partial',
    temporal_review:{status:'confirmed'},source_7a:{context,review:{confirmed:true,production:'present'}},
    provenance:{source_dependencies:{file_sha256:'wav',context_sha256:'ctx',review_sha256:'review'}},
    metrics:{pause_count:m(0),pause_percent:m(0),pause_duration_s:m(0),operational_speech_time_s:m(1),
      pause_mean_duration_s:m(null,'no_pauses'),pause_median_duration_s:m(null,'no_pauses'),
      reviewed_syllable_articulation_rate:m(4),reviewed_word_articulation_rate:m(null,'word_count_unconfirmed')}});
  const d=s.get().domains.pauses;assert.equal(d.status,'completed');assert.equal(d.metrics.pause_count.value,0);assert.equal(d.metrics.pause_mean_duration_s.reason,'no_pauses');
});
test('candidate-only source cannot feed any pause metric',()=>{
  const s=setup();s.put('phrase',phrase());s.put('candidates',{schema_version:'phrase_candidate_execution_v1',status:'completed',
    dependencies:{file_sha256:'wav',context_sha256:'ctx',context},automatic_candidates:[{duration_s:4}]});
  const p=s.get();assert.equal(p.domains.pauses.status,'not_started');assert.equal(p.domains.pauses.metrics.pause_count.value,null);assert.equal(p.review_support.feeds_final_metrics,false);
});
test('cross-context dependent sources are rejected',()=>{
  const s=setup();s.put('phrase',phrase());
  assert.throws(()=>s.put('prosody',{schema_version:'phrase_prosody_output_v1',context,dependencies:{file_sha256:'other',context_sha256:'ctx'}}));
  assert.throws(()=>s.put('prosody',{schema_version:'phrase_prosody_output_v1',context:{...context,attempt:2},dependencies:{file_sha256:'wav',context_sha256:'ctx'}}));
});
test('projection refuses cross-evaluation and cross-attempt sources',()=>{
  for(const key of ['evaluation_id','attempt_id','task']){const s=setup(),r=s.put('phrase',phrase());r[key]='foreign';assert.throws(()=>s.get());}
});
test('dependency edit produces stale, removes values and keeps original immutable',()=>{
  const s=setup(),r=s.put('phrase',phrase()),original=JSON.stringify(r.payload);invalidateAttempt(s.e,s.ids.phrase,['phrase'],'selection_changed');
  const p=s.get();assert.equal(p.snapshot_status,'stale');assert.equal(p.domains.speed.metrics.reviewed_word_rate.value,null);
  assert.equal(JSON.stringify(r.payload),original);assert.equal(p.domains.speed.metrics.reviewed_word_rate.reason_origin,'profile');
});
test('configuration/version compatibility is mandatory',()=>{
  const s=setup();s.put('phrase',phrase());s.protocol.sources.phrase.checks=[{pointer:'/protocol_version',value:'future'}];
  assert.equal(s.get().domains.speed.status,'stale');
});
test('no metrics are rounded, recalculated or duplicated as payloads',()=>{
  const s=setup(),p=phrase();p.rates.reviewed_syllable_rate=m(1.23456789012345);const r=s.put('phrase',p),out=s.get();
  const v=out.domains.speed.metrics.reviewed_syllable_rate;assert.equal(v.value,p.rates.reviewed_syllable_rate.value);
  assert.equal(v.source_ref,r.result_id);assert.equal(v.source_pointer,'/rates/reviewed_syllable_rate');assert.equal('payload' in out.source_catalog[r.result_id],false);
});
test('vocal and connected F0 have different task-qualified definitions',()=>{
  assert.notEqual(FIELDS.phonation[0][1],FIELDS.prosody[0][1]);assert.notEqual(FIELDS.phonation[0][3],FIELDS.prosody[0][3]);
});
test('future comparison examines metadata only and never calculates improvement',()=>{
  const a={task:'vowel',definition_id:'vowel.f0.v1',unit:'Hz',acquisition:'automatic',protocol:['v1']};
  assert.equal(compareMetadata(a,a).status,'same_method_metadata');
  for(const key of ['task','definition_id','unit','acquisition','protocol','modality','count_basis'])assert.equal(compareMetadata(a,{...a,[key]:'other'}).status,'compatibility_not_established');
  assert.equal(compareMetadata(a,a).clinical_comparability_established,false);
});
test('integrity errors fail the snapshot, preserve unrelated domains',()=>{
  const s=setup(),r=s.put('phrase',phrase());r.integrity_error=true;const p=s.get();assert.equal(p.snapshot_status,'failed');assert.equal(p.domains.speed.status,'failed');
  assert.equal(p.domains.phonation.status,'not_started');
});
test('null without reason and non-finite metrics are rejected',()=>{
  for(const value of [NaN,Infinity,null]){const s=setup(),p=phrase();p.rates.reviewed_word_rate=m(value);s.put('phrase',p);assert.throws(()=>s.get());}
});
test('closed prosody extraction stays completed with insufficient distributional support',()=>{
  const s=setup();s.put('phrase',phrase());s.put('prosody',{schema_version:'phrase_prosody_output_v1',status:'partial',context,frames:[{defined:true}],
    dependencies:{file_sha256:'wav',context_sha256:'ctx'},metrics:{f0_median_hz:m(200),robust_range_st:m(null,'insufficient_distributional_support'),
      slope_st_s:m(null,'insufficient_temporal_support'),coverage_percent:m(20)}});
  const d=s.get().domains.prosody;assert.equal(d.status,'completed');assert.equal(d.task_state.source_status,'partial');
  assert.equal(d.metrics.robust_range_st.reason_origin,'source');
});
test('no-evaluable temporal review keeps original reasons and is not a failed computation',()=>{
  const s=setup();s.put('phrase',phrase());s.put('pauses',{schema_version:'phrase_pause_output_v1',status:'partial',temporal_review:{status:'not_evaluable'},
    source_7a:{context,review:{confirmed:true,production:'present'}},provenance:{source_dependencies:{file_sha256:'wav',context_sha256:'ctx',review_sha256:'review'}},
    metrics:Object.fromEntries(FIELDS.pauses.map(d=>[d[0],m(null,'pause_review_not_evaluable')]))});
  assert.equal(s.get().domains.pauses.status,'not_evaluable');assert.equal(s.get().domains.pauses.metrics.pause_count.reason_origin,'source');
});
test('changing content review invalidates pauses but leaves compatible F0/candidates untouched',()=>{
  const s=setup();s.put('phrase',phrase());s.put('prosody',{schema_version:'phrase_prosody_output_v1',status:'not_evaluable',context,
    dependencies:{file_sha256:'wav',context_sha256:'ctx'},metrics:{}});
  s.put('pauses',{schema_version:'phrase_pause_output_v1',status:'partial',temporal_review:{status:'draft'},
    source_7a:{context},provenance:{source_dependencies:{file_sha256:'wav',context_sha256:'ctx',review_sha256:'review'}}});
  const p=phrase();p.provenance.review_sha256='changed';s.put('phrase',p);
  assert.equal(s.get().domains.pauses.status,'stale');assert.equal(s.get().domains.prosody.status,'not_evaluable');
});
test('numerator denominator method units and source status are preserved without recomputing',()=>{
  const s=setup(),p=phrase();p.rates.reviewed_word_rate={value:1.25,reason:null,unit:'words/min',numerator:17,denominator_s:888,count_basis:'manual_production_count',method:'source_method'};
  s.put('phrase',p);const v=s.get().domains.speed.metrics.reviewed_word_rate;
  assert.equal(v.value,1.25);assert.equal(v.numerator,17);assert.equal(v.denominator_s,888);assert.equal(v.unit,'words/min');assert.equal(v.method,'source_method');
});
test('missing live identity marks sources stale, never reanalyzes',()=>{
  const s=setup();s.put('phrase',phrase());assert.equal(project(s.e,s.sources,null).domains.speed.status,'stale');
});
test('auditory modalities require the original model asset with the exact 7A hash',()=>{
  const p=phrase();p.context={...context,modality:'auditory_model_only_v1',administration:{model_sha256:'model'}};
  assert.throws(()=>assertAssets('phrase',p,[{role:'wav',sha256:'wav'}]));
  assert.throws(()=>assertAssets('phrase',p,[{role:'wav',sha256:'wav'},{role:'model',sha256:'other'}]));
  assert.doesNotThrow(()=>assertAssets('phrase',p,[{role:'wav',sha256:'wav'},{role:'model',sha256:'model'}]));
});
