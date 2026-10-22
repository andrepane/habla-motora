import test from "node:test";
import assert from "node:assert/strict";
import {
  encodeWav,
  parseWav,
  centralInterval,
  metricText,
  REQUESTED,
} from "../frontend/audio.js";
test("PCM16 round trip / rates / signed samples", () => {
  for (const rate of [44100, 48000]) {
    const a = parseWav(encodeWav(Float32Array.from([-1, 0, 0.5, 1]), rate));
    assert.equal(a.rate, rate);
    assert.equal(a.bits, 16);
    assert.equal(a.samples[0], -1);
    assert.equal(a.samples[1], 0);
    assert.ok(Math.abs(a.samples[2] - 0.5) < 0.00004);
  }
});
test("central 3 s selection", () => {
  assert.deepEqual(centralInterval(1, 7, 8), { start_s: 2.5, end_s: 5.5 });
  assert.equal(centralInterval(0, 2.99, 8), null);
  assert.equal(centralInterval(-1, 6, 8), null);
  assert.equal(centralInterval(0, 9, 8), null);
});
test("null is not zero and negative HNR is preserved", () => {
  assert.equal(metricText({ value: null }), "No calculable");
  assert.equal(metricText({ value: 0 }), "0");
  assert.equal(metricText({ value: -10 }), "-10");
});
test("incompatible uploaded WAV is rejected without conversion", () => {
  for (const [at, value] of [
    [20, 3],
    [22, 2],
    [24, 22050],
    [34, 8],
  ]) {
    const b = encodeWav(new Float32Array(20), 48000),
      v = new DataView(b);
    if (at === 24) v.setUint32(at, value, true);
    else v.setUint16(at, value, true);
    assert.throws(() => parseWav(b));
  }
  assert.throws(() => parseWav(new ArrayBuffer(10)));
});
test("unsupported capture rate is not silently resampled", () =>
  assert.throws(() => encodeWav(new Float32Array(5), 22050)));
test("requested microphone processing constraints", () => {
  assert.equal(REQUESTED.echoCancellation, false);
  assert.equal(REQUESTED.noiseSuppression, false);
  assert.equal(REQUESTED.autoGainControl, false);
});

test("tiny finite measurements are not rounded to fake zeros", () => {
  assert.notEqual(metricText({ value: 0.0000002 }), "0");
  assert.notEqual(metricText({ value: -0.0000002 }), "0");
});

// Exercise the real presentation script with a minimal DOM, without invoking
// controllers or altering their status/recommendation inputs.
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {recommended} from '../frontend/evaluation-flow.js';
const visualScript=readFileSync(new URL('../frontend/visual-interface.js',import.meta.url),'utf8');
function prosodyStepper(initial,current=false){
  let observer;
  const panel={dataset:{status:initial}},attrs=new Map(current?[['aria-current','step']]:[]);
  let note;
  const button={dataset:{phraseStep:'prosody'},disabled:false,
    getAttribute:k=>attrs.get(k)??null,setAttribute:(k,v)=>attrs.set(k,v),
    querySelector:()=>note,append:n=>{note=n;}};
  const slot={querySelector:s=>s==='.prosodyPanel'?panel:null,querySelectorAll:()=>[button]};
  const document={body:{dataset:{page:'phrase'}},querySelector:()=>null,
    querySelectorAll:s=>s==='#attempts>section'?[slot]:[],createElement:()=>({textContent:''})};
  vm.runInNewContext(visualScript,{document,location:{search:''},URLSearchParams,
    MutationObserver:class{constructor(callback){observer=callback;}observe(){}},
    requestAnimationFrame:callback=>callback()});
  return {panel,button,label:()=>note.textContent,state:()=>attrs.get('data-visual-state'),
    change:status=>{panel.dataset.status=status;observer();}};
}
test('Prosody completed is presented as Completado',()=>{
  const view=prosodyStepper('completed');assert.equal(view.label(),'Completado');assert.equal(view.state(),'completed');
});
test('Prosody partial remains Parcial, including the active step and status changes',()=>{
  const view=prosodyStepper('completed');view.change('partial');
  assert.equal(view.label(),'Parcial');assert.equal(view.state(),'partial');
  const active=prosodyStepper('partial',true);assert.equal(active.label(),'Paso actual · Parcial');
  assert.ok(!active.label().includes('Completado'));assert.equal(active.panel.dataset.status,'partial');
});
test('Prosody not_evaluable retains its explicit meaning, also when active',()=>{
  const view=prosodyStepper('not_evaluable');assert.equal(view.label(),'No evaluable');
  assert.equal(view.state(),'not_evaluable');assert.ok(!view.label().includes('Completado'));
  assert.equal(prosodyStepper('not_evaluable',true).label(),'Paso actual · No evaluable');
});
test('Stepper presentation leaves the existing 10.2 recommendation and source state unchanged',()=>{
  for(const status of ['completed','partial','not_evaluable']){
    const rows=['vowel','ddk','phrase'].map(task=>({attempt:{task,attempt_id:task,current:{[task]:'source'}},summary:{status:task==='phrase'?'partial':'completed',representative:true,eligible:true,domains:{pauses:{status:'completed'},prosody:{status}}}}));
    const snapshot=structuredClone(rows),before=recommended({},rows),view=prosodyStepper(status);
    view.change(status);assert.deepEqual(rows,snapshot);assert.deepEqual(recommended({},rows),before);
    assert.equal(view.panel.dataset.status,status);
    assert.equal(before.label,status==='partial'?'Analizar Prosodia':'Ver Perfil');
  }
});
