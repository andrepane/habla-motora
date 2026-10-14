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
