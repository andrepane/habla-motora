import {createEvaluation,saveEvaluation,listEvaluations,getEvaluation,mutateEvaluation,addAttempt,bind,loadSources,importBundle} from './motor-profile-store.js';
import {attemptSummary,recommended,taskNames} from './evaluation-flow.js';
import {evaluationUrl,linkNavigation} from './evaluation-navigation.js';
const $=id=>document.getElementById(id),node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
let id=new URLSearchParams(location.search).get('evaluation_id'),protocol,revision=0;
const message=s=>$('message').textContent=s;
function go(task,attempt,step){const u=new URL(evaluationUrl(id,task,attempt),location.origin);if(step)u.searchParams.set('step',step);location.href=u;}
async function create(task){let aid;await mutateEvaluation(id,e=>aid=addAttempt(e,task));go(task,aid);}
async function render(){const version=++revision;try{
 const response=await fetch('/motor-profile-protocol',{cache:'no-store'});if(!response.ok)throw Error('No se pudo comprobar la versión de evaluación.');protocol=await response.json();
 const evaluations=await listEvaluations();$('evaluations').replaceChildren(new Option('Selecciona una evaluación',''));for(const e of evaluations)$('evaluations').add(new Option(`${e.case_ref||'Evaluación'} · ${new Date(e.session_at).toLocaleString()}`,e.evaluation_id));$('evaluations').value=id||'';
 $('identity').hidden=$('profileLink').hidden=!id;$('tasks').replaceChildren();linkNavigation(id);
 if(!id)return;const e=await getEvaluation(id);if(!e)throw Error('Evaluación no encontrada en este navegador.');const sources=await loadSources(e);if(version!==revision)return;linkNavigation(id,e);
 $('case').value=e.case_ref;$('session').value=new Date(new Date(e.session_at).getTime()-new Date(e.session_at).getTimezoneOffset()*60000).toISOString().slice(0,16);
 const rows=Object.values(e.attempts).map(a=>({attempt:a,summary:attemptSummary(e,a,sources,protocol)}));
 $('evaluationState').textContent=rows.some(r=>r.summary.status==='failed')?'Hay una tarea que no se pudo completar':rows.some(r=>r.summary.status==='stale')?'Hay resultados que necesitan actualizarse':rows.length?'Evaluación en curso':'Evaluación pendiente';
 const completed=rows.filter(r=>r.summary.representative).flatMap(r=>Object.values(r.summary.domains)).filter(d=>d.status==='completed').length;
 $('completeness').textContent=`${completed}/5 dominios cuantitativos completados · Inteligibilidad no evaluada`;
 const next=recommended(e,rows),button=node('button',next.label);button.id='recommended';button.onclick=async()=>{try{if(next.create)await create(next.task);else if(next.choose){await mutateEvaluation(id,e=>bind(e,next.task,next.attempt));await render();}else if(next.profile)location.href=evaluationUrl(id);else go(next.task,next.attempt,next.step);}catch(x){message(x.message);}};$('next').replaceChildren(node('p','Siguiente paso recomendado'),button);
 for(const task of ['vowel','ddk','phrase']){
  const section=node('section');section.dataset.task=task;section.append(node('h2',taskNames[task]));const attempts=rows.filter(r=>r.attempt.task===task);if(!attempts.length)section.append(node('p','Pendiente'));
  for(const {attempt:a,summary:s}of attempts){const row=node('article');row.dataset.attempt=a.attempt_id;row.append(node('h3',`Intento ${a.ordinal}`),node('p',`${s.label} · ${new Date(a.created_at).toLocaleString()}${s.representative?' · Elegido para el Perfil':''}`));
   const open=node('a',a.current[task]?'Consultar / continuar':'Continuar intento');open.href=evaluationUrl(id,task,a.attempt_id);row.append(open);
   if(s.eligible&&!s.representative){const use=node('button','Usar este intento en el Perfil');use.onclick=async()=>{try{await mutateEvaluation(id,e=>bind(e,task,a.attempt_id));await render();}catch(x){message(x.message);}};row.append(use);}section.append(row);
  }
  const add=node('button',attempts.length?'Crear nuevo intento':'Comenzar '+taskNames[task]);add.dataset.createTask=task;add.disabled=task==='phrase'&&attempts.length>=2;add.onclick=()=>create(task).catch(x=>message(x.message));section.append(add);$('tasks').append(section);
 }
 $('viewProfile').href=evaluationUrl(id);
 const manage=new URLSearchParams(location.search).get('manage_task');if(manage)$('tasks').querySelector(`[data-create-task="${manage}"]`)?.focus();
}catch(e){$('next').replaceChildren();message(e.message);}}
$('new').onclick=async()=>{try{const e=createEvaluation();await saveEvaluation(e);id=e.evaluation_id;history.pushState(null,'','/evaluation?evaluation_id='+id);await render();}catch(e){message(e.message);}};
$('evaluations').onchange=()=>location.href=$('evaluations').value?'/evaluation?evaluation_id='+encodeURIComponent($('evaluations').value):'/evaluation';
$('import').onchange=async()=>{try{const f=$('import').files[0];if(!f||f.size>150000000)throw Error('Paquete ausente o superior a 150 MB.');const e=await importBundle(JSON.parse(await f.text()),protocol);id=e.evaluation_id;history.pushState(null,'','/evaluation?evaluation_id='+id);await render();message('Evaluación importada y verificada.');}catch(e){message(e.message);}};
for(const [field,key]of [['case','case_ref'],['session','session_at']])$(field).onchange=async()=>{try{const v=$(field).value;if(key==='session_at'&&!v)return;await mutateEvaluation(id,e=>e[key]=key==='session_at'?new Date(v).toISOString():v);await render();}catch(e){message(e.message);}};
window.addEventListener('popstate',()=>{id=new URLSearchParams(location.search).get('evaluation_id');render();});window.addEventListener('focus',render);await render();
