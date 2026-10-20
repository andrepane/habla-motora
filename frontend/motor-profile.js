// Projection only. No signal processing, statistics, rates or acoustic imports.
export const SCHEMA = 'motor_speech_profile_v1';
export const BATTERY = 'motor_battery_v1';
export const DOMAIN_NAMES = {
  phonation:'Fonación — vocal sostenida', ddk:'DDK — secuenciación y tiempos revisados',
  speed:'Habla conectada — velocidad', pauses:'Pausas y tiempo operacional',
  prosody:'Prosodia — F0 en habla conectada',
};
export const KINDS = {phonation:'vowel',ddk:'ddk',speed:'phrase',pauses:'pauses',prosody:'prosody'};
export const TASKS = {vowel:'/',ddk:'/ddk',phrase:'/phrase'};
export const pointer = (object, path) => path.split('/').slice(1).reduce((v,k)=>v?.[k.replaceAll('~1','/').replaceAll('~0','~')],object);
const same = (a,b) => JSON.stringify(a)===JSON.stringify(b);
export const fileHash = (kind,p) => kind==='vowel'?p.input?.file_sha256:kind==='ddk'||kind==='phrase'?p.provenance?.file_sha256:kind==='pauses'?p.provenance?.source_dependencies?.file_sha256:p.dependencies?.file_sha256;
export const contextOf = (kind,p) => kind==='pauses'?p.source_7a?.context:p.context ?? p.dependencies?.context;
export const contextHash = (kind,p) => kind==='phrase'?p.provenance?.context_sha256:kind==='pauses'?p.provenance?.source_dependencies?.context_sha256:p.dependencies?.context_sha256;

// [key, label, unit, original JSON pointer, primary, acquisition, experimental]
export const FIELDS = {
  phonation:[
    ['f0_mean_hz','F0 media — vocal sostenida','Hz','/modules/shimmer/result/acoustic/f0_mean_hz',true,'automatic',true],
    ['f0_sd_hz','DT de F0 — vocal sostenida','Hz','/modules/shimmer/result/acoustic/f0_sd_hz',true,'automatic',true],
    ['hnr_mean_db','HNR medio — experimental','dB','/modules/hnr/result/acoustic/hnr_mean_db',true,'automatic',true],
    ['jitter_local_percent','Jitter local — experimental','%','/modules/shimmer/result/acoustic/jitter_local_percent',false,'automatic',true],
    ['shimmer_local_percent','Shimmer local — experimental','%','/modules/shimmer/result/acoustic/shimmer_local_percent',false,'automatic',true],
    ['f0_coverage_percent','Cobertura de F0','%','/modules/shimmer/result/quality/f0_coverage_percent',false,'automatic',true],
    ['hnr_coverage_percent','Cobertura HNR','%','/modules/hnr/result/quality/hnr_coverage_percent',false,'automatic',true],
  ],
  ddk:[
    ...[['event_rate_per_s','Sílabas revisadas/s','sílabas/s',true],['group_rate_per_s','Ciclos revisados/s','ciclos/s',true],
      ['event_regularity/cv_percent','CV entre sílabas revisadas','%',true],['event_count','Sílabas revisadas','count',false],
      ['group_count','Ciclos revisados','count',false],['event_regularity/mean_ms','Intervalo medio entre sílabas','ms',false],
      ['event_regularity/sd_ms','DT entre sílabas','ms',false],['group_regularity/mean_ms','Intervalo medio entre ciclos','ms',false],
      ['group_regularity/sd_ms','DT entre ciclos','ms',false],['group_regularity/cv_percent','CV entre ciclos','%',false]]
      .map(([k,l,u,m])=>[k.replaceAll('/','.'),l,u,'/reviewed_result/metrics/'+k,m,'manual_reviewed',false]),
  ],
  speed:[
    ['reviewed_syllable_rate','Sílabas revisadas/s','sílabas/s','/rates/reviewed_syllable_rate',true,'manual_reviewed',false],
    ['reviewed_word_rate','Palabras revisadas/min','palabras/min','/rates/reviewed_word_rate',true,'manual_reviewed',false],
    ['selected_duration_s','Duración seleccionada 7A','s','/selected_duration_s',true,'manual_selection',false],
    ['production_duration_s','Duración con producción confirmada','s','/production_duration_s',false,'manual_reviewed',false],
    ['reference_syllable_rate','Tasa de referencia — 25 sílabas','sílabas/s','/rates/reference_syllable_rate',false,'versioned_reference',false],
    ['reference_word_rate','Tasa de referencia — 14 palabras','palabras/min','/rates/reference_word_rate',false,'versioned_reference',false],
  ],
  pauses:[
    ...[['reviewed_syllable_articulation_rate','Tasa articulatoria operacional — sílabas','sílabas/s',true],
      ['pause_percent','Porcentaje de pausa revisada','%',true],['pause_count','Pausas revisadas','count',true],
      ['pause_duration_s','Tiempo total de pausas revisadas','s',false],['operational_speech_time_s','Tiempo de habla operacional','s',false],
      ['pause_mean_duration_s','Duración media de pausas','s',false],['pause_median_duration_s','Duración mediana de pausas','s',false],
      ['reviewed_word_articulation_rate','Tasa articulatoria operacional — palabras','palabras/min',false]]
      .map(([k,l,u,m])=>[k,l,u,'/metrics/'+k,m,'manual_reviewed',false]),
  ],
  prosody:[
    ...[['f0_median_hz','F0 mediana — habla conectada','Hz',true],['robust_range_st','Rango robusto P10–P90','ST',true],
      ['slope_st_s','Tendencia global de F0','ST/s',true],['f0_mean_hz','F0 media — habla conectada','Hz',false],
      ['f0_sd_hz','DT de F0','Hz',false],['f0_sd_st','DT de F0','ST',false],['p10_hz','P10 de F0','Hz',false],
      ['p90_hz','P90 de F0','Hz',false],['robust_range_hz','Rango robusto P10–P90','Hz',false],
      ['f0_min_hz','F0 mínima','Hz',false],['f0_max_hz','F0 máxima','Hz',false],['raw_range_hz','Rango bruto','Hz',false],
      ['coverage_percent','Cobertura de F0','%',false],['selection_duration_s','Duración exacta 7A','s',false]]
      .map(([k,l,u,m])=>[k,l,u,'/metrics/'+k,m,'automatic',false]),
  ],
};

export function checkCompatibility(kind,p,protocol) {
  if(!protocol?.sources?.[kind]) return 'identity_unavailable';
  const spec=protocol.sources[kind];
  if(p.schema_version!==spec.schema_version) return 'unsupported_schema';
  for(const c of spec.checks){
    if(c.when && pointer(p,c.when)==null) continue;
    if(pointer(p,c.pointer)!==c.value) return 'configuration_engine_or_protocol_changed';
  }
  return null;
}

export function assertPhraseBinding(kind,p,phrase) {
  if(!['pauses','prosody','candidates'].includes(kind)) return;
  if(!phrase || fileHash(kind,p)!==fileHash('phrase',phrase) || contextHash(kind,p)!==contextHash('phrase',phrase))
    throw Error('Contexto 7A incompatible: WAV, selección, modalidad o intento diferentes.');
  if(kind==='pauses' && p.provenance?.source_dependencies?.review_sha256!==phrase.provenance?.review_sha256)
    throw Error('La revisión 7B.1 pertenece a otra revisión 7A.');
}

function taskState(kind,p) {
  if(p.status==='failed') return {status:'failed',reason:p.reason??'source_failed'};
  if(p.status==='stale') return {status:'stale',reason:p.reason??'source_stale'};
  if(kind==='vowel') {
    const s=p.modules?.shimmer,h=p.modules?.hnr;
    if(s?.status==='failed' && h?.status==='failed') return {status:'failed',reason:'all_modules_failed'};
    // HNR failure/undefined cannot prevent closure of a completed phonation task.
    return {status:s?.status==='completed'?'completed':'partial',reason:s?.status==='completed'?null:'phonation_module_failed',
      review_status:'not_required',source_status:p.status};
  }
  if(kind==='ddk') return {status:p.stages?.review?.status==='completed' && p.reviewed_result?.confirmed?'completed':'partial',
    reason:p.stages?.review?.status==='completed'?null:'review_pending',review_status:p.stages?.review?.status,
    automatic_status:p.stages?.detection?.status,source_status:p.status};
  if(kind==='phrase') return {status:p.stages?.selection?.status==='completed' && p.review?.confirmed && p.review.production!=='pending'?'completed':'partial',
    reason:p.review?.confirmed?null:'content_review_pending',review_status:p.stages?.review?.status,source_status:p.status};
  if(kind==='pauses') return {status:p.temporal_review?.status==='not_evaluable'?'not_evaluable':
    p.temporal_review?.status==='confirmed' && p.source_7a?.review?.confirmed && p.source_7a.review.production==='present'?'completed':'partial',
    reason:p.temporal_review?.status==='not_evaluable'?'pause_review_not_evaluable':null,
    review_status:p.temporal_review?.status,source_status:p.status};
  // A completed extraction with insufficient statistical support is a closed task.
  return {status:p.status==='not_evaluable'?'not_evaluable':p.frames && p.context?.selection_confirmed?'completed':'partial',
    reason:p.reason,review_status:'not_required',source_status:p.status};
}

function rawWarnings(kind,p) {
  if(kind==='vowel') return Object.entries(p.modules??{}).flatMap(([module,r])=>[
    ...(r.result?.quality?.technical_warnings??[]),...(r.error?[{code:'MODULE_FAILED',module,message:r.error.message}]:[])]);
  if(kind==='ddk') return [...(p.automatic_original?.detection?.warnings??[]),
    ...(p.stages?.detection?.status==='failed'?[{code:'AUTOMATIC_DETECTOR_FAILED',message:'La revisión manual conserva su estado propio; el detector automático falló.'}]:[])];
  return p.warnings??p.original_execution?.warnings??[];
}

function metric(kind,def,source,blocked,reason) {
  const [key,label,unit,path,primary,acquisition,experimental]=def;
  const original=source?pointer(source.payload,path):null;
  const missing=original==null;
  if(original!=null && (typeof original!=='object' || !(original.value===null || typeof original.value==='number' && Number.isFinite(original.value))))
    throw Error('Contrato de métrica inválido: '+path);
  if(original?.value===null && !original.reason)throw Error('Métrica nula sin motivo: '+path);
  const value=blocked||missing?null:original.value;
  const why=blocked?reason:missing?'source_field_unavailable':original.reason??null;
  const p=source?.payload;
  return {key,label,value,unit:original?.unit??unit,reason:why,
    reason_origin:blocked||missing?'profile':why?'source':null,
    availability:value!==null?'available':blocked||missing?'unavailable':'not_calculable',
    source_ref:source?.result_id??null,source_pointer:path,
    definition_id:`${kind}.${key}.v1`,primary,acquisition,experimental,
    method:original?.method??null,source_measurement_status:original?.status??null,
    ...(original?.numerator!==undefined?{numerator:original.numerator}:{}),
    ...(original?.denominator_s!==undefined?{denominator_s:original.denominator_s}:{}),
    ...(original?.count_basis!==undefined?{count_basis:original.count_basis}:{}),
    evidence:{technical:'synthetic_technical_only',human_validation:'pending',
      pulse_reliability:kind==='vowel' && ['jitter_local_percent','shimmer_local_percent'].includes(key)?'unverified':undefined},
    comparability:{task:kind,definition_id:`${kind}.${key}.v1`,unit:original?.unit??unit,acquisition,
      protocol:source?.compatibility??null,modality:contextOf(kind,p??{})?.modality??null,
      stimulus:contextOf(kind,p??{})?.phrase_id??null,
      model_sha256:contextOf(kind,p??{})?.administration?.model_sha256??null,
      count_basis:original?.count_basis??acquisition}};
}

export function project(evaluation,sources,protocol) {
  if(evaluation.schema_version!=='motor_evaluation_v1' || evaluation.battery_version!==BATTERY) throw Error('Evaluación no compatible.');
  const domains={};let integrityFailed=false;
  for(const [domain,kind] of Object.entries(KINDS)){
    const task=domain==='phonation'?'vowel':domain==='ddk'?'ddk':'phrase';
    const attemptId=evaluation.bindings[task], attempt=evaluation.attempts[attemptId];
    if(attempt && (attempt.evaluation_id!==evaluation.evaluation_id || attempt.task!==task)) throw Error('Intento de otra evaluación/tarea.');
    const resultId=attempt?.current[kind],source=resultId?sources[resultId]:null;
    let state={status:'not_started',reason:attempt?'source_not_attached':'representative_attempt_not_selected'};
    if(source){
      if(source.evaluation_id!==evaluation.evaluation_id || source.attempt_id!==attemptId || source.kind!==kind || source.task!==task) throw Error('Fuente de otra evaluación/intento/tarea.');
      if(!source.integrity_error && task==='phrase' && contextOf(kind,source.payload)?.attempt!==attempt.ordinal)throw Error('Intento 7A incompatible.');
      if(source.integrity_error){integrityFailed=true;state={status:'failed',reason:'source_integrity_failed'};}
      else {
        state=taskState(kind,source.payload);
        let mismatch=checkCompatibility(kind,source.payload,protocol);
        if(task==='phrase' && kind!=='phrase') {
          const parent=sources[attempt.current.phrase];
          try {assertPhraseBinding(kind,source.payload,parent?.payload);} catch{mismatch='7a_dependency_changed';}
        }
        if(attempt.invalid[kind] || mismatch) state={...state,status:'stale',reason:attempt.invalid[kind]??mismatch};
        if(attempt.errors[kind])state={...state,status:'failed',reason:attempt.errors[kind]};
      }
    }else if(attempt?.errors?.[kind]) state={status:'failed',reason:attempt.errors[kind]};
    const p=source?.payload;
    const blocked=['not_started','stale','failed'].includes(state.status);
    const unreviewed=kind==='ddk' && !p?.reviewed_result?.confirmed || kind==='pauses' && p?.temporal_review?.status!=='confirmed' && state.status!=='not_evaluable';
    domains[domain]={name:DOMAIN_NAMES[domain],status:state.status,reason:state.reason??null,
      task_state:state,attempt_id:attemptId??null,source_refs:source?[source.result_id]:[],
      metrics:Object.fromEntries(FIELDS[domain].map(d=>{
        const selectionPending=kind==='phrase' && d[0]==='selected_duration_s' && p?.stages?.selection?.status!=='completed';
        return [d[0],metric(kind,d,source,blocked||unreviewed||selectionPending,
          blocked?state.reason:selectionPending?'selection_unconfirmed':kind==='ddk'?'review_pending':'pause_review_pending')];
      })),
      evidence:{human_validation:'pending',automatic_is_not_reviewed:true},
      warnings:source&&!source.integrity_error?rawWarnings(kind,p).map(w=>({source_ref:source.result_id,...typeof w==='string'?{code:w}:w})):[],
      details_ref:source?.artifact_ref??null};
  }
  const completeness=Object.fromEntries(['not_started','partial','completed','not_evaluable','stale','failed'].map(s=>[s,Object.values(domains).filter(d=>d.status===s).length]));
  completeness.required_domains=5;
  const catalog=Object.fromEntries(Object.entries(sources).map(([id,s])=>{const {payload,...metadata}=s;return [id,metadata];}));
  return {schema_version:SCHEMA,projection_version:'motor_profile_projection_v1',evaluation:{
    evaluation_id:evaluation.evaluation_id,created_at:evaluation.created_at,updated_at:evaluation.updated_at,
    session_at:evaluation.session_at,time_zone:evaluation.time_zone,case_ref:evaluation.case_ref,battery_version:evaluation.battery_version},
    bindings:structuredClone(evaluation.bindings),source_catalog:catalog,domains,completeness,
    snapshot_status:integrityFailed?'failed':completeness.stale?'stale':completeness.not_started===5?'empty':'current',
    review_support:{candidate_source_ref:evaluation.attempts[evaluation.bindings.phrase]?.current.candidates??null,
      experimental:true,feeds_final_metrics:false},
    intelligibility:{status:'not_evaluated',label:'Inteligibilidad — No evaluada en esta versión',note:evaluation.intelligibility_note??''},
    clinical_notes:evaluation.notes??'',clinical_interpretation_generated:false};
}

export function compareMetadata(a,b) {
  const reasons=[];
  for(const key of ['task','definition_id','unit','acquisition','modality','stimulus','model_sha256','count_basis'])
    if(!same(a[key],b[key])) reasons.push(key+'_changed');
  if(!a.protocol || !b.protocol) reasons.push('version_evidence_missing');
  else if(!same(a.protocol,b.protocol)) reasons.push('protocol_configuration_or_engine_changed');
  return {status:reasons.length?'compatibility_not_established':'same_method_metadata',reasons,
    clinical_comparability_established:false};
}
