import assert from 'node:assert/strict';
import fs from 'node:fs';
const enabled=process.env.USABILITY_AUDIT==='1',dir=process.env.VISUAL_EVIDENCE_DIR||'/tmp/h104b-visual';
const findings=[],positions=[];
export async function usabilityCheckpoint(page,name,width){
 if(!enabled)return;
 const check=(value,label)=>{assert.ok(value,`${name}/${width}: ${label}`);findings.push({screen:name,width,label,passed:true});};
 const actions=page.locator('#clinicalActions');
 if(['03-vocal','04-ddk','06-pausas'].includes(name)){const selector=name==='06-pausas'?'[data-next-step]:not([hidden])':'#clinicalActions';positions.push({screen:name,width,...await page.locator(selector).first().evaluate(n=>({top:n.getBoundingClientRect().top+scrollY,height:document.documentElement.scrollHeight}))});fs.writeFileSync(`${dir}/positions.json`,JSON.stringify(positions,null,2));}

 if(['03-vocal','04-ddk'].includes(name)){
  const anchor=page.locator(name==='03-vocal'?'#warnings':'#reviewedCards');
  const gap=await actions.evaluate((node,id)=>node.getBoundingClientRect().top-document.querySelector(id).getBoundingClientRect().bottom,name==='03-vocal'?'#warnings':'#reviewedCards');
  check(gap>=0&&gap<80,'single existing CTA immediately follows result/warnings');
  check(await page.locator('#clinicalActions').count()===1,'no duplicated clinical action block');
  await actions.scrollIntoViewIfNeeded();await page.screenshot({path:`${dir}/step-end-${name}-${width}.png`});
  const details=page.locator('details[data-polish="metrics"]');
  check(await details.count()>0,'secondary metrics retained in disclosure');
  await details.locator('summary').click();check(await details.locator('.card,.metric').count()>0,'secondary values still accessible');await details.locator('summary').click();
 }
 if(name==='04-ddk'){
  const scroll=page.locator('#editTable').locator('..');
  check(await scroll.getAttribute('tabindex')==='0','table keyboard focus retained');
  const before=await page.locator('#editTable tbody tr:first-child td:first-child').boundingBox();
  await scroll.focus();
  const overflows=await scroll.evaluate(n=>n.scrollWidth>n.clientWidth+1);
  if(overflows){await page.keyboard.press('ArrowRight');await page.waitForFunction(()=>document.querySelector('#editTable').parentElement.scrollLeft>0);check(true,'native keyboard horizontal scroll works');}
  const control=page.locator('#editTable tbody tr:first-child input').first();await control.focus();await page.keyboard.press('Tab');
  check(await page.locator('#editTable tbody tr:first-child select').evaluate(n=>document.activeElement===n),'time-to-label keyboard tab order preserved');
  await scroll.evaluate(n=>n.scrollLeft=n.scrollWidth);
  const after=await page.locator('#editTable tbody tr:first-child td:first-child').boundingBox();
  check(Math.abs(before.x-after.x)<2,'event identity sticky during horizontal scrolling');
  check(await page.locator('#editTable tbody tr:first-child select').count()>0,'manual label control retained');
  if(width<600){check(await page.locator('#ddk-scroll-help').isVisible(),'horizontal scroll hint visible');await page.screenshot({path:`${dir}/ddk-horizontal-${width}.png`,fullPage:true});}
  await scroll.evaluate(n=>n.scrollLeft=0);
 }
 if(name==='06-pausas'){
  const panel=page.locator('.pausePanel:visible'),notice=panel.locator('.pause-result-state');
  check((await notice.innerText()).includes('Resultado confirmado'),'confirmed result explicit');
  check(!await panel.locator('[data-p="status"]').isVisible(),'draft selector never contradicts confirmed result');
  const gap=await panel.locator('[data-next-step]').evaluate(n=>n.getBoundingClientRect().top-n.closest('.pausePanel').querySelector('[data-p=state]').getBoundingClientRect().bottom);
  check(gap>=0&&gap<150,'Continue Prosody next to confirmation');
  const raw=await panel.locator('[data-p="start"]').inputValue(),seconds=await panel.locator('[data-seconds-for="p-start"]').inputValue();
  check(Number(seconds)===Number(raw)/48000,'seconds display is exact sample/rate quotient');
  const audit=JSON.parse(await panel.locator('[data-p="audit"]').textContent());
  check(audit.current_response.temporal_review.intervals[0].start_sample===96000,'exact interval samples preserved');
  check(await panel.locator('details.sample-details').count()>0,'sample controls preserved in details');
  // Observe presentation of an existing invalidation on a clone page, leaving clinical journey untouched.
  if(width===320){
   const historyBefore=await page.evaluate(async()=>{const id=new URL(location.href).searchParams.get('evaluation_id');return JSON.stringify(await(await import('/static/motor-profile-store.js')).getEvaluation(id));});
   await page.screenshot({path:`${dir}/pauses-confirmed-${width}.png`,fullPage:true});
   const rawAudit=await panel.locator('[data-p="audit"]').textContent();
   await panel.locator('[data-p="audit"]').evaluate(n=>{const a=JSON.parse(n.textContent);a.history.push({event:'invalidated',response:a.current_response});a.current_response=null;n.textContent=JSON.stringify(a);});
   await notice.filter({hasText:'Cambios pendientes posteriores'}).waitFor();
   check(await panel.locator('[data-p="status"]').count()===1,'later draft distinct from retained confirmed result');
   await page.screenshot({path:`${dir}/pauses-later-draft-${width}.png`,fullPage:true});
   await panel.locator('[data-p="audit"]').evaluate((n,text)=>n.textContent=text,rawAudit);
   await notice.filter({hasText:'Resultado confirmado'}).waitFor();
   check(await page.evaluate(async()=>{const id=new URL(location.href).searchParams.get('evaluation_id');return JSON.stringify(await(await import('/static/motor-profile-store.js')).getEvaluation(id));})===historyBefore,'presentation of subsequent draft never writes sources');
  }
 }
 if(name==='08-perfil'){
  check((await page.locator('#export').innerText()).includes('Resumen para consultar o archivar'),'summary purpose explicit');
  check((await page.locator('#bundle').innerText()).includes('Copia completa para recuperar'),'recoverable purpose explicit');
  // Import an actual exported summary; validation still rejects it without writing.
  const summaryDownload=page.waitForEvent('download');await page.locator('#export').click();const download=await summaryDownload;
  const content=fs.readFileSync(await download.path());
  const state=await page.evaluate(async()=>{const id=new URL(location.href).searchParams.get('evaluation_id');return JSON.stringify(await(await import('/static/motor-profile-store.js')).getEvaluation(id));});
  const management=page.locator('.profile-management');if(await management.count())await management.evaluate(n=>n.open=true);
  await page.locator('#import').setInputFiles({name:'resumen.json',mimeType:'application/json',buffer:content});
  await page.locator('#message').filter({hasText:'Este archivo parece ser un resumen'}).waitFor();
  check((await page.locator('#message').innerText()).includes('Perfil → Copia completa'),'summary import error gives recovery location');
  check(await page.evaluate(async()=>{const id=new URL(location.href).searchParams.get('evaluation_id');return JSON.stringify(await(await import('/static/motor-profile-store.js')).getEvaluation(id));})===state,'summary rejected without changing evaluation');
  await page.screenshot({path:`${dir}/summary-import-error-${width}.png`,fullPage:true});
  if(await management.count())await management.evaluate(n=>n.open=false);
 }
 fs.writeFileSync(`${dir}/usability.json`,JSON.stringify(findings,null,2));
}
