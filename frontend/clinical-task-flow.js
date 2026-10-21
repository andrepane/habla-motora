// Presentation only. Existing task controllers own every calculation and confirmation.
const make=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
export function mountTaskSteps(task,bridge){
 const list=make('ol');list.className='flow-context';list.setAttribute('aria-label','Pasos de la tarea');
 for(const text of task==='vowel'?['Preparación','Grabar o subir audio','Escuchar','Seleccionar emisión','Analizar','Revisar resultado','Usar intento en Perfil / continuar']:['Preparación','Grabación o subida','Detección de candidatos','Revisión manual','Confirmación','Resultado revisado'])list.append(make('li',text));
 document.querySelector('.profile-bridge')?.after(list);
 if(task==='ddk')document.querySelector('#reviewSection h2').textContent='Revisión manual de acontecimientos';
}
export function mountPhraseSteps(slots,bridge){
 for(const s of slots){
  const direct=[...s.section.children],selection=s.q('.wave').closest('fieldset'),record=s.get('file').closest('fieldset'),content=s.q('.review'),pauses=s.q('.pausePanel'),candidates=s.q('.candidatePanel'),prosody=s.q('.prosodyPanel');
  const nav=make('nav');nav.className='flow-nav';nav.setAttribute('aria-label','Pasos de Habla conectada');s.section.prepend(nav);
  const source=make('div');source.className='flow-source';selection.before(source);
  // One waveform and player are reused across selection and pause review.
  const shared=[s.q('.audio'),s.q('.wave'),s.q('.times'),s.q('.zoomSelection'),s.q('.zoomReset'),s.q('.playSelection')];
  for(const n of shared)source.append(n);
  const help=make('details');help.className='candidateHelp';help.append(make('summary','Ayuda opcional: proponer y revisar candidatos'),candidates);pauses.querySelector('[data-p="editing"]').closest('label').before(help);
  for(const [panel,title]of [[content,'Revisión de contenido'],[pauses,'Pausas revisadas'],[candidates,'Candidatos automáticos — ayuda opcional'],[prosody,'Prosodia']])panel.querySelector('legend').textContent=title;
  const selectionTitle=selection.querySelector('legend');selectionTitle.textContent='Seleccionar y confirmar la producción';
  const original=[...direct].filter(n=>![content,pauses,candidates,prosody].includes(n));
  let step='recording',all=false;
  const options=make('details');options.append(make('summary','Opciones técnicas de navegación'));const showAll=make('button','Mostrar todos los apartados');showAll.type='button';showAll.className='showAllSteps';showAll.onclick=()=>window.dispatchEvent(new Event('motor-show-all'));options.append(showAll);nav.after(options);const wanted=new URLSearchParams(location.search).get('step');
  const keys=['recording','content','pauses','prosody'],labels=['Grabación y selección','Contenido','Pausas','Prosodia'],buttons=new Map();
  function available(key){return key==='recording'||key==='content'&&!!s.state.contextResult?.context.selection_confirmed||key==='pauses'&&!!s.state.result?.review?.confirmed&&s.state.result.review.production==='present'||key==='prosody'&&!!s.state.contextResult?.context.selection_confirmed;}
  function show(key){if(!available(key))return;step=key;render();}
  for(let i=0;i<keys.length;i++){const key=keys[i],b=make('button',labels[i]);b.type='button';b.dataset.phraseStep=key;b.onclick=()=>show(key);buttons.set(key,b);nav.append(b);}
  const footer=make('div');footer.className='flow-actions';const next=make('button');next.type='button';next.dataset.nextStep='true';footer.append(next);s.section.append(footer);
  function render(){
   if(bridge.isConsulting())return;
   if(!available(step))step='recording';
   if(all){help.open=true;raw.open=true;for(const n of original)n.hidden=false;content.hidden=pauses.hidden=prosody.hidden=source.hidden=false;s.q('.model').hidden=s.get('modality').value==='direct_reading_v1';s.q('.stimulus').hidden=s.get('modality').value==='auditory_model_only_v1';next.hidden=true;return;}
   for(const [key,b]of buttons){b.disabled=!available(key);b.setAttribute('aria-current',step===key?'step':'false');}
   for(const n of original)n.hidden=step!=='recording'&&!(step==='content'&&n.matches('.state,.results,details'));
   // Original rendering owns result visibility, avoid moving controls or confirming anything.
   content.hidden=step!=='content';pauses.hidden=step!=='pauses';prosody.hidden=step!=='prosody';
   source.hidden=!['recording','content','pauses'].includes(step);
   if(step==='recording')s.q('.model').hidden=s.get('modality').value==='direct_reading_v1';
   const i=keys.indexOf(step),key=keys[i+1];next.hidden=!key;next.disabled=!!key&&!available(key);next.textContent=key?'Continuar con '+labels[i+1]:'';next.onclick=()=>show(key);
  }
  // Structured event controls serialize to the unchanged type: note contract.
  const textarea=s.get('events'),label=textarea.closest('label'),editor=make('fieldset');editor.append(make('legend','Acontecimientos observados (opcional)'));
  const select=make('select');select.setAttribute('aria-label','Tipo de acontecimiento');
  for(const [v,t]of [['omission','Omisión'],['repetition','Repetición'],['substitution','Sustitución'],['fragment','Fragmento'],['restart','Reinicio'],['addition','Adición'],['filled_pause','Pausa llena'],['uncertain','Dudoso']])select.add(new Option(t,v));
  const note=make('input');note.setAttribute('aria-label','Nota del acontecimiento');const add=make('button','Añadir acontecimiento');add.type='button';
  let lastEvents=null;const rows=make('div');const sync=()=>{lastEvents=textarea.value;rows.replaceChildren();for(const [i,line]of textarea.value.split('\n').filter(x=>x.trim()).entries()){const type=line.split(':',1)[0].trim(),name=[...select.options].find(o=>o.value===type)?.textContent;const row=make('p',name?name+' · '+line.slice(line.indexOf(':')+1).trim():line),remove=make('button','Eliminar acontecimiento');remove.type='button';remove.onclick=()=>{const lines=textarea.value.split('\n').filter(x=>x.trim());lines.splice(i,1);textarea.value=lines.join('\n');textarea.dispatchEvent(new Event('input',{bubbles:true}));sync();};row.append(remove);rows.append(row);}};
  add.onclick=()=>{textarea.value+=(textarea.value?'\n':'')+select.value+': '+note.value.replaceAll('\n',' ');textarea.dispatchEvent(new Event('input',{bubbles:true}));note.value='';sync();};editor.append(select,note,add,rows);label.before(editor);const raw=make('details');raw.append(make('summary','Formato técnico de acontecimientos'));label.before(raw);raw.append(label);const types=raw.nextElementSibling;if(types?.textContent.startsWith('Tipos:'))raw.append(types);
  // Changes in task DOM trigger view updates; own view writes are excluded.
  let scheduled=false;
  const update=()=>{if(scheduled)return;scheduled=true;queueMicrotask(()=>{scheduled=false;if(textarea.value!==lastEvents)sync();render();});};
  s.section.addEventListener('input',update);s.section.addEventListener('change',update);
  const obs=new MutationObserver(records=>{if(records.some(r=>!r.target.closest?.('.flow-nav,.flow-actions')&&r.type==='childList'))update();});
  obs.observe(s.section,{childList:true,subtree:true});
  window.addEventListener('motor-show-all',()=>{all=true;render();});
  window.addEventListener('motor-result-saved',update);window.addEventListener('motor-phrase-resumed',()=>{sync();if(wanted&&available(wanted))step=wanted;render();});window.addEventListener('motor-edit-start',()=>{step='recording';queueMicrotask(render);});
  render();
 }
}
