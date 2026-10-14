import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import * as audio from '../frontend/audio.js';

// Run the actual event handlers with deferred browser operations. No acoustic mocks.
const source = fs.readFileSync(new URL('../frontend/app.js', import.meta.url), 'utf8')
  .replace(/^import[\s\S]*?from "\.\/audio\.js";\n/, '');
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
function harness(stage) {
  const pending = deferred(), elements = new Map(), contexts = [], tracks = [];
  let calls = 0, nodes = 0;
  const element = (id) => {
    if (!elements.has(id)) elements.set(id, {
      value: '', disabled: false, hidden: true, clientWidth: 800,
      addEventListener() {}, pause() {}, removeAttribute() {},
      getContext: () => ({ scale() {}, clearRect() {} }),
    });
    return elements.get(id);
  };
  function stream() {
    const track = { stopped: false, stop() { this.stopped = true; },
      getSettings: () => ({}), getConstraints: () => ({}) };
    tracks.push(track);
    return { getTracks: () => [track], getAudioTracks: () => [track] };
  }
  class Context {
    constructor() {
      this.sampleRate = 48000;
      this.state = 'suspended';
      const first = contexts.length === 0;
      this.audioWorklet = { addModule: () => first && stage === 'worklet' ? pending.promise : Promise.resolve() };
      this.resume = () => first && stage === 'resume' ? pending.promise : Promise.resolve();
      contexts.push(this);
    }
    createMediaStreamSource() { return { connect() {}, disconnect() {} }; }
    async close() { this.state = 'closed'; }
  }
  class Node {
    constructor() { nodes++; this.port = {}; }
    connect() {}
    disconnect() {}
  }
  const sandbox = {
    ...audio, document: { getElementById: element }, devicePixelRatio: 1,
    window: { AudioWorkletNode: Node, addEventListener() {} },
    AudioWorkletNode: Node, AudioContext: Context, performance,
    navigator: { mediaDevices: { getUserMedia: () => {
      calls++;
      return calls === 1 && stage === 'permission' ? pending.promise : Promise.resolve(stream());
    } } }, URL, AbortController, setTimeout,
  };
  vm.runInNewContext(source, sandbox);
  return { element, pending, contexts, tracks, stream, nodes: () => nodes };
}
const flush = () => new Promise((resolve) => setImmediate(resolve));
for (const stage of ['permission', 'worklet', 'resume']) {
  for (const rejected of [false, true]) {
    test(`cancel during ${stage}, then restart before old ${rejected ? 'rejection' : 'completion'}`, async () => {
      const h = harness(stage);
      const first = h.element('record').onclick();
      await flush();
      await h.element('stop').onclick();
      const second = h.element('record').onclick();
      await second;
      assert.equal(h.element('status').textContent, 'Grabando /a/…');
      if (rejected) h.pending.reject(new Error('old capture failed'));
      else h.pending.resolve(stage === 'permission' ? h.stream() : undefined);
      await first;
      assert.equal(h.element('status').textContent, 'Grabando /a/…');
      assert.equal(h.element('record').disabled, true);
      assert.equal(h.element('stop').disabled, false);
      assert.equal(h.tracks.filter((t) => !t.stopped).length, 1);
      assert.equal(h.contexts.filter((c) => c.state !== 'closed').length, 1);
      assert.equal(h.nodes(), stage === 'resume' ? 2 : 1);
      await h.element('stop').onclick();
      assert.ok(h.tracks.every((t) => t.stopped));
      assert.ok(h.contexts.every((c) => c.state === 'closed'));
    });
  }
}
