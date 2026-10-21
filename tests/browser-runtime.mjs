import {chromium as engine} from 'playwright';
// Optional executable for environments without Playwright's managed download.
export const chromium={...engine,launch:options=>engine.launch({...options,
  ...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE,args:[...(options?.args??[]),'--no-sandbox','--disable-gpu']}:{}),
})};
// Existing acoustic/editor regressions explicitly exercise the optional full technical view.
// The guided default is covered separately by the clinical journey browser test.
export async function technicalTaskView(page){
 await page.addInitScript(()=>{
  new MutationObserver(()=>{
   const d=document.querySelector('#automaticDetails');if(d)d.open=true;
   const b=document.querySelector('.showAllSteps');if(b&&!b.dataset.regressionOpen){b.dataset.regressionOpen='true';b.click();}
  }).observe(document,{childList:true,subtree:true});
 });
}
