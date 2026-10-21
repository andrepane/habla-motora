import {stateLabels} from './evaluation-flow.js';
import {project,pointer} from './motor-profile.js';
import {loadSources,artifact} from './motor-profile-store.js';
import {metricText} from './audio.js';
const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
// Read-only projection of immutable sources. Never invokes a motor or registers a result.
export async function savedTaskView(e,a,protocol){
  const host=node('section');host.id='savedTask';host.style.overflowWrap='anywhere';host.dataset.mode='consult';host.append(node('h2','Consultar resultado guardado'));
  const copy=structuredClone(e);copy.bindings[a.task]=a.attempt_id;
  const sources=await loadSources(e),profile=project(copy,sources,protocol);
  host.append(node('p',`Intento ${a.ordinal} · ${e.bindings[a.task]===a.attempt_id?'Elegido para el Perfil':'No elegido para el Perfil'}. Consulta sin modificar resultados.`));
  for(const d of Object.values(profile.domains).filter(d=>d.attempt_id===a.attempt_id)){
    host.append(node('h3',d.name),node('p',`Estado conservado: ${stateLabels[d.status]??d.status}`));
    if(['stale','failed'].includes(d.status))host.append(node('p','Valores del resultado original conservado; no se utilizan como resultados vigentes del Perfil.'));
    const list=node('dl');
    for(let m of Object.values(d.metrics)){
      if(['stale','failed'].includes(d.status)&&sources[m.source_ref]&&!sources[m.source_ref].integrity_error){
        const raw=pointer(sources[m.source_ref].payload,m.source_pointer);
        if(raw&&Object.hasOwn(raw,'value'))m={...m,...raw};
      }
      list.append(node('dt',m.label),node('dd',`${metricText(m)}${m.value!==null?' '+m.unit:' · '+m.reason}`));
    }
    host.append(list);
    for(const w of d.warnings)host.append(node('p',w.message||w.code));
  }
  const source=sources[a.current[a.task]];
  if(!source||source.integrity_error)throw Error('No se pudo verificar el resultado original. No se habilita su edición.');
  const wav=source.assets.find(x=>x.role==='wav'),stored=await artifact(wav.sha256),audio=node('audio');audio.controls=true;
  const url=URL.createObjectURL(new Blob([stored.bytes],{type:'audio/wav'}));audio.src=url;host.append(node('p','WAV original conservado'),audio);
  window.addEventListener('pagehide',()=>URL.revokeObjectURL(url),{once:true});
  const audit=node('details');audit.append(node('summary','Selección, revisión y procedencia conservadas'));
  for(const kind of Object.keys(a.current)){
    const s=sources[a.current[kind]];if(!s||s.integrity_error)continue;
    // Exclude heavy frames/pulses; original remains recoverable through the Profile.
    audit.append(node('h3',kind),node('pre',JSON.stringify({source_ref:s.result_id,selection:s.selection,
      context:s.context,provenance:s.provenance,review:s.payload.review??s.payload.reviewed_result??s.payload.temporal_review,
      dependencies:s.payload.dependencies,invalid_reason:a.invalid[kind]??null},null,2)));
  }
  host.append(audit);return host;
}
