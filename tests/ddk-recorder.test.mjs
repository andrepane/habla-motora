import test from "node:test";
import assert from "node:assert/strict";
import { DdkRecorder } from "../frontend/ddk-recorder.js";
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((a, b) => {
    resolve = a;
    reject = b;
  });
  return { promise, resolve, reject };
};
for (const stage of ["permission", "worklet", "resume"])
  for (const rejected of [false, true]) {
    test(`DDK recording cancellation ${stage} ${rejected ? "reject" : "resolve"} preserves restart`, async () => {
      const originals = Object.fromEntries(
        ["navigator", "window", "AudioContext", "AudioWorkletNode"].map((k) => [
          k,
          Object.getOwnPropertyDescriptor(globalThis, k),
        ]),
      );
      const gate = deferred(),
        tracks = [],
        contexts = [];
      let calls = 0;
      const stream = () => {
        const t = {
          stopped: false,
          stop() {
            this.stopped = true;
          },
          getSettings: () => ({}),
          getConstraints: () => ({}),
        };
        tracks.push(t);
        return { getTracks: () => [t], getAudioTracks: () => [t] };
      };
      class Context {
        constructor() {
          this.sampleRate = 48000;
          this.state = "suspended";
          const first = contexts.length === 0;
          this.audioWorklet = {
            addModule: () =>
              first && stage === "worklet" ? gate.promise : Promise.resolve(),
          };
          this.resume = () =>
            first && stage === "resume" ? gate.promise : Promise.resolve();
          contexts.push(this);
        }
        createMediaStreamSource() {
          return { connect() {}, disconnect() {} };
        }
        async close() {
          this.state = "closed";
        }
      }
      class Node {
        constructor() {
          this.port = {};
        }
        connect() {}
        disconnect() {}
      }
      try {
        for (const [k, v] of Object.entries({
          navigator: {
            mediaDevices: {
              getUserMedia: () =>
                ++calls === 1 && stage === "permission"
                  ? gate.promise
                  : Promise.resolve(stream()),
            },
          },
          window: { AudioWorkletNode: Node },
          AudioContext: Context,
          AudioWorkletNode: Node,
        }))
          Object.defineProperty(globalThis, k, {
            value: v,
            configurable: true,
          });
        const rec = new DdkRecorder(() => {}),
          first = rec.start();
        await new Promise((r) => setImmediate(r));
        assert.equal(await rec.stop(), null);
        assert.equal(await rec.start(), true);
        if (rejected) gate.reject(Error("old"));
        else gate.resolve(stage === "permission" ? stream() : undefined);
        assert.equal(await first, false);
        assert.equal(tracks.filter((t) => !t.stopped).length, 1);
        assert.equal(contexts.filter((c) => c.state !== "closed").length, 1);
        await rec.stop();
        assert.ok(tracks.every((t) => t.stopped));
        assert.ok(contexts.every((c) => c.state === "closed"));
      } finally {
        for (const [k, d] of Object.entries(originals)) {
          if (d) Object.defineProperty(globalThis, k, d);
          else delete globalThis[k];
        }
      }
    });
  }
