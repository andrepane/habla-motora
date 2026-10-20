import test from "node:test";
import assert from "node:assert/strict";
import { CandidateState } from "../frontend/phrase-candidate-state.js";
const candidate = {
  candidate_id: "c1",
  start_sample: 10,
  end_sample_exclusive: 100,
};
const run = {
  status: "completed",
  automatic_candidates: [candidate],
  original_execution: { run_id: "r1" },
};
const manual = { temporal_draft: { intervals: [] }, current_response: null };
function ready() {
  const s = new CandidateState();
  s.complete(run, s.begin());
  return s;
}
test("original proposals immutable and separate from decisions", () => {
  const s = ready();
  assert.throws(() => {
    s.run.automatic_candidates[0].start_sample = 20;
  });
  s.decide("c1", "rejected");
  assert.deepEqual(s.run.automatic_candidates, [candidate]);
  assert.deepEqual(s.exported(manual).manual_annotations, []);
});
test("copy preserves automatic and edited limits and link", () => {
  const s = ready();
  s.decide(
    "c1",
    "copied",
    { start_sample: 20, end_sample_exclusive: 90 },
    "p1",
  );
  assert.equal(s.links[0].original_bounds.start_sample, 10);
  assert.equal(s.links[0].edited_bounds.start_sample, 20);
  assert.equal(s.links[0].manual_annotation_id, "p1");
  assert.throws(() => s.decide("c1", "pause"));
});
for (const reason of ["audio", "selection", "modality", "attempt", "context"])
  test(`invalidate ${reason} archives without reuse`, () => {
    const s = ready();
    s.decide("c1", "rejected");
    s.invalidate(reason);
    assert.equal(s.run, null);
    assert.equal(s.decisions.length, 0);
    assert.equal(s.history.at(-1).candidate_decisions[0].action, "rejected");
  });
test("late response cannot replace current run", () => {
  const s = new CandidateState();
  const rev = s.begin();
  s.invalidate("selection");
  assert.equal(s.complete(run, rev), false);
  assert.equal(s.run, null);
});
test("zero candidates never synthesizes manual zero", () => {
  const s = new CandidateState();
  s.complete({ ...run, automatic_candidates: [] }, s.begin());
  assert.equal(s.exported(manual).manual_final_result, null);
});
for (const status of ["failed", "not_evaluable", "stale"])
  test(`${status} keeps null candidates`, () => {
    const s = new CandidateState();
    s.complete({ status, automatic_candidates: null }, s.begin());
    assert.equal(s.exported(manual).automatic_candidates, null);
  });
test("regeneration archives links and leaves supplied manual evidence intact", () => {
  const s = ready();
  s.decide(
    "c1",
    "copied",
    { start_sample: 10, end_sample_exclusive: 100 },
    "p1",
  );
  const m = {
    temporal_draft: { intervals: [{ id: "p1", classification: "uncertain" }] },
    current_response: null,
  };
  s.begin();
  assert.equal(s.exported(m).manual_annotations[0].classification, "uncertain");
  assert.equal(
    s.history.at(-1).candidate_manual_links[0].manual_annotation_id,
    "p1",
  );
});
test("attempt instances independent", () => {
  const a = ready(),
    b = ready();
  a.decide("c1", "rejected");
  assert.equal(b.decisions.length, 0);
});
