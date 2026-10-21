import {chromium} from './browser-runtime.mjs';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const base=process.env.BASE_URL||'http://127.0.0.1:8000',fixture=JSON.parse(fs.readFileSync(process.env.PROFILE_FIXTURES||'/tmp/profile-fixtures.json'));
const browser=await chromium.launch({headless:true});let checks=0;
function check(v,label){assert.ok(v,`${++checks}: ${label}`);}
try{
 const context=await browser.newContext(),p=await context.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(base+'/profile');
 const seed=await p.evaluate(async f=>{
  const s=await import('/static/motor-profile-store.js'),e=s.createEvaluation('Continuidad sintética');await s.saveEvaluation(e);
  let ids={};for(const task of ['vowel','ddk','phrase']){await s.mutateEvaluation(e.evaluation_id,e=>{const id=s.addAttempt(e,task);s.bind(e,task,id);ids[task]=id;});}
  const protocol=await(await fetch('/motor-profile-protocol')).json();
  for(const kind of ['vowel','ddk','phrase','pauses','candidates','prosody']){
   const task=['pauses','candidates','prosody'].includes(kind)?'phrase':kind;
   const bytes=Uint8Array.from(atob(f.wavs[task]),c=>c.charCodeAt(0));
   await s.registerResult(e.evaluation_id,ids[task],kind,f.payloads[kind],[{blob:new File([bytes],task+'.wav'),role:'wav'}],protocol);
  }
  let second;await s.mutateEvaluation(e.evaluation_id,e=>second=s.addAttempt(e,'phrase'));
  return {id:e.evaluation_id,ids,second};
 },fixture);
 const url=(task,id=seed.ids[task])=>base+({vowel:'/',ddk:'/ddk',phrase:'/phrase'}[task])+`?evaluation_id=${seed.id}&attempt_id=${id}`;
 const record=()=>p.evaluate(async id=>(await import('/static/motor-profile-store.js')).getEvaluation(id),seed.id);
 const consult=()=>p.locator('#savedTask').waitFor();
 const original=JSON.stringify(await record());let writes=0;p.on('request',r=>{if(r.method()==='POST')writes++;});
 await p.goto(url('vowel'));await consult();check((await p.locator('#savedTask').innerText()).includes('F0 media'),'stored metrics visible');check(await p.locator('#savedTask audio').count()===1,'original audio available');
 await p.locator('nav a[data-evaluation-task="ddk"]').click();await consult();check(new URL(p.url()).searchParams.get('evaluation_id')===seed.id,'Vocal → DDK preserves evaluation');check(new URL(p.url()).searchParams.get('attempt_id')===seed.ids.ddk,'DDK representative resolved');
 await p.locator('nav a[data-evaluation-task="phrase"]').click();await consult();check(new URL(p.url()).searchParams.get('attempt_id')===seed.ids.phrase,'DDK → phrase preserves attempt/evaluation');
 check(await p.locator('#tab1').isDisabled()&&await p.locator('#tab2').isDisabled(),'linked phrase tabs locked');
 await p.locator('#tab2').evaluate(x=>x.click());check(await p.locator('#attempt2').evaluate(x=>x.hidden),'programmatic other tab cannot switch');
 await p.locator('.profile-bridge a').click();await p.locator('[data-domain="prosody"]').waitFor();check(new URL(p.url()).searchParams.get('evaluation_id')===seed.id,'phrase → profile preserves evaluation');
 await p.locator('[data-domain="prosody"] > a').click();await consult();check(new URL(p.url()).searchParams.get('attempt_id')===seed.ids.phrase,'Profile Ver tarea targets exact phrase attempt');
 await p.reload();await consult();await p.goBack();await p.goForward();await consult();check(new URL(p.url()).searchParams.get('attempt_id')===seed.ids.phrase,'reload and browser history preserve context');
 check(JSON.stringify(await record())===original,'consultation changes no states, sources, history or hashes');check(writes===0,'consultation invokes no analysis or registration POST');
 const confirmation=p.waitForEvent('dialog');const consultClick=p.locator('.profile-bridge button').click();await(await confirmation).dismiss();await consultClick;check(await p.locator('#savedTask').isVisible(),'cancel editing retains consultation');check(JSON.stringify(await record())===original,'cancel editing makes no changes');
 const editDialog=p.waitForEvent('dialog');const editClick=p.locator('.profile-bridge button').click();await(await editDialog).accept();await editClick;
 await p.locator('#attempt1 .state').filter({hasText:'WAV conservado'}).waitFor();await p.waitForFunction(async id=>{const e=await(await import('/static/motor-profile-store.js')).getEvaluation(id);return Object.values(e.attempts).some(a=>a.invalid.prosody);},seed.id);
 const changed=await record(),a=changed.attempts[seed.ids.phrase];check(!!a.invalid.phrase&&!!a.invalid.pauses&&!!a.invalid.prosody,'explicit editing invalidates existing dependencies');check(Object.keys(changed.sources).length===Object.keys(JSON.parse(original).sources).length,'old immutable sources retained');
 check((await p.locator('.profile-bridge').innerText()).includes('borrador temporal'),'temporary draft warning visible');
 const cancelLeave=p.waitForEvent('dialog');const leaveClick=p.locator('.profile-bridge a').click();await(await cancelLeave).dismiss();await leaveClick;check(p.url().includes('attempt_id='),'cancel unsafe exit retains editor');
 const leaveDialog=p.waitForEvent('dialog');const leave=p.locator('.profile-bridge a').click();await(await leaveDialog).accept();await leave;await p.waitForFunction(()=>document.querySelector('#audit')?.textContent.includes('motor_speech_profile_v1'));
 await p.goto(url('phrase',seed.second));await p.locator('.profile-bridge p').filter({hasText:'Sin resultado guardado'}).waitFor();check(await p.locator('#attempt2').isVisible()&&!await p.locator('#attempt1').isVisible(),'second linked attempt displays only second slot');
 const card=p.locator('#attempt2');await card.locator('[data-f="file"]').setInputFiles({name:'phrase.wav',mimeType:'audio/wav',buffer:Buffer.from(fixture.wavs.phrase,'base64')});await card.locator('.state').filter({hasText:'WAV conservado'}).waitFor();await card.locator('[data-f="selectionConfirmed"]').check();await card.locator('.analyze').click();await p.locator('.profile-bridge p').filter({hasText:'Resultado phrase guardado'}).waitFor();
 const now=await record(),result=now.sources[now.attempts[seed.second].current.phrase];check(result.attempt_id===seed.second&&result.context.attempt===2,'attempt 2 registered only under its own ID');check(now.attempts[seed.ids.phrase].current.phrase===a.current.phrase,'attempt 1 current result untouched');
 // Prosody still uses the exact current second-attempt 7A context.
 await card.locator('[data-pr="run"]').click();await p.locator('.profile-bridge p').filter({hasText:'Resultado prosody guardado'}).waitFor();const final=await record(),prosody=final.sources[final.attempts[seed.second].current.prosody];check(prosody.context.attempt===2&&prosody.parent_source_ref===result.result_id,'Prosody binds to same 7A attempt');
 // Content review and manual pauses may change without changing the F0 selection.
 for(const [field,value]of [['production','present'],['match','exact_once']])await card.locator(`[data-f="${field}"]`).selectOption(value);
 for(const [field,value]of [['words','14'],['syllables','25']])await card.locator(`[data-f="${field}"]`).fill(value);
 for(const field of ['wordsConfirmed','syllablesConfirmed','reviewConfirmed'])await card.locator(`[data-f="${field}"]`).check();
 await card.locator('.submitReview').click();await p.locator('.profile-bridge p').filter({hasText:'Resultado phrase guardado'}).waitFor();
 await card.locator('[data-p="confirmed"]').check();await card.locator('[data-p="calculate"]').click();await p.locator('.profile-bridge p').filter({hasText:'Resultado pauses guardado'}).waitFor();
 const withPauses=await record(),secondState=withPauses.attempts[seed.second],secondPauses=withPauses.sources[secondState.current.pauses];
 check(secondPauses.attempt_id===seed.second&&secondPauses.context.attempt===2&&secondPauses.parent_source_ref===secondState.current.phrase,'new manual pauses register under second 7A attempt');
 check(secondState.current.prosody===prosody.result_id&&!secondState.invalid.prosody,'content/pause review does not alter existing F0');
 // Browser-native reload warning also protects temporary drafts.
 await card.locator('[data-f="notes"]').fill('Borrador temporal');
 const reloadDialog=p.waitForEvent('dialog');const reload=p.reload({timeout:3000}).catch(()=>null);await(await reloadDialog).dismiss();await reload;
 check(await card.locator('[data-f="notes"]').inputValue()==='Borrador temporal','cancel reload preserves unconfirmed draft');
 const pauseSource=final.sources[final.attempts[seed.ids.phrase].current.pauses];check(pauseSource.attempt_id===seed.ids.phrase&&pauseSource.parent_source_ref===a.current.phrase,'existing pauses retain own 7A parent');
 p.on('dialog',d=>d.accept());await p.goto(base+'/phrase');await p.locator('#tab2').click();check(await p.locator('#attempt2').isVisible(),'independent two-attempt mode remains available');
 await p.goto(base+'/');check((await p.locator('.profile-bridge').innerText()).includes('Análisis independiente'),'independent Vocal remains explicit');
 await p.setViewportSize({width:390,height:844});await p.goto(url('ddk'));await consult();check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'read-only consultation fits mobile');
 // An unstarted task redirects to explicit management, not to independent analysis.
 await p.goto(base+'/profile');await p.locator('#new').click();await p.locator('#identity').waitFor();const emptyId=new URL(p.url()).searchParams.get('evaluation_id');await p.locator('nav a[data-evaluation-task="ddk"]').click();check(p.url().includes('manage_task=ddk')&&p.url().includes(emptyId),'missing attempt opens same evaluation management');check(await p.locator('#identity > details').evaluate(x=>x.open),'explicit attempt creation exposed');
 // An auditory attempt must never silently reopen as direct reading.
 const auditory=await p.evaluate(async f=>{
   const s=await import('/static/motor-profile-store.js'),e=s.createEvaluation('Modelo sintético');await s.saveEvaluation(e);let aid;
   await s.mutateEvaluation(e.evaluation_id,e=>{aid=s.addAttempt(e,'phrase');s.bind(e,'phrase',aid);});
   const wav=new File([Uint8Array.from(atob(f.wavs.phrase),c=>c.charCodeAt(0))],'original.wav',{type:'audio/wav'});
   const hash=await s.sha(await wav.arrayBuffer()),ctx={...f.payloads.phrase.context,modality:'auditory_model_only_v1',recording_limit_reached:true,administration:{model_id:'wav-sha256:'+hash,model_sha256:hash,model_presented_confirmed:true}};
   const form=new FormData();form.append('file',wav);form.append('context_json',JSON.stringify(ctx));
   const r=await fetch('/phrase-analysis',{method:'POST',body:form});if(!r.ok)throw Error(await r.text());
   const source=await r.json(),protocol=await(await fetch('/motor-profile-protocol')).json();
   await s.registerResult(e.evaluation_id,aid,'phrase',source,[{blob:wav,role:'wav'},{blob:wav,role:'model'}],protocol);
   return {id:e.evaluation_id,aid,hash};
 },fixture);
 await p.goto(base+`/phrase?evaluation_id=${auditory.id}&attempt_id=${auditory.aid}`);await consult();
 await p.getByRole('button',{name:'Editar / Reanalizar'}).click();
 await p.locator('#attempt1 .modelState').filter({hasText:'Modelo identificado:'}).waitFor();
 check(await p.locator('#attempt1 [data-f="modality"]').inputValue()==='auditory_model_only_v1','editing preserves auditory modality');
 check(await p.locator('#attempt1 [data-f="limit"]').isChecked(),'editing preserves recorded limit flag');
 check((await p.locator('#attempt1 .modelState').innerText()).includes(auditory.hash),'editing restores byte-identical original model');
 check((await p.locator('#attempt1 .modelState').innerText()).includes('Aún no presentado'),'restoring model never fabricates its presentation confirmation');
 check(errors.length===0,'no uncaught browser errors');console.log(`Continuity browser: ${checks} checks passed`);await context.close();
}finally{await browser.close();}
