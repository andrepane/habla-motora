import test from 'node:test';
import assert from 'node:assert/strict';
import {ProsodyState,segments,displayTime,frameValue,edgeRegions,nearestFrame,identityKey,sourceKey} from '../frontend/phrase-prosody-state.js';
const frame=(i,t,hz,st=0)=>({frame_index:i,time_relative_s:t,f0_hz:hz,f0_st:st,defined:hz!==null});
test('undefined frames and missing grid cells split all segments, never interpolated',()=>{
  const fs=[frame(1,.1,100),frame(2,.105,100),frame(3,.11,null),frame(4,.115,200),frame(6,.125,200)];
  assert.deepEqual(segments(fs,'hz',.005).map(x=>x.map(p=>p.frame.frame_index)),[[1,2],[4],[6]]);
  assert.deepEqual(segments(fs,'st',.005).map(x=>x.length),[2,1,1]);
});
test('Hz/ST use exported exact values including zero; null is never zero',()=>{
  assert.equal(frameValue(frame(1,0,200,0),'st'),0);
  assert.equal(frameValue(frame(1,0,200,12),'hz'),200);
  assert.equal(frameValue(frame(1,0,null,null),'st'),null);
  assert.equal(frameValue({...frame(1,0,200),f0_st:null},'st'),null);
});
test('time normalization changes only coordinates relative to entire selection',()=>{
  assert.equal(displayTime(1,4,'seconds'),1);assert.equal(displayTime(1,4,'percent'),25);
  const fs=[frame(1,1,200)];const original=structuredClone(fs);segments(fs,'st',.005);assert.deepEqual(fs,original);
});
test('edge cells and cursor distinguish no analysis from undefined F0',()=>{
  const fs=[frame(1,.0275,200),frame(2,.0325,null)];
  assert.deepEqual(edgeRegions(fs,1,.005),[{start_s:0,end_s:.025,kind:'edge'},{start_s:.035,end_s:1,kind:'edge'}]);
  assert.equal(nearestFrame(fs,0,.005),null);assert.equal(nearestFrame(fs,.032,.005).defined,false);
});
for(const reason of ['wav','selection','attempt','modality','phrase_version','engine','configuration']){
  test(`${reason} invalidates display and late responses, retains audit history`,()=>{
    const s=new ProsodyState();const r=s.begin('source');const result={status:'completed',metrics:{zero:{value:0,reason:null}},frames:[frame(1,0,200)]};
    s.accept(result,r,'source');s.invalidate(reason);
    assert.equal(s.status,'stale');assert.equal(s.result,null);assert.equal(s.accept(result,r,'source'),false);
    const out=s.exported({});assert.equal(out.results_current,false);assert.deepEqual(out.history[0].response,result);
  });
}
test('partial retains valid metrics and null reasons in independent export',()=>{
  const s=new ProsodyState();const n=s.begin('a');const result={status:'partial',metrics:{a:{value:0,reason:null},b:{value:null,reason:'insufficient_temporal_support'}},frames:[],gaps:[],warnings:[],reference_st:{value_hz:200}};
  assert.equal(s.accept(result,n,'a'),true);const out=s.exported({unit:'st'});assert.deepEqual(out.current_response,result);
  out.current_response.metrics.a.value=9;assert.equal(s.result.metrics.a.value,0);
});
test('wrong attempt/context cannot accept an otherwise fresh response',()=>{
  const s=new ProsodyState();const n=s.begin('attempt1');assert.equal(s.accept({status:'completed'},n,'attempt2'),false);
});
test('identity includes phrase version, config and engine, source excludes pause results',()=>{
  const p={config_sha256:'c',engine_sha256:'e',phrase_config_sha256:'p',protocol_version:'v',integration_version:'i'};
  assert.notEqual(identityKey(p),identityKey({...p,phrase_config_sha256:'new'}));
  const source={provenance:{file_sha256:'w',context_sha256:'x'},review:{words:14}};
  assert.equal(sourceKey(source),sourceKey({...source,review:{words:90},pauses:[1]}));
});
