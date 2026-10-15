import test from "node:test";
import assert from "node:assert/strict";
import { AttemptState, parseEvents } from "../frontend/phrase-state.js";
for (const reason of [
  "audio",
  "start",
  "end",
  "phrase",
  "modality",
  "model",
  "selectionConfirmed",
]) {
  test(`${reason} invalidates context/rates and rejects stale response`, () => {
    const s = new AttemptState(1);
    s.accept({ rates: { reference_word_rate: { value: 105 } } }, 0);
    s.invalidate(reason, true);
    assert.equal(s.result, null);
    assert.equal(s.contextResult, null);
    assert.equal(s.accept({ old: true }, 0), false);
    assert.ok(s.history.some((h) => h.event === "result_invalidated"));
  });
}
test("review edit invalidates rates, preserves context and does not affect other attempt", () => {
  const a = new AttemptState(1),
    b = new AttemptState(2);
  const r = { provenance: { context_sha256: "abc" } };
  a.accept(r, 0);
  b.accept(r, 0);
  a.invalidate("words", false);
  assert.equal(a.result, null);
  assert.deepEqual(a.contextResult, r);
  assert.deepEqual(b.result, r);
  assert.equal(a.accept(r, 0), false);
});
test("manual annotations do not turn into inferred counts", () => {
  assert.deepEqual(parseEvents("omission: pequeñas\nrestart: segundo inicio"), [
    { id: "e1", type: "omission", note: "pequeñas" },
    { id: "e2", type: "restart", note: "segundo inicio" },
  ]);
});
