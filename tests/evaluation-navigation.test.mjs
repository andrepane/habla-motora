import test from 'node:test';
import assert from 'node:assert/strict';
import {destination,evaluationUrl,linkNavigation} from '../frontend/evaluation-navigation.js';
const e={evaluation_id:'E',bindings:{vowel:'v',ddk:'d',phrase:'p'},attempts:Object.fromEntries([['v','vowel'],['d','ddk'],['p','phrase'],['p2','phrase']].map(([id,task])=>[id,{task,evaluation_id:'E'}]))};
test('evaluation routes preserve identity and representative without choosing one',()=>{
  const before=structuredClone(e);
  for(const [task,id]of Object.entries(e.bindings))assert.equal(new URL(destination(e,task),'http://local').searchParams.get('attempt_id'),id);
  assert.equal(destination(e,'phrase',{phrase:'p2'}),'/phrase?evaluation_id=E&attempt_id=p2');
  assert.equal(destination(e,'ddk',{ddk:'foreign'}),'/ddk?evaluation_id=E&attempt_id=d');
  assert.equal(destination({...e,bindings:{}},'ddk'),'/evaluation?evaluation_id=E&manage_task=ddk');
  assert.equal(destination(e),'/profile?evaluation_id=E');assert.deepEqual(e,before);
});
test('URLs encode evaluation identity and explicit attempt',()=>{
  assert.equal(new URL(evaluationUrl('E &','vowel','V?'),'http://local').searchParams.get('evaluation_id'),'E &');
});
test('navigation retains original destination through asynchronous resolution and clearing context',()=>{
  const oldDoc=globalThis.document,oldLocation=globalThis.location,oldStorage=globalThis.sessionStorage;
  const links=['/','/ddk','/phrase','/profile'].map(href=>({href,dataset:{}}));
  globalThis.document={querySelectorAll:()=>links};globalThis.location={href:'http://local/profile'};globalThis.sessionStorage={getItem:()=>null};
  try{linkNavigation('E');linkNavigation('E',e);assert.equal(links[1].href,'/ddk?evaluation_id=E&attempt_id=d');linkNavigation(null);assert.equal(links[1].href,'/ddk');}finally{globalThis.document=oldDoc;globalThis.location=oldLocation;globalThis.sessionStorage=oldStorage;}
});
