import {project} from './motor-profile.js';
export const taskNames={vowel:'Vocal',ddk:'DDK',phrase:'Habla conectada'};
export const stateLabels={not_started:'Pendiente',partial:'Pendiente de revisión',completed:'Completada',stale:'Necesita actualizarse',failed:'No se pudo completar',not_evaluable:'No evaluable'};
export function attemptSummary(e,a,sources,protocol){
 const copy=structuredClone(e);copy.bindings[a.task]=a.attempt_id;
 const p=project(copy,sources,protocol),keys=a.task==='vowel'?['phonation']:a.task==='ddk'?['ddk']:['speed','pauses','prosody'];
 const domains=Object.fromEntries(keys.map(k=>[k,p.domains[k]]));
 const main=domains[keys[0]],statuses=Object.values(domains).map(d=>d.status);
 const status=statuses.includes('failed')?'failed':statuses.includes('stale')?'stale':statuses.every(s=>s==='completed')?'completed':a.current[a.task]?'partial':'not_started';
 return {status,label:status==='not_started'?'En curso':stateLabels[status],eligible:main.status==='completed',domains,representative:e.bindings[a.task]===a.attempt_id};
}
export function recommended(e,rows){
 for(const task of ['vowel','ddk','phrase']){
  const attempts=rows.filter(r=>r.attempt.task===task),bound=attempts.find(r=>r.summary.representative),r=bound||attempts.at(-1);
  if(!r)return {task,label:'Comenzar '+taskNames[task],create:true};
  const {attempt:a,summary:s}=r;
  if(s.status==='failed'||s.status==='stale')return {task,attempt:a.attempt_id,label:'Continuar '+taskNames[task]};
  if(!s.eligible)return {task,attempt:a.attempt_id,label:task==='ddk'&&a.current.ddk?'Revisar DDK':task==='phrase'&&a.current.phrase?'Revisar contenido':'Continuar '+taskNames[task],step:task==='phrase'?'content':undefined};
  if(task==='phrase'){
   if(!['completed','not_evaluable'].includes(s.domains.pauses.status))return {task,attempt:a.attempt_id,label:'Revisar pausas',step:'pauses'};
   if(!['completed','not_evaluable'].includes(s.domains.prosody.status))return {task,attempt:a.attempt_id,label:'Analizar Prosodia',step:'prosody'};
  }
  if(!bound)return {task,attempt:a.attempt_id,label:'Usar este intento en el Perfil',choose:true};
 }
 return {label:'Ver Perfil',profile:true};
}
