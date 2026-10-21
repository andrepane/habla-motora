import {getEvaluation,mutateEvaluation,invalidateAttempt,registerResult,artifact} from './motor-profile-store.js';
import {evaluationUrl,linkNavigation,rememberAttempt} from './evaluation-navigation.js';
import {savedTaskView} from './saved-task-view.js';

export function taskBridge(task){
  const params=new URLSearchParams(location.search),evaluationId=params.get('evaluation_id'),attemptId=params.get('attempt_id');
  const box=document.createElement('aside');box.className='notice profile-bridge';box.style.margin='16px 0';
  const back=document.createElement('a');back.href=evaluationId?evaluationUrl(evaluationId):'/profile';back.textContent='Perfil de habla motora';
  const message=document.createElement('p'),identity=document.createElement('p');message.setAttribute('role','status');box.append(back,identity,message);document.querySelector('main header')?.after(box);
  let context=null,protocol=null,queue=Promise.resolve(),editable=!evaluationId,pending=0,bypass=false,consulting=false;
  const revisions={},dirty=new Set();
  const controls=()=>[...document.querySelector('main').children].filter(n=>n!==box && !['NAV','HEADER','SCRIPT'].includes(n.tagName)&&n.id!=='savedTask');
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
    protocol=await response.json();context={evaluationId,attemptId,ordinal:a.ordinal};rememberAttempt(evaluationId,task,attemptId);linkNavigation(evaluationId,e);
    identity.textContent=`Evaluación ${e.case_ref||evaluationId.slice(0,8)} · ${task} · intento ${a.ordinal} · ${e.bindings[task]===attemptId?'Elegido para el Perfil':'No elegido para el Perfil'}.`;
    const source=e.sources[a.current[task]];
    if(source){
      consulting=true;lock();const view=await savedTaskView(e,a,protocol);box.after(view);
      message.textContent='Resultado guardado. Consultar no modifica sus estados. La revisión y los motivos originales se conservan.';
      const button=document.createElement('button');button.type='button';button.textContent='Editar / Reanalizar';box.append(button);
      button.onclick=async()=>{
        const warning=task==='phrase'
          ? 'Iniciar la edición recuperará el WAV y requerirá confirmar de nuevo la selección y la revisión. Pausas, candidatos y Prosodia necesitarán actualizarse. El resultado anterior seguirá conservado en el historial. ¿Continuar?'
          : 'Iniciar la edición recuperará el WAV para confirmar de nuevo la selección y reanalizar. El resultado anterior seguirá conservado en el historial. ¿Continuar?';
        if(!window.confirm(warning))return;
        try{
          const ref=source.assets.find(x=>x.role==='wav'),stored=await artifact(ref.sha256);
          const input=task==='phrase'?document.querySelector(`#attempt${a.ordinal} [data-f="file"]`):document.querySelector('#file');
          if(!input)throw Error('El editor todavía no está disponible.');
          editable=true;consulting=false;view.remove();button.remove();unlock();
          const transfer=new DataTransfer();transfer.items.add(new File([stored.bytes],ref.name,{type:'audio/wav'}));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
        }catch(e){message.textContent=e.message;}
      };
    }else{editable=true;unlock();message.textContent='Sin resultado guardado. Revisión pendiente; los cambios del editor son un borrador temporal hasta calcular y guardar.';}
  })().catch(e=>{message.textContent='Registro no disponible: '+e.message;});
  function enqueue(fn){pending++;queue=queue.then(()=>ready).then(()=>context?fn():undefined).catch(e=>{message.textContent='No se guardó en el Perfil: '+e.message;dirty.add('save_failed');}).finally(()=>pending--);return queue;}
  function permitted(ordinal){return editable&&(!evaluationId||context&&(ordinal===null||ordinal===context.ordinal));}
  function draftMessage(){message.textContent='Cambios sin confirmar: borrador temporal solo en esta pestaña. Al salir se perderán los cambios no guardados. Los resultados anteriores se conservan; las dependencias modificadas necesitan actualizarse.';}
  async function leave(event){
    const a=event.target.closest('a');if(!a||event.defaultPrevented||a.download||!a.href||!evaluationId)return;
    const target=new URL(a.href,location.href);if(target.origin!==location.origin||target.pathname===location.pathname&&target.search===location.search)return;
    // Modified clicks do not unload this editor. The new page still carries context.
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||a.target==='_blank')return;
    event.preventDefault();await ready;await queue;
    if(dirty.size&&!window.confirm('Hay cambios sin confirmar en un borrador temporal. Se perderán al salir. Los resultados guardados y el historial se conservan. ¿Salir?'))return;
    bypass=true;location.href=a.href;
  }
  document.addEventListener('click',leave);
  document.addEventListener('click',event=>{
    if(evaluationId&&editable&&event.target.closest('#record, .record')){dirty.add(task);draftMessage();}
  });
  window.addEventListener('beforeunload',event=>{if(evaluationId&&!bypass&&(dirty.size||pending)){event.preventDefault();event.returnValue='';}});
  window.addEventListener('pageshow',event=>{if(event.persisted&&evaluationId)location.reload();});
  return {
    ready,context:()=>context,flush:()=>queue,isConsulting:()=>consulting,
    acceptsOrdinal:ordinal=>!evaluationId||context?.ordinal===ordinal,
    invalidate(kinds,reason,ordinal=null){
      if(!permitted(ordinal))return Promise.resolve();
      for(const k of kinds){if(k===task || k==='pauses'&&!reason.startsWith('7A:'))dirty.add(k);const key=k+':'+ordinal;revisions[key]=(revisions[key]??0)+1;}
      if(evaluationId)draftMessage();
      return enqueue(()=>mutateEvaluation(evaluationId,e=>invalidateAttempt(e,attemptId,kinds,reason)));
    },
    save(kind,payload,file,capture=null,model=null,ordinal=null){
      if(!permitted(ordinal))return Promise.resolve();
      if(context)message.textContent='Guardando resultado '+kind+' en la evaluación local…';
      const copy=structuredClone(payload),key=kind+':'+ordinal,revision=revisions[key]??0;
      return enqueue(async()=>{
        if(revision!==(revisions[key]??0))return;
        if(!file)throw Error('Falta el WAV original.');
        await registerResult(evaluationId,attemptId,kind,copy,[{blob:file,role:'wav'},...(model?[{blob:model,role:'model'}]:[])],protocol,capture);
        dirty.delete(kind);dirty.delete('save_failed');
        const reviewPending=kind==='ddk'?!copy.reviewed_result?.confirmed:kind==='phrase'?!copy.review?.confirmed:kind==='pauses'?copy.temporal_review?.status!=='confirmed':false;
        message.textContent=`Resultado ${kind} guardado en esta evaluación · intento ${context.ordinal}.${reviewPending?' Revisión pendiente.':''}${dirty.size?' Quedan cambios sin confirmar en un borrador temporal.':''} El resumen utiliza solo el intento representativo elegido explícitamente.`;
      });
    },
    failed(kind,reason,ordinal=null){if(!permitted(ordinal))return Promise.resolve();return enqueue(()=>{
      dirty.add(kind);message.textContent='No se pudo completar el análisis. Los cambios del borrador no están guardados; los resultados anteriores permanecen conservados.';
      return mutateEvaluation(evaluationId,e=>{e.attempts[attemptId].errors[kind]=reason;invalidateAttempt(e,attemptId,[kind],reason);});
    });},
  };
}
