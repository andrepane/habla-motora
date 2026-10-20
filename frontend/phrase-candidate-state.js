// Automatic evidence is immutable. Decisions and manual links are separate records.
const clone = (x) => structuredClone(x);
function freeze(x) {
  if (x && typeof x === "object") {
    Object.values(x).forEach(freeze);
    Object.freeze(x);
  }
  return x;
}
export class CandidateState {
  constructor() {
    this.run = null;
    this.decisions = [];
    this.links = [];
    this.history = [];
    this.revision = 0;
    this.status = "idle";
  }
  invalidate(reason) {
    if (this.run || this.status === "processing")
      this.history.push({
        event: "invalidated",
        reason,
        status: "stale",
        at: new Date().toISOString(),
        execution: clone(this.run),
        candidate_decisions: clone(this.decisions),
        candidate_manual_links: clone(this.links),
      });
    this.run = null;
    this.decisions = [];
    this.links = [];
    this.status = "stale";
    return ++this.revision;
  }
  begin(dependencies = null) {
    const revision = this.invalidate("regenerated");
    this.status = "processing";
    if (dependencies)
      this.history.push({
        event: "execution_requested",
        at: new Date().toISOString(),
        revision,
        dependencies: clone(dependencies),
      });
    return revision;
  }
  complete(run, revision) {
    if (revision !== this.revision) {
      this.history.push({ event: "stale_response", execution: clone(run) });
      return false;
    }
    this.run = freeze(clone(run));
    this.status = run.status;
    this.history.push({
      event: "execution",
      at: new Date().toISOString(),
      execution: clone(run),
    });
    return true;
  }
  candidate(id) {
    return this.run?.automatic_candidates?.find((c) => c.candidate_id === id);
  }
  decided(id) {
    return this.decisions.some((d) => d.candidate_id === id);
  }
  decide(id, action, bounds = null, manualId = null) {
    const c = this.candidate(id);
    if (
      !c ||
      this.status !== "completed" ||
      this.decided(id) ||
      !["rejected", "copied"].includes(action)
    )
      throw Error("Propuesta no disponible.");
    if (
      action === "copied" &&
      (!manualId ||
        !bounds ||
        !Number.isInteger(bounds.start_sample) ||
        !Number.isInteger(bounds.end_sample_exclusive) ||
        bounds.start_sample >= bounds.end_sample_exclusive)
    )
      throw Error("Límites no válidos.");
    const decision = {
      candidate_id: id,
      run_id: this.run.original_execution.run_id,
      action,
      at: new Date().toISOString(),
      original_bounds: {
        start_sample: c.start_sample,
        end_sample_exclusive: c.end_sample_exclusive,
      },
      edited_bounds: bounds ? clone(bounds) : null,
    };
    this.decisions.push(decision);
    if (action === "copied")
      this.links.push({ ...clone(decision), manual_annotation_id: manualId });
  }
  exported(manual) {
    return clone({
      schema_version: "phrase_candidate_review_v1",
      status: this.status,
      automatic_execution: this.run,
      automatic_candidates: this.run?.automatic_candidates ?? null,
      candidate_decisions: this.decisions,
      candidate_manual_links: this.links,
      manual_annotations: manual.temporal_draft.intervals,
      manual_final_result: manual.current_response,
      history: this.history,
    });
  }
}
