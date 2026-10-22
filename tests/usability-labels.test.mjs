import test from 'node:test';
import assert from 'node:assert/strict';
import {secondsAt,sampleAtSeconds,displayReason,displayUnit,importMessage,pauseDisplay} from '../frontend/usability-labels.js';
test('seconds presentation roundtrips exact samples at 44.1/48 kHz including zero',()=>{
 for(const rate of [44100,48000])for(const index of [0,1,17,44099,48001,384000]){
  assert.equal(secondsAt(index,rate),index/rate);assert.equal(sampleAtSeconds(secondsAt(index,rate),rate),index);
 }
 assert.equal(secondsAt(null,48000),null);assert.equal(secondsAt(1,null),null);
});
test('display translations preserve null, zero, raw units and reasons in source',()=>{
 const source={value:null,reason:'insufficient_intervals',unit:'count'},before=JSON.stringify(source);
 assert.match(displayReason(source.reason),/No hay suficientes intervalos/);
 assert.equal(displayUnit(source.unit,'Pausas revisadas'),'pausas');assert.equal(JSON.stringify(source),before);
 assert.equal(displayReason('unknown_code'),'unknown_code');assert.equal(displayUnit('Hz'),'Hz');
 assert.equal(displayReason(null),null);assert.equal(secondsAt(0,48000),0);
});
test('summary import gets guidance while bundle validation errors remain unchanged',()=>{
 const error=new Error('Paquete no compatible.');assert.match(importMessage(error,{schema_version:'motor_speech_profile_v1'}),/Perfil → Copia completa/);
 assert.equal(importMessage(error,{schema_version:'unknown'}),error.message);
 assert.equal(importMessage(new Error('Hash incorrecto'),{schema_version:'motor_speech_profile_v1'}),'Hash incorrecto');
});

test('pause presentation distinguishes confirmed result, later draft, and not evaluable',()=>{
 const result={temporal_review:{status:'confirmed'}},audit={current_response:result,history:[]};const raw=JSON.stringify(audit);
 assert.match(pauseDisplay(audit),/^Resultado confirmado/);assert.equal(JSON.stringify(audit),raw);
 assert.match(pauseDisplay({current_response:null,history:[{response:result}]}),/^Cambios pendientes posteriores/);
 assert.match(pauseDisplay({current_response:{temporal_review:{status:'not_evaluable'}}}),/^Revisión no evaluable/);
 assert.match(pauseDisplay({history:[{draft:{status:'confirmed'}}]}),/^Borrador/);
});
