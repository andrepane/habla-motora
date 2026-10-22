import {chromium} from './browser-runtime.mjs';
import fs from 'node:fs';import assert from 'node:assert/strict';
const base=process.env.BASE_URL||'http://127.0.0.1:8000',f=JSON.parse(fs.readFileSync(process.env.PROFILE_FIXTURES||'/tmp/profile-fixtures.json'));
const browser=await chromium.launch({headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});let checks=0;
const check=(v,why)=>assert.ok(v,`${++checks}: ${why}`);
for(let i=0;i<40;i++){try{if((await fetch(base+'/health')).ok)break;}catch{}await new Promise(r=>setTimeout(r,200));}
try{for(const width of [1440,390,320]){
 const ctx=await browser.newContext({acceptDownloads:true,permissions:['microphone'],viewport:{width,height:844}}),p=await ctx.newPage();
 await p.goto(base+'/vocal');await p.locator('.flow-context').waitFor();await p.locator('h1').click();let emptyDialogs=0;
 const noDialog=d=>{emptyDialogs++;d.dismiss();};p.on('dialog',noDialog);await p.reload();await p.locator('.flow-context').waitFor();p.off('dialog',noDialog);check(emptyDialogs===0,'empty independent task has no exit warning');
 await p.locator('#record').click();await p.waitForTimeout(700);await p.locator('#stop').click();await p.locator('#audioInfo').filter({hasText:'vocal.wav'}).waitFor();
 const info=await p.locator('#audioInfo').textContent();
 p.once('dialog',d=>{check(d.type()==='beforeunload','independent reload is protected');d.dismiss();});await p.reload({timeout:2000}).catch(()=>null);check(await p.locator('#audioInfo').textContent()===info,'cancel reload retains captured audio');
 p.once('dialog',d=>{check(d.type()==='confirm','independent internal navigation is protected');d.dismiss();});await p.locator('nav [data-evaluation-task="ddk"]').click();check(new URL(p.url()).pathname==='/vocal','cancel task navigation retains page');
 const download=p.waitForEvent('download');await p.locator('#downloadAudio').click();await download;check(await p.locator('#audioInfo').textContent()===info,'download does not clear recording or cause exit warning');
 // Browsers do not expose reliable download completion to the app. Keep protection.
 p.once('dialog',d=>d.accept());await p.reload();await p.locator('.flow-context').waitFor();check(await p.locator('#audioInfo').textContent()==='Todavía no hay audio.','confirmed reload deliberately discards temporary recording');
 check(await p.evaluate(async()=>!(await indexedDB.databases()).length),'independent capture creates no persistent database');
 await p.locator('#record').click();await p.waitForTimeout(500);await p.locator('#stop').click();await p.locator('#audioInfo').filter({hasText:'vocal.wav'}).waitFor();p.once('dialog',d=>d.accept());await p.locator('nav [data-evaluation-task="ddk"]').click();await p.waitForURL('**/ddk');check(true,'confirmed navigation permits exit');
 // Build immutable source fixtures using the existing registry and real API.
 await p.goto(base+'/profile');
 const seed=await p.evaluate(async f=>{
  const s=await import('/static/motor-profile-store.js'),e=s.createEvaluation('10.4A synthetic continuity');await s.saveEvaluation(e);const ids={};
  for(const task of ['vowel','ddk','phrase'])await s.mutateEvaluation(e.evaluation_id,e=>{ids[task]=s.addAttempt(e,task);s.bind(e,task,ids[task]);});
  const protocol=await(await fetch('/motor-profile-protocol')).json(),file=task=>new File([Uint8Array.from(atob(f.wavs[task]),c=>c.charCodeAt(0))],task+'.wav',{type:'audio/wav'});
  const ops=[{action:'label',id:'c1',label:'pa'},{action:'delete',id:'c3'}],form=new FormData();form.append('file',file('ddk'));form.append('emission_start_s','0');form.append('emission_end_s','1');form.append('expected_file_sha256',f.payloads.ddk.provenance.file_sha256);form.append('review_json',JSON.stringify({operations:ops,confirmed:false}));
  const response=await fetch('/ddk-analysis',{method:'POST',body:form});if(!response.ok)throw Error(await response.text());const draft=await response.json();
  for(const kind of ['vowel','ddk','phrase','pauses','prosody']){const task=['pauses','prosody'].includes(kind)?'phrase':kind;await s.registerResult(e.evaluation_id,ids[task],kind,kind==='ddk'?draft:f.payloads[kind],[{blob:file(task),role:'wav'}],protocol);}
  return {id:e.evaluation_id,ids,draft};
 },f);
 const record=()=>p.evaluate(async id=>(await import('/static/motor-profile-store.js')).getEvaluation(id),seed.id);
 const url=task=>base+({ddk:'/ddk',phrase:'/phrase'}[task])+`?evaluation_id=${seed.id}&attempt_id=${seed.ids[task]}`;
 await p.goto(url('ddk'));await p.locator('#savedTask').waitFor();await p.locator('[data-resume-ddk]:not(:disabled)').waitFor();const beforeDdk=JSON.stringify(await record());let posts=0;const onPost=r=>{if(r.method()==='POST')posts++;};p.on('request',onPost);
 await p.locator('[data-resume-ddk]').click();await p.locator('#reviewSection').waitFor();
 check(posts===0,'DDK resume makes no detector/API call');check(JSON.stringify(await record())===beforeDdk,'DDK resume makes no source/history/invalidation writes');
 check(await p.locator('#editTable tbody tr').count()===2,'DDK stored removal retained');check(await p.locator('#editTable tbody tr').first().locator('select').inputValue()==='pa','DDK stored manual label retained');
 check(await p.getByRole('button',{name:'Editar / Reanalizar',exact:true}).count()===1,'DDK explicit reanalysis remains separate');
 await p.locator('#editTable tbody tr').last().locator('select').selectOption('ta');await p.locator('#confirmed').check();await p.locator('#calculateReview').click();await p.locator('[data-saved-kind="ddk"]').waitFor();
 await p.goto(url('ddk'));await p.locator('[data-ddk-read-only]').waitFor();const confirmedRecord=JSON.stringify(await record()),postsBefore=posts;
 check((await p.locator('[data-ddk-read-only]').innerText()).includes('Revisión manual confirmada'),'DDK confirmed review human-readable');check(await p.locator('[data-ddk-read-only] table tbody tr').count()===2,'confirmed events visible');check((await p.locator('[data-ddk-read-only]').innerText()).includes('eliminado de la revisión'),'manual exclusions visible');check((await p.locator('[data-ddk-read-only]').innerText()).includes('Ciclos revisados'),'reviewed cycle result explicit');
 await p.reload();await p.locator('[data-ddk-read-only]').waitFor();check(JSON.stringify(await record())===confirmedRecord&&posts===postsBefore,'confirmed DDK consultation is read-only');check(await p.locator('[data-resume-ddk]').count()===0,'confirmed review cannot silently resume editing');
 // The unreviewed automatic result also resumes its original candidate list.
 await p.evaluate(async({eid,aid,f})=>{const s=await import('/static/motor-profile-store.js'),protocol=await(await fetch('/motor-profile-protocol')).json();await s.registerResult(eid,aid,'ddk',f.payloads.ddk_automatic,[{blob:new File([Uint8Array.from(atob(f.wavs.ddk),c=>c.charCodeAt(0))],'ddk.wav'),role:'wav'}],protocol);},{eid:seed.id,aid:seed.ids.ddk,f});
 await p.goto(url('ddk'));await p.locator('[data-resume-ddk]:not(:disabled)').waitFor();const autoBefore=JSON.stringify(await record()),autoPosts=posts;
 await p.locator('[data-resume-ddk]').click();await p.locator('#reviewSection').waitFor();check(await p.locator('#editTable tbody tr').count()===f.payloads.ddk_automatic.automatic_original.detection.events.length,'automatic-only DDK resumes original candidates');check(posts===autoPosts&&JSON.stringify(await record())===autoBefore,'automatic-only resume also makes no requests or writes');
 p.off('request',onPost);
 // Real export/import creates typed-array artifacts. Resume must preserve all bytes/identity.
 await p.goto(base+'/profile?evaluation_id='+seed.id);await p.locator('#bundle').waitFor();const dl=p.waitForEvent('download');await p.locator('#bundle').click();const bundle=fs.readFileSync(await(await dl).path());
 const imported=await browser.newContext({viewport:{width,height:844}}),q=await imported.newPage();await q.goto(base+'/');await q.locator('#import').setInputFiles({name:'evaluation.json',mimeType:'application/json',buffer:bundle});await q.locator('#recommended').waitFor();await q.goto(url('phrase'));await q.locator('[data-resume-phrase]:not(:disabled)').waitFor();
 const get=()=>q.evaluate(async id=>(await import('/static/motor-profile-store.js')).getEvaluation(id),seed.id),before=JSON.stringify(await get());let analyses=0;q.on('request',r=>{if(r.method()==='POST')analyses++;});
 const recovered=await q.evaluate(async({eid,aid})=>{const s=await import('/static/motor-profile-store.js'),e=await s.getEvaluation(eid),ref=e.sources[e.attempts[aid].current.phrase].assets.find(x=>x.role==='wav'),a=await s.artifact(ref.sha256),{exactAudioBuffer}=await import('/static/recovered-audio.js'),buffer=exactAudioBuffer(a.bytes);return {hash:await s.sha(buffer),expected:ref.sha256,bytes:Array.from(new Uint8Array(buffer))};},{eid:seed.id,aid:seed.ids.phrase});
 check(Buffer.from(recovered.bytes).equals(Buffer.from(f.wavs.phrase,'base64'))&&recovered.hash===recovered.expected,'import recovery is byte/hash/length identical');
 await q.locator('[data-resume-phrase]').click();await q.locator('.profile-bridge p').filter({hasText:'Continuación de revisiones'}).waitFor();check(await q.locator('#attempt1 [data-phrase-step="pauses"]').isEnabled(),'imported phrase resumes after one click');check(JSON.stringify(await get())===before&&analyses===0,'import continuation changes no sources, identities, dependencies or states');
 await imported.close();
 // Gate protocol loading explicitly; only dependent actions must be unavailable.
 let release;const gate=new Promise(r=>release=r);await p.route('**/phrase-protocol',async route=>{await gate;await route.continue();});
 await p.goto(url('phrase'),{waitUntil:'domcontentloaded'});await p.locator('[data-resume-phrase]').waitFor();check(await p.locator('[data-resume-phrase]').isDisabled(),'slow protocol keeps continuation disabled');check((await p.locator('[data-controller-state]').innerText()).includes('Preparando'),'preparation state is visible');check(await p.getByRole('link',{name:'Volver a evaluación',exact:true}).isVisible(),'read/navigation remains available during preparation');
 release();await p.locator('[data-resume-phrase]:not(:disabled)').waitFor();await p.locator('[data-resume-phrase]').click();await p.locator('.profile-bridge p').filter({hasText:'Continuación de revisiones'}).waitFor();check(await p.locator('#attempt1 [data-phrase-step="content"]').isEnabled(),'one click after preparation works');await p.unroute('**/phrase-protocol');
 await p.route('**/phrase-protocol',route=>route.fulfill({status:503,body:'Unavailable'}));await p.goto(url('phrase'),{waitUntil:'domcontentloaded'});await p.getByRole('button',{name:'Reintentar preparación'}).waitFor();check(await p.locator('[data-resume-phrase]').isDisabled(),'failed preparation does not expose a dead action');check((await p.locator('[data-controller-state]').innerText()).includes('No se pudo preparar'),'failed preparation explained');await p.unroute('**/phrase-protocol');await p.getByRole('button',{name:'Reintentar preparación'}).click();await p.locator('[data-resume-phrase]:not(:disabled)').waitFor();await p.locator('[data-resume-phrase]').click();await p.locator('.profile-bridge p').filter({hasText:'Continuación de revisiones'}).waitFor();check(true,'retry preparation safely restores continuation');
 // Native tab-close warning is requested by the same beforeunload mechanism.
 const close=await ctx.newPage();await close.goto(base+'/vocal');await close.locator('.flow-context').waitFor();await close.locator('#record').click();await close.waitForTimeout(400);await close.locator('#stop').click();await close.locator('#audioInfo').filter({hasText:'vocal.wav'}).waitFor();const closeDialog=close.waitForEvent('dialog');await close.close({runBeforeUnload:true});const dialog=await closeDialog;check(dialog.type()==='beforeunload','tab close invokes protection');await dialog.dismiss();check(!close.isClosed(),'cancel close keeps task alive');
 await ctx.close();console.log(`H10.4A ${width}px completed`);
}}finally{await browser.close();}
console.log(`H10.4A critical continuity: ${checks} checks passed`);
