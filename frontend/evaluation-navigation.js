// Navigation metadata only. Does not select a representative or mutate an evaluation.
export const taskPaths = {vowel:'/',ddk:'/ddk',phrase:'/phrase'};
export function evaluationUrl(id, task=null, attempt=null) {
  const params=new URLSearchParams({evaluation_id:id});
  if(attempt)params.set('attempt_id',attempt);
  else if(task)params.set('manage_task',task);
  return (attempt?taskPaths[task]:'/profile')+'?'+params;
}
export function destination(e,task,active={}) {
  if(!task)return evaluationUrl(e.evaluation_id);
  const id=[active[task],e.bindings[task]].find(id=>e.attempts[id]?.task===task&&e.attempts[id]?.evaluation_id===e.evaluation_id),a=e.attempts[id];
  return a?.task===task && a.evaluation_id===e.evaluation_id
    ? evaluationUrl(e.evaluation_id,task,id):evaluationUrl(e.evaluation_id,task);
}
const key=id=>'motor-active-attempts:'+id;
export function activeAttempts(id){try{return JSON.parse(sessionStorage.getItem(key(id))||'{}');}catch{return {};}}
export function rememberAttempt(id,task,attempt){try{sessionStorage.setItem(key(id),JSON.stringify({...activeAttempts(id),[task]:attempt}));}catch{/* URL remains authoritative. */}}
export function linkNavigation(id,e=null){
  for(const a of document.querySelectorAll('nav a')){
    if(!a.dataset.evaluationTask){
      const path=new URL(a.href,location.href).pathname,task=Object.keys(taskPaths).find(k=>taskPaths[k]===path);
      if(!task&&path!=='/profile')continue;
      a.dataset.evaluationTask=task||'profile';
    }
    const task=a.dataset.evaluationTask==='profile'?null:a.dataset.evaluationTask;
    a.href=!id?(task?taskPaths[task]:'/profile'):e?destination(e,task,activeAttempts(id)):evaluationUrl(id,task);
  }
}
