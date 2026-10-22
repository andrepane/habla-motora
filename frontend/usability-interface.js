import {secondsAt,sampleAtSeconds,reasonLabels,displayUnit,pauseDisplay} from './usability-labels.js';
// Presentation only: no API/storage access, source writes, or clinical calculations.
const page=document.body.dataset.page,main=document.querySelector('main');
const make=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const json=n=>{try{return JSON.parse(n?.textContent||'{}');}catch{return {};}};
function details(parent,key,title){let d=parent.querySelector(`:scope > details[data-polish="${key}"]`);if(!d){d=make('details');d.dataset.polish=key;d.className='polish-details';d.append(make('summary',title));parent.append(d);}return d;}
function placeAfter(node,anchor){if(node&&anchor&&anchor.nextElementSibling!==node)anchor.after(node);}
const mirrors=new Map();
function rateOf(slot){const text=slot.querySelector('.times')?.textContent??'';return Number(/^(\d+) Hz/.exec(text)?.[1])||null;}
function sampleControl(input,slot,label){
 if(!input)return;
 let entry=mirrors.get(input);
 if(!entry){
  const originalLabel=input.closest('label'),host=originalLabel.parentElement;
  const group=make('div');group.className='seconds-control';const l=make('label',label+' (s)'),seconds=make('input');seconds.type='number';seconds.min='0';seconds.step='any';seconds.dataset.secondsFor=input.dataset.f?'f-'+input.dataset.f:input.dataset.p?'p-'+input.dataset.p:'key-'+input.dataset.key;l.append(seconds);group.append(l);
  const exact=details(host,'samples','Detalles técnicos: índices de muestra exactos');exact.classList.add('sample-details');originalLabel.before(group);exact.append(originalLabel);
  const equivalence=make('small');originalLabel.append(equivalence);if(/Final/.test(label)){const note=make('small','El final queda fuera del intervalo. La edición se ajusta a la muestra más próxima.');group.append(note);}
  entry={input,seconds,equivalence,slot};mirrors.set(input,entry);
  seconds.addEventListener('input',()=>{const rate=rateOf(slot),value=seconds.value===''?null:sampleAtSeconds(Number(seconds.value),rate);if(value===null){seconds.setCustomValidity('Introduce un tiempo válido con audio disponible.');input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));update();return;}seconds.setCustomValidity('');input.value=String(value);input.dispatchEvent(new Event('input',{bubbles:true}));update();});
 }
 const rate=rateOf(slot),index=input.value===''?null:Number(input.value),value=secondsAt(index,rate);
 const disabled=input.disabled||!rate;if(entry.seconds.disabled!==disabled)entry.seconds.disabled=disabled;
 if(document.activeElement!==entry.seconds&&entry.seconds.value!==(value===null?'':String(value)))entry.seconds.value=value===null?'':String(value);
 const text=value===null?'Tiempo no disponible':`${index} muestras ÷ ${rate} Hz = ${value} s`;
 if(entry.equivalence.textContent!==text)entry.equivalence.textContent=text;
}
function foldCards(container,keep,title){if(!container)return;const secondary=[...container.children].filter(n=>n.matches('.metric,.card')&&!keep(n));if(!secondary.length)return;const d=details(container,'metrics',title);d.classList.add('secondary-metrics');for(const n of secondary)if(n.parentElement!==d)d.append(n);}
function paint(){
 // Move existing action nodes; never duplicate handlers or enable controls.
 const actions=document.querySelector('#clinicalActions'),consult=document.querySelector('#savedTask:not([hidden])');
 if(page==='vowel'){
  const cards=document.querySelector('#cards');foldCards(cards,n=>!/[Jj]itter|[Ss]himmer/.test(n.textContent),'Jitter y shimmer · medidas experimentales');
  const results=document.querySelector('#results'),charts=results?.querySelector('.charts');if(results&&charts&&!charts.closest('details')){const d=details(results,'curves','Curvas y soporte técnico');d.append(charts);}
  if(!consult)placeAfter(actions,document.querySelector('#warnings'));
 }
 if(page==='ddk'){
  const cards=document.querySelector('#reviewedCards');if(cards){const original=[...cards.querySelectorAll(':scope > .card')];foldCards(cards,n=>original.indexOf(n)<4,'Regularidad temporal · detalles');}
  const section=document.querySelector('#reviewSection');if(section){const d=details(section,'review-charts','Gráficos e intervalos revisados');for(const n of [document.querySelector('#eventChart'),document.querySelector('#intervalChart'),document.querySelector('#intervalTable')?.closest('.tableScroll')])if(n&&n.parentElement!==d)d.append(n);}
  if(!consult)placeAfter(actions,cards);
  const table=document.querySelector('#editTable'),scroll=table?.closest('.tableScroll');if(scroll){let hint=scroll.previousElementSibling;if(!hint?.classList.contains('table-hint')){hint=make('p','Desliza para ver más · el acontecimiento permanece fijo a la izquierda.');hint.className='table-hint';hint.id='ddk-scroll-help';scroll.before(hint);scroll.setAttribute('aria-describedby',hint.id);}const hidden=scroll.scrollWidth<=scroll.clientWidth+1;if(hint.hidden!==hidden)hint.hidden=hidden;}
 }
 for(const slot of document.querySelectorAll('#attempts > section')){
  if(!slot.querySelector('.flow-nav'))continue;
  const step=slot.querySelector('[aria-current="step"]')?.dataset.phraseStep;
  const footer=slot.querySelector('[data-next-step]')?.parentElement;
  const close=step==='pauses'?slot.querySelector('[data-p="state"]'):step==='prosody'?slot.querySelector('[data-pr="warnings"]'):slot.querySelector('.state');
  if(step!=='prosody')placeAfter(footer,close);
  if(!consult&&actions&&slot.offsetWidth){if(step==='prosody')placeAfter(actions,close);else if(footer)placeAfter(actions,footer);}
  const results=slot.querySelector('.results');foldCards(results,n=>!/referencia/.test(n.textContent),'Tasas de referencia del estímulo');
  for(const [selector,label]of [['[data-f="start"]','Inicio'],['[data-f="end"]','Final'],['[data-p="start"]','Inicio del intervalo'],['[data-p="end"]','Final del intervalo'],['[data-key="start_sample"]','Inicio del intervalo'],['[data-key="end_sample_exclusive"]','Final del intervalo']])for(const input of slot.querySelectorAll(selector))sampleControl(input,slot,label);
  const times=slot.querySelector('.times');if(times){const rate=rateOf(slot),a=Number(slot.querySelector('[data-f="start"]')?.value),b=Number(slot.querySelector('[data-f="end"]')?.value);let human=slot.querySelector('.selection-seconds');if(!human){human=make('p');human.className='selection-seconds';times.before(human);}const value=rate?`Selección: ${a/rate}–${b/rate} s · final excluido`:'';if(human.textContent!==value)human.textContent=value;times.classList.add('technical-times');}
  const panel=slot.querySelector('.pausePanel'),audit=json(panel?.querySelector('[data-p="audit"]')),saved=audit.current_response;
  if(panel){
   // Finished intervals remain fully editable in disclosures; no review data is changed.
   const reviewed=saved?.temporal_review?.status==='confirmed',rows=panel.querySelector('[data-p="rows"]');
   if(reviewed&&rows)for(const row of rows.querySelectorAll(':scope > fieldset')){
    const d=make('details');d.dataset.polish='reviewed-interval';d.className='polish-details';
    const a=Number(row.querySelector('[data-key="start_sample"]').value),b=Number(row.querySelector('[data-key="end_sample_exclusive"]').value),rate=rateOf(slot),classification=row.querySelector('[data-key="classification"]');
    d.append(make('summary',`${row.querySelector('legend').textContent} · ${a/rate}–${b/rate} s · ${classification.selectedOptions[0].textContent}`));row.before(d);d.append(row);
   }
   if(rows)for(const d of rows.querySelectorAll(':scope > details[data-polish="reviewed-interval"]')){const row=d.querySelector('fieldset'),rate=rateOf(slot),a=Number(row.querySelector('[data-key="start_sample"]').value),b=Number(row.querySelector('[data-key="end_sample_exclusive"]').value),classification=row.querySelector('[data-key="classification"]'),text=`${row.querySelector('legend').textContent} · ${a/rate}–${b/rate} s · ${classification.selectedOptions[0].textContent}`;if(d.firstElementChild.textContent!==text)d.firstElementChild.textContent=text;}
   if(!reviewed&&rows)for(const d of rows.querySelectorAll(':scope > details[data-polish="reviewed-interval"]'))if(d.dataset.draft!=='true'){d.dataset.draft='true';d.open=true;}
   const label=panel.querySelector('[data-p="status"]')?.closest('label');if(label){const d=details(panel,'pause-status','Opciones del borrador / no evaluable');if(label.parentElement!==d)d.append(label);const confirmed=saved?.temporal_review?.status==='confirmed';if(label.hidden!==!!confirmed)label.hidden=!!confirmed;if(d.hidden!==!!confirmed)d.hidden=!!confirmed;let notice=panel.querySelector('.pause-result-state');if(!notice){notice=make('p');notice.className='pause-result-state';notice.setAttribute('role','status');panel.querySelector('[data-p="state"]').after(notice);}const text=pauseDisplay(audit);if(notice.textContent!==text)notice.textContent=text;}}
 }
 // Known display reasons only; never touch raw JSON, form values or source objects.
 for(const n of document.querySelectorAll('.metric small,.card small')){let text=displayUnit(n.textContent,n.parentElement.textContent);for(const [code,label]of Object.entries(reasonLabels))text=text.replaceAll(code,label);if(text!==n.textContent)n.textContent=text;}
 for(const [input]of mirrors)if(!input.isConnected)mirrors.delete(input);
 const tabs=document.querySelector('.tabs');if(tabs){const note=tabs.nextElementSibling;if(note?.tagName==='P'&&note.textContent.startsWith('Intento vinculado')){const d=details(tabs.parentElement,'attempt-context','Contexto del intento');tabs.after(d);d.append(note);}}
}
let pending=false;function update(){if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;paint();});}
new MutationObserver(update).observe(main,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','disabled','aria-current','data-status']});
for(const event of ['input','change','click'])main.addEventListener(event,update);
window.addEventListener('resize',update);paint();
