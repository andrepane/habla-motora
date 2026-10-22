import {checkCompatibility} from './motor-profile.js';
import {attemptSummary,taskNames} from './evaluation-flow.js';
import {getEvaluation,mutateEvaluation,invalidateAttempt,registerResult,artifact,bind,loadSources} from './motor-profile-store.js';
import {evaluationUrl,linkNavigation,rememberAttempt,commonNavigation,destination,activeAttempts} from './evaluation-navigation.js';
import {exactAudioBuffer} from './recovered-audio.js';
import {savedTaskView} from './saved-task-view.js';

export function taskBridge(task){
  commonNavigation();
  const params=new URLSearchParams(location.search),evaluationId=params.get('evaluation_id'),attemptId=params.get('attempt_id');
  const box=document.createElement('aside');box.className='notice profile-bridge';box.style.margin='16px 0';
  const back=document.createElement('a');back.href=evaluationId?evaluationUrl(evaluationId):'/profile';back.textContent='Perfil de habla motora';
  const hub=document.createElement('a');hub.textContent='Volver a evaluación';hub.href='/evaluation'+(evaluationId?'?evaluation_id='+encodeURIComponent(evaluationId):'');box.append(hub);
  const message=document.createElement('p'),identity=document.createElement('p');message.setAttribute('role','status');box.append(back,identity,message);document.querySelector('main header')?.after(box);
  const actions=document.createElement('section');actions.id='clinicalActions';actions.className='flow-actions';actions.hidden=!evaluationId;box.after(actions);
  let context=null,protocol=null,queue=Promise.resolve(),editable=!evaluationId,pending=0,bypass=false,consulting=false;
  const revisions={},dirty=new Set();
  let controllerState='preparing',controllerError='';
  const preparedActions=[];
  const preparation=document.createElement('p'),retry=document.createElement('button');
  preparation.dataset.controllerState='preparing';preparation.setAttribute('role','status');
  retry.type='button';retry.textContent='Reintentar preparación';retry.hidden=true;
  retry.onclick=()=>location.reload();box.append(preparation,retry);preparation.hidden=true;
  function paintPreparation(){
    for(const {button,label} of preparedActions){button.disabled=controllerState!=='ready';button.textContent=controllerState==='preparing'?'Preparando…':label;}
    preparation.dataset.controllerState=controllerState;
    preparation.hidden=controllerState==='ready'||!preparedActions.length&&controllerState!=='failed';
    preparation.textContent=controllerState==='failed'?'No se pudo preparar la tarea. Puedes seguir consultando el resultado guardado o reintentar. '+controllerError:'Preparando…';
    retry.hidden=controllerState!=='failed';
  }
  function preparedButton(label){const button=document.createElement('button');button.type='button';preparedActions.push({button,label});paintPreparation();return button;}

  const controls=()=>[...document.querySelector('main').children].filter(n=>n!==box && !['NAV','HEADER','SCRIPT'].includes(n.tagName)&&!['savedTask','clinicalActions'].includes(n.id));
  // Block task interactions while identity/source lookup is in progress.
  let originalHidden=new Map();
  function lock(){for(const n of controls()){if(!originalHidden.has(n))originalHidden.set(n,n.hidden);n.hidden=true;}}
  function unlock(){for(const [n,hidden]of originalHidden)n.hidden=hidden;originalHidden.clear();}
  if(evaluationId){lock();message.textContent='Comprobando evaluación e intento…';linkNavigation(evaluationId);}
  const observer=new MutationObserver(()=>{if(evaluationId&&!editable)lock();});observer.observe(document.querySelector('main'),{childList:true});
  const ready=(async()=>{
    if(!evaluationId){message.textContent='Análisis independiente, sin evaluación vinculada.';return;}
    const e=await getEvaluation(evaluationId);if(!e)throw Error('Evaluación no encontrada en este navegador.');linkNavigation(evaluationId,e);
    const a=e.attempts[attemptId];
    if(!a){back.href=evaluationUrl(evaluationId,task);message.textContent='Elige o crea explícitamente un intento desde la evaluación.';return;}
    if(a.evaluation_id!==evaluationId||a.task!==task)throw Error('Vinculación de evaluación/intento inválida.');
    const response=await fetch('/motor-profile-protocol',{cache:'no-store'});if(!response.ok)throw Error('No se pudo verificar el protocolo del perfil.');
    protocol=await response.json();context={evaluationId,attemptId,ordinal:a.ordinal};if(task==='phrase')for(const b of document.querySelectorAll('.tabs button'))b.disabled=true;rememberAttempt(evaluationId,task,attemptId);linkNavigation(evaluationId,e);
    identity.textContent=`Evaluación activa${e.case_ref?' · '+e.case_ref:''} · ${taskNames[task]} · intento ${a.ordinal} · ${e.bindings[task]===attemptId?'Elegido para el Perfil':'No elegido para el Perfil'}.`;
    await updateActions();
    const source=e.sources[a.current[task]];
    if(source){
      consulting=true;lock();const view=await savedTaskView(e,a,protocol);box.after(view);
      message.textContent='Resultado guardado. Consultar no modifica sus estados. La revisión y los motivos originales se conservan.';
      if(task==='phrase'){
        const loaded=await loadSources(e),parent=loaded[a.current.phrase]?.payload;
        if(parent?.context.selection_confirmed&&!a.invalid.phrase&&!a.errors.phrase&&!loaded[a.current.phrase]?.integrity_error&&!checkCompatibility('phrase',parent,protocol)){
          const resume=preparedButton('Continuar contenido, pausas o Prosodia');resume.dataset.resumePhrase='true';box.append(resume);
          resume.onclick=async()=>{try{
            const ref=source.assets.find(x=>x.role==='wav'),wav=await artifact(ref.sha256),modelRef=source.assets.find(x=>x.role==='model'),model=modelRef?{...(await artifact(modelRef.sha256)),sha256:modelRef.sha256}:null;
            editable=true;consulting=false;unlock();view.hidden=true;
            const payloads=Object.fromEntries(['pauses','prosody'].filter(k=>a.current[k]&&!a.invalid[k]&&!a.errors[k]&&!loaded[a.current[k]]?.integrity_error&&!checkCompatibility(k,loaded[a.current[k]].payload,protocol)).map(k=>[k,loaded[a.current[k]].payload]));
            await new Promise((resolve,reject)=>window.dispatchEvent(new CustomEvent('motor-phrase-resume',{detail:{source:parent,sources:payloads,bytes:exactAudioBuffer(wav.bytes),file:new File([wav.bytes],ref.name,{type:'audio/wav'}),model,resolve,reject}})));
            resume.hidden=true;message.textContent='Continuación de revisiones. Selección y contenido guardados permanecen bloqueados; editar la selección requiere Editar / Reanalizar.';
          }catch(x){message.textContent=x.message;}};
        }
      }

      if(task==='ddk'){
        const loaded=await loadSources(e),original=loaded[a.current.ddk]?.payload;
        if(original&&!original.reviewed_result?.confirmed&&!a.invalid.ddk&&!a.errors.ddk&&!checkCompatibility('ddk',original,protocol)){
          const resume=preparedButton('Continuar revisión');resume.dataset.resumeDdk='true';box.append(resume);
          resume.onclick=async()=>{try{
            const ref=source.assets.find(x=>x.role==='wav'),wav=await artifact(ref.sha256);
            editable=true;consulting=false;unlock();
            await new Promise((resolve,reject)=>window.dispatchEvent(new CustomEvent('motor-ddk-resume',{detail:{source:original,bytes:exactAudioBuffer(wav.bytes),file:new File([wav.bytes],ref.name,{type:'audio/wav'}),capture:source.capture,resolve,reject}})));
            editable=true;consulting=false;unlock();view.hidden=true;resume.hidden=true;
            message.textContent='Revisión pendiente recuperada. No se ha vuelto a ejecutar la detección. Los cambios nuevos son un borrador temporal hasta guardar el cálculo de revisión.';
          }catch(x){editable=false;consulting=true;lock();view.hidden=false;message.textContent='No se pudo continuar la revisión: '+x.message;}};
        }
      }
      const button=preparedButton('Editar / Reanalizar');box.append(button);
      button.onclick=async()=>{
        const warning=task==='phrase'
          ? 'Iniciar la edición recuperará el WAV y requerirá confirmar de nuevo la selección y la revisión. Pausas, candidatos y Prosodia necesitarán actualizarse. El resultado anterior seguirá conservado en el historial. ¿Continuar?'
          : 'Iniciar la edición recuperará el WAV para confirmar de nuevo la selección y reanalizar. El resultado anterior seguirá conservado en el historial. ¿Continuar?';
        if(!window.confirm(warning))return;
        window.dispatchEvent(new Event('motor-edit-start'));
        try{
          const ref=source.assets.find(x=>x.role==='wav'),stored=await artifact(ref.sha256);
          const input=task==='phrase'?document.querySelector(`#attempt${a.ordinal} [data-f="file"]`):document.querySelector('#file');
          if(!input)throw Error('El editor todavía no está disponible.');
          editable=true;consulting=false;view.remove();button.remove();unlock();
          const transfer=new DataTransfer();transfer.items.add(new File([stored.bytes],ref.name,{type:'audio/wav'}));input.files=transfer.files;
          if(task==='phrase'){
            const slot=document.querySelector(`#attempt${a.ordinal}`),modality=slot.querySelector('[data-f="modality"]');
            modality.value=source.context.modality;modality.dispatchEvent(new Event('input',{bubbles:true}));
            await new Promise(resolve=>input.dispatchEvent(new CustomEvent('change',{bubbles:true,detail:{loaded:resolve}})));
            const limit=slot.querySelector('[data-f="limit"]');
            if(source.context.recording_limit_reached){limit.checked=true;limit.dispatchEvent(new Event('input',{bubbles:true}));}
            const model=source.assets.find(x=>x.role==='model');
            if(model){
              const original=await artifact(model.sha256),modelInput=slot.querySelector('[data-f="model"]'),files=new DataTransfer();
              files.items.add(new File([original.bytes],model.name,{type:'audio/wav'}));modelInput.files=files.files;modelInput.dispatchEvent(new Event('change',{bubbles:true}));
              message.textContent='Modalidad y modelo originales recuperados. Vuelve a escuchar el modelo completo y confirma selección y revisión. Los resultados anteriores se conservan; las dependencias necesitan actualizarse.';
            }
          }else input.dispatchEvent(new Event('change',{bubbles:true}));
        }catch(e){message.textContent=e.message;}
      };
    }else{editable=true;unlock();message.textContent='Sin resultado guardado. Revisión pendiente; los cambios del editor son un borrador temporal hasta calcular y guardar.';}
  })().catch(e=>{message.textContent='Registro no disponible: '+e.message;});
  async function updateActions(){
    if(!context)return;
    const e=await getEvaluation(evaluationId),a=e.attempts[attemptId],sources=await loadSources(e),summary=attemptSummary(e,a,sources,protocol);
    actions.replaceChildren();actions.hidden=!summary.eligible;
    const footer=document.querySelector('main > footer');if(footer)footer.before(actions);else document.querySelector('main').append(actions);
    const use=document.createElement('button');use.dataset.useProfile='true';use.textContent=e.bindings[task]===attemptId?'Intento elegido para el Perfil':'Usar este intento en el Perfil';
    use.disabled=!summary.eligible||e.bindings[task]===attemptId;
    use.onclick=async()=>{try{await queue;const current=await getEvaluation(evaluationId),s=attemptSummary(current,current.attempts[attemptId],await loadSources(current),protocol);if(!s.eligible)throw Error('Completa la tarea y su revisión antes de elegir este intento.');await mutateEvaluation(evaluationId,e=>bind(e,task,attemptId));await updateActions();identity.textContent=`Evaluación activa${e.case_ref?' · '+e.case_ref:''} · ${taskNames[task]} · intento ${a.ordinal} · Elegido para el Perfil`;message.textContent='Intento elegido explícitamente para el Perfil.';}catch(x){message.textContent=x.message;}};
    actions.append(use);
    const nextTask=task==='vowel'?'ddk':task==='ddk'?'phrase':null,link=document.createElement('a');
    link.textContent=nextTask?'Continuar con '+taskNames[nextTask]:'Ver Perfil';link.href=destination(e,nextTask,activeAttempts(evaluationId));actions.append(link);
  }
  function enqueue(fn){pending++;queue=queue.then(()=>ready).then(()=>context?fn():undefined).catch(e=>{message.textContent='No se guardó en el Perfil: '+e.message;dirty.add('save_failed');}).finally(()=>pending--);return queue;}
  function permitted(ordinal){return editable&&(!evaluationId||context&&(ordinal===null||ordinal===context.ordinal));}
  function draftMessage(){message.textContent='Cambios sin confirmar: borrador temporal solo en esta pestaña. Al salir se perderán los cambios no guardados. Los resultados anteriores se conservan; las dependencias modificadas necesitan actualizarse.';}
  async function leave(event){
    const a=event.target.closest('a');if(!a||event.defaultPrevented||a.download||!a.href||!evaluationId&&!independentContent())return;
    const target=new URL(a.href,location.href);if(target.origin!==location.origin||target.pathname===location.pathname&&target.search===location.search)return;
    // Modified clicks do not unload this editor. The new page still carries context.
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||a.target==='_blank')return;
    event.preventDefault();await ready;await queue;
    if((evaluationId?dirty.size:independentContent())&&!window.confirm(evaluationId?'Hay cambios sin confirmar en un borrador temporal. Se perderán al salir. Los resultados guardados y el historial se conservan. ¿Salir?':'Hay audio o cambios temporales en esta tarea independiente. Se perderán al salir. No se guardan automáticamente. ¿Salir?'))return;
    bypass=true;location.href=a.href;
  }
  document.addEventListener('click',leave);
  document.addEventListener('click',event=>{
    if(evaluationId&&editable&&event.target.closest('#record, .record')){dirty.add(task);draftMessage();}
  });
  function independentContent(){return [...document.querySelectorAll('main input[type="file"]')].some(n=>n.files?.length)||!!document.querySelector('main audio[src^="blob:"],#stop:not(:disabled),.stop:not(:disabled)');}
  window.addEventListener('beforeunload',event=>{if(!bypass&&(evaluationId?(dirty.size||pending):independentContent())){event.preventDefault();event.returnValue='';}});
  window.addEventListener('pageshow',event=>{if(event.persisted&&evaluationId)location.reload();});
  return {
    controllerReady(){controllerState='ready';paintPreparation();},controllerFailed(error){controllerState='failed';controllerError=error.message||String(error);paintPreparation();},
    ready,context:()=>context,flush:()=>queue,isConsulting:()=>consulting,
    acceptsOrdinal:ordinal=>!evaluationId||context?.ordinal===ordinal,
    invalidate(kinds,reason,ordinal=null){
      if(!permitted(ordinal))return Promise.resolve();
      for(const k of kinds){if(k===task || k==='pauses'&&!reason.startsWith('7A:'))dirty.add(k);const key=k+':'+ordinal;revisions[key]=(revisions[key]??0)+1;}
      if(evaluationId){delete message.dataset.savedKind;draftMessage();}
      return enqueue(()=>mutateEvaluation(evaluationId,e=>invalidateAttempt(e,attemptId,kinds,reason)));
    },
    save(kind,payload,file,capture=null,model=null,ordinal=null){
      if(!permitted(ordinal))return Promise.resolve();
      if(context){delete message.dataset.savedKind;message.textContent='Guardando resultado en la evaluación local…';}
      const copy=structuredClone(payload),key=kind+':'+ordinal,revision=revisions[key]??0;
      return enqueue(async()=>{
        if(revision!==(revisions[key]??0))return;
        if(!file)throw Error('Falta el WAV original.');
        await registerResult(evaluationId,attemptId,kind,copy,[{blob:file,role:'wav'},...(model?[{blob:model,role:'model'}]:[])],protocol,capture);
        dirty.delete(kind);dirty.delete('save_failed');await updateActions();window.dispatchEvent(new Event('motor-result-saved'));
        const reviewPending=kind==='ddk'?!copy.reviewed_result?.confirmed:kind==='phrase'?!copy.review?.confirmed:kind==='pauses'?copy.temporal_review?.status!=='confirmed':false;
        message.dataset.savedKind=kind;message.textContent=`Resultado guardado · ${{vowel:'Vocal',ddk:'DDK',phrase:'Habla conectada',pauses:'Pausas',candidates:'Candidatos experimentales',prosody:'Prosodia'}[kind]} · evaluación activa · intento ${context.ordinal}.${reviewPending?' Revisión pendiente.':''}${dirty.size?' Quedan cambios sin confirmar en un borrador temporal.':''} El resumen utiliza solo el intento representativo elegido explícitamente.`;
      });
    },
    failed(kind,reason,ordinal=null){if(!permitted(ordinal))return Promise.resolve();return enqueue(()=>{
      dirty.add(kind);message.textContent='No se pudo completar el análisis. Los cambios del borrador no están guardados; los resultados anteriores permanecen conservados.';
      return mutateEvaluation(evaluationId,e=>{e.attempts[attemptId].errors[kind]=reason;invalidateAttempt(e,attemptId,[kind],reason);});
    });},
  };
}
