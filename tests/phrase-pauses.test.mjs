import test from "node:test";
import assert from "node:assert/strict";
import { PauseState, dependencies } from "../frontend/phrase-pauses.js";
for (const reason of [
  "audio",
  "selection",
  "content_review",
  "modality",
  "phrase",
  "attempt",
  "model",
  "protocol",
]) {
  test(`7B source ${reason}: clear confirmation/result and retain evidence history`, () => {
    const s = new PauseState();
    s.intervals = [{ id: "p1", start_sample: 10, end_sample_exclusive: 30 }];
    s.accept({ metrics: { pause_count: { value: 1 } } }, 0);
    s.invalidate(reason, true);
    assert.equal(s.result, null);
    assert.deepEqual(s.intervals, []);
    assert.equal(s.accept({ stale: true }, 0), false);
    assert.equal(
      s.history.find((h) => h.event === "invalidated").intervals[0].id,
      "p1",
    );
  });
}
test("manual interval edit preserves draft, invalidates result and does not affect other attempt", () => {
  const a = new PauseState(),
    b = new PauseState();
  a.intervals = [{ id: "p1" }];
  a.accept({ ok: true }, 0);
  b.accept({ ok: true }, 0);
  a.invalidate("boundary");
  assert.equal(a.result, null);
  assert.equal(a.intervals.length, 1);
  assert.deepEqual(b.result, { ok: true });
});
test("source identity binds review separately from context", () => {
  const source = {
    provenance: {
      file_sha256: "a",
      context_sha256: "b",
      review_sha256: "c",
      config_sha256: "d",
      engine_sha256: "e",
      unrelated: "x",
    },
  };
  assert.equal(Object.keys(dependencies(source)).length, 5);
  assert.equal(dependencies(source).review_sha256, "c");
});
