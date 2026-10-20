import {DOMAIN_NAMES,TASKS,project} from './motor-profile.js';
import {createEvaluation,saveEvaluation,listEvaluations,getEvaluation,mutateEvaluation,addAttempt,bind,buildProfile,loadSources,exportBundle,importBundle,artifact} from './motor-profile-store.js';
import {segments,edgeRegions} from './phrase-prosody-state.js';
import {metricText} from './audio.js';
const $=id=>document.getElementById(id),el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const statuses={not_started:'Sin iniciar',partial:'Parcial',completed:'Completado',not_evaluable:'No evaluable',stale:'Desactualizado',failed:'Fallido'};
const reasonLabels={insufficient_intervals:'No hay suficientes intervalos',insufficient_distributional_support:'Soporte temporal/distribucional insuficiente',
  insufficient_temporal_support:'Soporte temporal insuficiente',no_pauses:'No hay pausas revisadas',review_pending:'Revisión pendiente',
  representative_attempt_not_selected:'Selecciona explícitamente un intento representativo',source_not_attached:'Todavía no hay un resultado registrado',
  identity_unavailable:'No se pudo verificar la identidad actual del servidor'};
const warningLabels={ACOUSTIC_CANDIDATES_NOT_PHONETIC_RECOGNITION:'El detector produce candidatos acústicos; las cifras revisadas dependen de la confirmación manual.',
  TECHNICAL_VALIDATION_ONLY_HUMAN_VALIDATION_PENDING:'Validación técnica; validación humana pendiente.',
  OPERATIONAL_NOT_PURE_ARTICULATION_TIME:'El tiempo operacional no equivale a articulación pura.',
  UNDEFINED_F0_REGIONS:'Existen regiones sin F0 definida. No equivalen automáticamente a pausas revisadas.',
  LOW_F0_COVERAGE:'Cobertura de F0 baja.',POSSIBLE_OCTAVE_JUMP:'Posible salto de octava; sin corrección automática.',
  EXTREME_DISCONTINUITY:'Discontinuidad extrema de F0.',F0_NEAR_SEARCH_LIMIT:'Valores próximos a límites de búsqueda.',
  SHORT_SELECTION:'Selección corta.',UPPER_FILTERED_BAND:'F0 en la banda superior del extractor filtrado.'};
let id=new URLSearchParams(location.search).get('evaluation_id'),protocol=null,renderRevision=0;
function message(s){$('message').textContent=s;}
async function refreshProtocol(){try{const r=await fetch('/motor-profile-protocol',{cache:'no-store'});if(!r.ok)throw Error();protocol=await r.json();}catch{protocol=null;}}
async function listing(){const evaluations=await listEvaluations();$('evaluations').replaceChildren(new Option('Selecciona una evaluación',''));
  for(const e of evaluations)$('evaluations').add(new Option(`${e.case_ref||e.evaluation_id.slice(0,8)} · ${new Date(e.session_at).toLocaleString()}`,e.evaluation_id));
  $('evaluations').value=id??'';
}
const taskOf=d=>d==='phonation'?'vowel':d==='ddk'?'ddk':'phrase';
function taskUrl(task,attemptId){return `${TASKS[task]}?evaluation_id=${encodeURIComponent(id)}&attempt_id=${encodeURIComponent(attemptId)}`;}
function metricCard(m){const n=el('div',undefined,'profile-metric');n.dataset.metric=m.key;n.append(el('span',m.label),el('strong',metricText(m)),
  el('small',m.value!==null?m.unit:`${reasonLabels[m.reason]??m.reason} · ${m.reason}`),
  el('small',`${m.acquisition==='manual_reviewed'?'Revisada':m.acquisition==='versioned_reference'?'Referencia del estímulo':m.acquisition==='manual_selection'?'Selección manual':'Automática'}${m.experimental?' · Experimental':''}`));return n;}
function miniCurve(host,p){
  if(!p?.frames?.length)return;
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.classList.add('profile-mini');svg.setAttribute('viewBox','0 0 900 200');svg.setAttribute('aria-label','Mini-curva de F0 en Hz, sin interpolar huecos');
  const add=(tag,attrs)=>{const x=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))x.setAttribute(k,v);svg.append(x);return x;};
  const d=p.metrics.selection_duration_s.value,hop=p.configuration.profile.hop_s,runs=segments(p.frames,'hz',hop),values=runs.flat().map(x=>x.value);
  const low=values.length?Math.min(...values)-1:0,high=values.length?Math.max(...values)+1:1;
  const X=t=>20+t/d*860,Y=v=>175-(v-low)/(high-low)*150;
  for(const g of [...edgeRegions(p.frames,d,hop).map(x=>({...x,edge:true})),...(p.gaps??[])]){
    add('rect',{x:X(g.start_s),y:20,width:X(g.end_s)-X(g.start_s),height:155,fill:g.edge?'#ccd6db':'#fae8c5','data-region':g.edge?'edge':'gap'});
  }
  for(const run of runs){add('polyline',{points:run.map(x=>`${X(x.frame.time_relative_s)},${Y(x.value)}`).join(' '),stroke:'#086b76',fill:'none','stroke-width':2,'data-f0-segment':'true'});
    for(const x of run){const c=add('circle',{cx:X(x.frame.time_relative_s),cy:Y(x.value),r:1.5,fill:'#086b76'}),t=document.createElementNS(ns,'title');t.textContent=`${x.frame.time_relative_s} s · ${x.value} Hz · frame ${x.frame.frame_index}`;c.append(t);}}
  host.append(svg,el('small','F0 en Hz · tiempo real de la selección 7A · huecos en ámbar · bordes sin análisis en gris. Sin suavizado.'));
}
async function renderContent(){
  const revision=++renderRevision;await listing();
  $('identity').hidden=$('intelligibility').hidden=$('notesSection').hidden=!id;
  if(!id){$('domains').replaceChildren();return;}
  const e=await getEvaluation(id);if(!e){message('Evaluación no encontrada en este navegador.');return;}
  const sources=await loadSources(e),profile=project(e,sources,protocol);if(revision!==renderRevision)return;
  $('domains').replaceChildren();
  $('evaluationIdentity').textContent=`Evaluación ${e.evaluation_id} · ${e.battery_version} · ${profile.schema_version} · zona ${e.time_zone}`;
  $('case').value=e.case_ref;$('session').value=new Date(new Date(e.session_at).getTime()-new Date(e.session_at).getTimezoneOffset()*60000).toISOString().slice(0,16);
  $('notes').value=e.notes;$('intelligibilityNote').value=e.intelligibility_note;
  $('snapshot').textContent=`Estado del resumen: ${{empty:'Sin resultados incorporados',current:'Actualizado',stale:'Desactualizado',failed:'Fallo de integridad'}[profile.snapshot_status]}. Describe vigencia, no estado clínico.`;
  const c=profile.completeness,counts=[['partial','parcial'],['not_started','sin iniciar'],['not_evaluable','no evaluable'],['stale','desactualizado'],['failed','fallido']]
    .filter(([key])=>c[key]>0).map(([key,label])=>`${c[key]} ${label}${c[key]>1 && !['partial','not_started'].includes(key)?'s':key==='partial'&&c[key]>1?'es':''}`);
  $('completeness').textContent=[`${c.completed}/5 dominios cuantitativos completados`,...counts,'Inteligibilidad no evaluada'].join(' · ');
  $('attempts').replaceChildren();
  for(const [task,name]of [['vowel','Vocal sostenida'],['ddk','DDK'],['phrase','Frase: velocidad, pausas y Prosodia']]){
    const group=el('fieldset');group.append(el('legend',name));const label=el('label','Intento representativo '),select=el('select');select.dataset.binding=task;
    select.append(new Option('Sin seleccionar explícitamente',''));
    for(const a of Object.values(e.attempts).filter(x=>x.task===task)){
      select.append(new Option(`Intento ${a.ordinal}`,a.attempt_id));const link=el('a',`Abrir intento ${a.ordinal}`);link.href=taskUrl(task,a.attempt_id);group.append(link);
    }
    select.value=e.bindings[task]??'';select.onchange=async()=>{await mutateEvaluation(id,e=>bind(e,task,select.value||null));await render();};label.append(select);group.prepend(label);
    const button=el('button','Crear intento');button.dataset.addTask=task;button.onclick=async()=>{try{await mutateEvaluation(id,e=>addAttempt(e,task));await render();message('Intento creado. Elige explícitamente si será el representativo.');}catch(x){message(x.message);}};group.append(button);$('attempts').append(group);
  }
  for(const [key,d]of Object.entries(profile.domains)){
    const card=el('section',undefined,'profile-card');card.dataset.domain=key;card.dataset.status=d.status;
    const top=el('div',undefined,'profile-top');top.append(el('h2',d.name),el('span',statuses[d.status],'profile-status'));card.append(top);
    card.append(el('p',`Tarea original: ${d.task_state.source_status??d.task_state.status} · Revisión: ${d.task_state.review_status??'según tarea'} · Validación humana pendiente.`));
    if(d.reason)card.append(el('p',reasonLabels[d.reason]??d.reason,'profile-warning'));
    const hidePrimary=d.status==='not_started'||key==='ddk'&&d.task_state.review_status!=='completed';
    const metrics=el('div',undefined,'profile-metrics');if(!hidePrimary)for(const m of Object.values(d.metrics).filter(x=>x.primary))metrics.append(metricCard(m));card.append(metrics);
    const source=sources[d.source_refs[0]];
    if(key==='prosody'){
      const coverage=d.metrics.coverage_percent;card.append(el('p',`Cobertura de F0: ${metricText(coverage)}${coverage.value!==null?' %':' · '+coverage.reason}`));
      if(!['stale','failed'].includes(d.status))miniCurve(card,source?.payload);
    }
    if(key==='ddk'&&d.task_state.review_status!=='completed')card.append(el('p','Revisión pendiente. Los candidatos automáticos no se presentan como sílabas revisadas.'));
    if(key==='pauses')card.append(el('p','Tiempo operacional, no articulación pura. 7B.2 es solo soporte experimental de revisión y no alimenta estas cifras.'));
    if(d.warnings.length){const list=el('ul',undefined,'profile-warning');for(const w of d.warnings)list.append(el('li',`${w.message??warningLabels[w.code]??w.code} · ${w.code}`));card.append(list);}
    const link=el('a','Ver tarea');link.href=d.attempt_id?taskUrl(taskOf(key),d.attempt_id):'#attempts';
    if(!d.attempt_id)link.onclick=event=>{event.preventDefault();$('attempts').parentElement.open=true;$('attempts').scrollIntoView();};card.append(link);
    const details=el('details'),grid=el('div',undefined,'profile-details');details.append(el('summary','Detalles técnicos'));
    for(const m of Object.values(d.metrics).filter(x=>hidePrimary||!x.primary))grid.append(metricCard(m));details.append(grid,
      el('p','La completitud describe el cierre de la tarea/revisión. Una métrica puede no ser calculable dentro de un dominio completado.'));
    if(source){
      details.append(el('pre',JSON.stringify({source_ref:source.result_id,source_pointer:'/',payload_sha256:source.payload_sha256,selection:source.selection,
        compatibility:source.compatibility,task_state:d.task_state,metric_provenance:d.metrics},null,2)));
      const show=el('button','Ver resultado original y escuchar WAV'),raw=el('pre');show.onclick=async()=>{try{
        const original=await artifact(source.payload_sha256);raw.textContent=new TextDecoder().decode(original.bytes);
        const wav=source.assets.find(a=>a.role==='wav');const a=await artifact(wav.sha256),audio=el('audio');audio.controls=true;
        audio.src=URL.createObjectURL(new Blob([a.bytes],{type:'audio/wav'}));details.append(audio);show.disabled=true;
      }catch(x){message(x.message);}};details.append(show,raw);
    }
    card.append(details);$('domains').append(card);
  }
  $('audit').textContent=JSON.stringify(profile,null,2);
}
async function render(){try{await renderContent();}catch(e){
  $('domains').replaceChildren();$('snapshot').textContent='Estado del resumen: Fallido.';
  $('completeness').textContent='No se pudo construir un resumen íntegro. Inteligibilidad no evaluada.';
  $('audit').textContent=JSON.stringify({schema_version:'motor_speech_profile_v1',snapshot_status:'failed',reason:e.message});
  message(e.message);
}}
function download(object,name){const url=URL.createObjectURL(new Blob([JSON.stringify(object,null,2)],{type:'application/json'})),a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('new').onclick=async()=>{try{const e=createEvaluation();await saveEvaluation(e);id=e.evaluation_id;history.replaceState(null,'','/profile?evaluation_id='+id);await render();message('Evaluación creada. Crea los intentos y elige los representativos de forma explícita.');}catch(x){message(x.message);}};
$('evaluations').onchange=async()=>{id=$('evaluations').value||null;history.replaceState(null,'','/profile'+(id?'?evaluation_id='+id:''));await render();};
for(const [input,field]of [['case','case_ref'],['notes','notes'],['intelligibilityNote','intelligibility_note']])$(input).onchange=async()=>{
  const value=$(input).value;await mutateEvaluation(id,e=>{e[field]=value;});await render();
};
$('session').onchange=async()=>{if(!$('session').value)return;await mutateEvaluation(id,e=>{e.session_at=new Date($('session').value).toISOString();});await render();};
$('export').onclick=async()=>{try{await refreshProtocol();const p=await buildProfile(id,protocol);download(p,'perfil-habla-motora.json');await render();}catch(x){message(x.message);}};
$('bundle').onclick=async()=>{try{await refreshProtocol();download(await exportBundle(id,protocol),'evaluacion-habla-motora-paquete.json');}catch(x){message(x.message);}};
$('import').onchange=async()=>{try{const file=$('import').files[0];if(!file||file.size>150000000)throw Error('Paquete ausente o superior a 150 MB.');await refreshProtocol();const e=await importBundle(JSON.parse(await file.text()),protocol);id=e.evaluation_id;history.replaceState(null,'','/profile?evaluation_id='+id);await render();message('Paquete verificado y resumen reconstruido desde resultados originales.');}catch(x){message(x.message);}};
window.addEventListener('focus',async()=>{await refreshProtocol();await render();});
document.addEventListener('visibilitychange',async()=>{if(!document.hidden){await refreshProtocol();await render();}});
await refreshProtocol();await render();
