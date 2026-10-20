import {getEvaluation,mutateEvaluation,invalidateAttempt,registerResult,artifact} from './motor-profile-store.js';

export function taskBridge(task){
  const params=new URLSearchParams(location.search),evaluationId=params.get('evaluation_id'),attemptId=params.get('attempt_id');
  const box=document.createElement('aside');box.className='notice profile-bridge';box.style.margin='16px 0';
  const back=document.createElement('a');back.href='/profile'+(evaluationId?'?evaluation_id='+encodeURIComponent(evaluationId):'');back.textContent='Perfil de habla motora';
  const message=document.createElement('p');box.append(back,message);document.querySelector('main header')?.after(box);
  let context=null,protocol=null,queue=Promise.resolve();const revisions={};
  const ready=(async()=>{
    if(!evaluationId||!attemptId){message.textContent='Sin vinculación a evaluación. Para registrar tareas, abre un intento desde el Perfil.';return;}
    const e=await getEvaluation(evaluationId),a=e?.attempts[attemptId];
    if(!a || a.evaluation_id!==evaluationId || a.task!==task)throw Error('Vinculación de evaluación/intento inválida.');
    const response=await fetch('/motor-profile-protocol',{cache:'no-store'});if(!response.ok)throw Error('No se pudo verificar el protocolo del perfil.');
    protocol=await response.json();context={evaluationId,attemptId,ordinal:a.ordinal};
    message.textContent=`Evaluación ${e.case_ref||evaluationId.slice(0,8)} · ${task} · intento ${a.ordinal}. Registro local; el intento representativo se elige en el Perfil.`;
    const source=e.sources[a.current[task]];
    if(source){
      const saved=document.createElement('p');saved.textContent='Existe un resultado registrado. Abrir la tarea no lo modifica. Recuperar y editar el original lo dejará desactualizado.';box.append(saved);
      const button=document.createElement('button');button.type='button';button.textContent='Recuperar WAV para editar/reanalizar';box.append(button);
      button.onclick=async()=>{try{
        const ref=source.assets.find(x=>x.role==='wav'),stored=await artifact(ref.sha256);
        const input=task==='phrase'?document.querySelector(`#attempt${a.ordinal} [data-f="file"]`):document.querySelector('#file');
        const transfer=new DataTransfer();transfer.items.add(new File([stored.bytes],ref.name,{type:'audio/wav'}));input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
        message.textContent='WAV original recuperado. Revisa límites y confirma de nuevo la tarea; las revisiones anteriores permanecen en la auditoría del Perfil.';
      }catch(e){message.textContent=e.message;}};
    }
  })().catch(e=>{message.textContent='Registro no disponible: '+e.message;});
  function enqueue(fn){queue=queue.then(()=>ready).then(()=>context?fn():undefined).catch(e=>{message.textContent='No se guardó en el Perfil: '+e.message;});return queue;}
  back.onclick=async event=>{if(!context)return;event.preventDefault();await queue;location.href=back.href;};
  return {
    ready,context:()=>context,flush:()=>queue,
    invalidate(kinds,reason,ordinal=null){
      if(context && (ordinal===null||ordinal===context.ordinal))message.textContent='Resultado anterior desactualizado. Pendiente de volver a completar o confirmar la tarea.';
      for(const k of kinds){const key=k+':'+ordinal;revisions[key]=(revisions[key]??0)+1;}
      return enqueue(()=>{
        if(ordinal!==null&&ordinal!==context.ordinal)return;
        return mutateEvaluation(evaluationId,e=>invalidateAttempt(e,attemptId,kinds,reason));
      });
    },
    save(kind,payload,file,capture=null,model=null,ordinal=null){
      if(context && (ordinal===null||ordinal===context.ordinal))message.textContent='Guardando resultado '+kind+' en la evaluación local…';
      const copy=structuredClone(payload),key=kind+':'+ordinal,revision=revisions[key]??0;
      return enqueue(async()=>{
        if(ordinal!==null&&ordinal!==context.ordinal || revision!==(revisions[key]??0))return;
        if(!file)throw Error('Falta el WAV original.');
        await registerResult(evaluationId,attemptId,kind,copy,[{blob:file,role:'wav'},...(model?[{blob:model,role:'model'}]:[])],protocol,capture);
        message.textContent=`Resultado ${kind} guardado en esta evaluación · intento ${context.ordinal}. El resumen utiliza solo el intento representativo elegido explícitamente.`;
      });
    },
    failed(kind,reason,ordinal=null){return enqueue(()=>{
      if(ordinal!==null&&ordinal!==context.ordinal)return;
      return mutateEvaluation(evaluationId,e=>{e.attempts[attemptId].errors[kind]=reason;invalidateAttempt(e,attemptId,[kind],reason);});
    });},
  };
}
