import {BATTERY,project,checkCompatibility,assertPhraseBinding,fileHash,contextOf,pointer} from './motor-profile.js';
const enc=new TextEncoder(),dec=new TextDecoder();
export async function sha(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
export const bytesOf = x => enc.encode(JSON.stringify(x));
const now=()=>new Date().toISOString();
export function createEvaluation(caseRef=''){
  return {schema_version:'motor_evaluation_v1',battery_version:BATTERY,evaluation_id:crypto.randomUUID(),
    created_at:now(),updated_at:now(),session_at:now(),time_zone:Intl.DateTimeFormat().resolvedOptions().timeZone,
    case_ref:caseRef,notes:'',intelligibility_note:'',attempts:{},bindings:{vowel:null,ddk:null,phrase:null},sources:{},history:[]};
}
export function addAttempt(e,task){
  if(!['vowel','ddk','phrase'].includes(task))throw Error('Tarea no admitida.');
  const ordinal=Object.values(e.attempts).filter(a=>a.task===task).length+1;
  if(task==='phrase' && ordinal>2)throw Error('7A admite dos intentos por evaluación. Crea otra evaluación para otra sesión.');
  const id=crypto.randomUUID();e.attempts[id]={attempt_id:id,evaluation_id:e.evaluation_id,task,ordinal,created_at:now(),current:{},invalid:{},errors:{}};
  return id;
}
export function bind(e,task,id){
  if(id!==null && (!e.attempts[id] || e.attempts[id].task!==task || e.attempts[id].evaluation_id!==e.evaluation_id))throw Error('Intento de otra evaluación/tarea.');
  e.bindings[task]=id;
}
export function invalidateAttempt(e,id,kinds,reason){
  const a=e.attempts[id];if(!a)throw Error('Intento desconocido.');
  for(const kind of kinds)if(a.current[kind])a.invalid[kind]=reason;
  e.history.push({event:'invalidated',attempt_id:id,kinds,reason,at:now()});
}
export function attach(e,attemptId,source,payload,payloads,protocol){
  const a=e.attempts[attemptId];
  if(!a || source.evaluation_id!==e.evaluation_id || source.attempt_id!==attemptId || source.task!==a.task)throw Error('Fuente de otra evaluación/intento.');
  const allowed=a.task==='phrase'?['phrase','pauses','candidates','prosody']:[a.task];
  if(!allowed.includes(source.kind))throw Error('Módulo incompatible con tarea.');
  const incompatible=checkCompatibility(source.kind,payload,protocol);if(incompatible)throw Error(incompatible);
  const ctx=contextOf(source.kind,payload);
  if(a.task==='phrase' && ctx?.attempt!==a.ordinal)throw Error('Número de intento 7A incompatible.');
  const parent=payloads[a.current.phrase];assertPhraseBinding(source.kind,payload,parent);
  if(e.sources[source.result_id])throw Error('Resultado inmutable ya registrado.');
  e.sources[source.result_id]=structuredClone(source);a.current[source.kind]=source.result_id;
  delete a.invalid[source.kind];delete a.errors[source.kind];
  if(source.kind==='phrase')for(const kind of ['pauses','candidates','prosody']){
    const previous=payloads[a.current[kind]];
    if(previous)try{assertPhraseBinding(kind,previous,payload);}catch{a.invalid[kind]='7a_dependency_changed';}
  }
  e.history.push({event:'source_attached',result_id:source.result_id,attempt_id:attemptId,at:now()});
}
let dbPromise;
function db(){
  return dbPromise??=new Promise((resolve,reject)=>{
    const r=indexedDB.open('habla-motora-profiles-v1',1);
    r.onupgradeneeded=()=>{r.result.createObjectStore('evaluations',{keyPath:'evaluation_id'});r.result.createObjectStore('artifacts',{keyPath:'id'});};
    r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);
  });
}
async function read(store,id){const d=await db();return new Promise((resolve,reject)=>{const r=d.transaction(store).objectStore(store).get(id);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
export async function listEvaluations(){const d=await db();return new Promise((resolve,reject)=>{const r=d.transaction('evaluations').objectStore('evaluations').getAll();r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
export const getEvaluation=id=>read('evaluations',id);
export async function mutateEvaluation(id,fn){
  const d=await db();return new Promise((resolve,reject)=>{
    const tx=d.transaction('evaluations','readwrite'),store=tx.objectStore('evaluations');let value;
    const r=store.get(id);r.onsuccess=()=>{try{value=r.result;if(!value)throw Error('Evaluación inexistente.');fn(value);value.updated_at=now();store.put(value);}catch(e){tx.abort();reject(e);}};
    tx.oncomplete=()=>resolve(value);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error??Error('Operación cancelada.'));
  });
}
export async function saveEvaluation(e){
  const d=await db();return new Promise((resolve,reject)=>{const tx=d.transaction('evaluations','readwrite');tx.objectStore('evaluations').add(e);tx.oncomplete=()=>resolve(e);tx.onerror=()=>reject(tx.error);});
}
async function putArtifact(bytes,type){
  const id=await sha(bytes),d=await db();
  await new Promise((resolve,reject)=>{const tx=d.transaction('artifacts','readwrite'),s=tx.objectStore('artifacts'),r=s.get(id);
    r.onsuccess=()=>{if(!r.result)s.add({id,type,bytes});};tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});
  return id;
}
export async function artifact(id){const x=await read('artifacts',id);if(!x || await sha(x.bytes)!==id)throw Error('Integridad de artefacto incorrecta: '+id);return x;}
export async function loadSources(e){
  const result={};
  for(const s of Object.values(e.sources)){
    try{const x=await artifact(s.payload_sha256);const payload=JSON.parse(dec.decode(x.bytes));
      for(const a of s.assets??[])await artifact(a.sha256);
      if(s.file_sha256!==fileHash(s.kind,payload) || !s.assets.some(a=>a.role==='wav'&&a.sha256===s.file_sha256))throw Error('Identidad WAV incompatible.');
      result[s.result_id]={...s,payload};
    }catch{result[s.result_id]={...s,integrity_error:true};}
  }
  return result;
}
export async function registerResult(evaluationId,attemptId,kind,payload,assets,protocol,capture=null){
  const initial=await getEvaluation(evaluationId),a=initial?.attempts[attemptId];if(!a)throw Error('Evaluación/intento inexistente.');
  const payloadBytes=bytesOf(payload),payloadHash=await putArtifact(payloadBytes,'application/json');
  const refs=[];
  for(const item of assets){const bytes=await item.blob.arrayBuffer();const hash=await putArtifact(bytes,'audio/wav');refs.push({sha256:hash,role:item.role,name:item.blob.name??'original.wav',size:bytes.byteLength});}
  const wav=refs.find(x=>x.role==='wav');if(!wav || wav.sha256!==fileHash(kind,payload))throw Error('El WAV no corresponde al resultado original.');
  const context=contextOf(kind,payload);
  const source={result_id:crypto.randomUUID(),evaluation_id:evaluationId,attempt_id:attemptId,task:a.task,kind,
    created_at:now(),parent_source_ref:a.task==='phrase'&&kind!=='phrase'?a.current.phrase:null,
    recorded_at:capture?.started_at??null,recorded_at_reason:capture?.started_at?null:'not_exported_by_source',
    capture:structuredClone(capture),schema_version:payload.schema_version,source_status:payload.status,
    payload_sha256:payloadHash,artifact_ref:'artifacts/'+payloadHash+'.json',assets:refs,file_sha256:wav.sha256,
    selection:context?.selection??payload.analysis_interval??null,context:context??null,
    provenance:structuredClone(payload.provenance??payload.dependencies??{}),
    compatibility:protocol.sources[kind].checks.filter(c=>!c.when||pointer(payload,c.when)!=null).map(c=>({pointer:c.pointer,value:pointer(payload,c.pointer)}))};
  // Synchronous mutation inside one IDB transaction: concurrent attempts cannot overwrite each other.
  const loaded=await loadSources(initial),payloads=Object.fromEntries(Object.entries(loaded).map(([id,s])=>[id,s.payload]));
  await mutateEvaluation(evaluationId,e=>{
    // Refuse a late dependent response if 7A changed while assets were being hashed.
    if(JSON.stringify(e.attempts[attemptId].current)!==JSON.stringify(initial.attempts[attemptId].current) ||
       JSON.stringify(e.attempts[attemptId].invalid)!==JSON.stringify(initial.attempts[attemptId].invalid))
      throw Error('El intento cambió durante el registro; vuelve a guardar el resultado vigente.');
    attach(e,attemptId,source,payload,payloads,protocol);
  });
  return source;
}
export async function buildProfile(id,protocol){const e=await getEvaluation(id);if(!e)throw Error('Evaluación inexistente.');return project(e,await loadSources(e),protocol);}
const b64=bytes=>{let s='';const a=new Uint8Array(bytes);for(let i=0;i<a.length;i+=16384)s+=String.fromCharCode(...a.subarray(i,i+16384));return btoa(s);};
export async function exportBundle(id,protocol){
  const evaluation=await getEvaluation(id),sources=await loadSources(evaluation),summary=project(evaluation,sources,protocol);
  if(summary.snapshot_status==='failed')throw Error('No se exporta un paquete con integridad fallida.');
  const ids=new Set(Object.values(evaluation.sources).flatMap(s=>[s.payload_sha256,...s.assets.map(a=>a.sha256)]));
  const artifacts=[];for(const id of ids){const a=await artifact(id);artifacts.push({sha256:id,type:a.type,base64:b64(a.bytes)});}
  return {schema_version:'motor_speech_bundle_v1',evaluation,summary,artifacts};
}
export async function importBundle(bundle,protocol){
  if(bundle.schema_version!=='motor_speech_bundle_v1' || !Array.isArray(bundle.artifacts) || bundle.artifacts.length>1000)throw Error('Paquete no compatible.');
  const e=structuredClone(bundle.evaluation);if(e.schema_version!=='motor_evaluation_v1' || e.battery_version!==BATTERY || !e.evaluation_id)throw Error('Evaluación inválida.');
  if(await getEvaluation(e.evaluation_id))throw Error('Esta evaluación ya existe. La importación no sobrescribe resultados.');
  const map={};for(const a of bundle.artifacts){const bytes=Uint8Array.from(atob(a.base64),x=>x.charCodeAt(0));if(await sha(bytes)!==a.sha256)throw Error('Hash de paquete incorrecto.');map[a.sha256]={bytes,type:a.type};}
  const sources={};
  for(const s of Object.values(e.sources)){
    const a=e.attempts[s.attempt_id];
    if(!a || a.evaluation_id!==e.evaluation_id || s.evaluation_id!==e.evaluation_id || s.task!==a.task || e.sources[s.result_id]!==s)
      throw Error('Fuente de otra evaluación/intento.');
    if(!(a.task==='phrase'?['phrase','pauses','candidates','prosody']:[a.task]).includes(s.kind))throw Error('Tipo de fuente incompatible.');
    const data=map[s.payload_sha256];if(!data)throw Error('Falta el resultado original.');
    for(const a of s.assets)if(!map[a.sha256])throw Error('Falta un WAV/modelo.');
    const payload=JSON.parse(dec.decode(data.bytes));
    if(a.task==='phrase' && contextOf(s.kind,payload)?.attempt!==a.ordinal)throw Error('Intento 7A incompatible.');
    const identity=protocol?.sources?.[s.kind]?.checks.filter(c=>!c.when||pointer(payload,c.when)!=null).map(c=>({pointer:c.pointer,value:pointer(payload,c.pointer)}));
    if(identity && JSON.stringify(identity)!==JSON.stringify(s.compatibility))throw Error('Metadatos de procedencia incompatibles con el original.');
    if(s.file_sha256!==fileHash(s.kind,payload) || !s.assets.some(a=>a.role==='wav'&&a.sha256===s.file_sha256))throw Error('WAV incompatible.');
    sources[s.result_id]={...s,payload};
  }
  for(const s of Object.values(sources))if(['pauses','candidates','prosody'].includes(s.kind)){
    const parent=sources[s.parent_source_ref];
    if(!parent || parent.attempt_id!==s.attempt_id || parent.kind!=='phrase')throw Error('Falta el origen 7A compatible.');
    assertPhraseBinding(s.kind,s.payload,parent.payload);
  }
  // Never trusts the embedded summary; reconstructs from verified source artifacts.
  project(e,sources,protocol);
  for(const [hash,a] of Object.entries(map))await putArtifact(a.bytes,a.type);
  e.history.push({event:'imported',at:now()});await saveEvaluation(e);return e;
}
