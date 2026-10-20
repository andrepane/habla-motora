// Display/state helpers only: no acoustic inference, corrections or smoothing.
const clone = (x) => structuredClone(x);
export const sourceKey = (source) => source
  ? `${source.provenance.file_sha256}:${source.provenance.context_sha256}` : null;
export const identityKey = (p) => p
  ? [p.config_sha256, p.engine_sha256, p.phrase_config_sha256, p.protocol_version, p.integration_version].join(':') : null;
export class ProsodyState {
  constructor() {
    this.status = 'idle'; this.reason = null; this.result = null;
    this.history = []; this.revision = 0; this.source = null;
  }
  invalidate(reason) {
    if (this.result || this.status === 'processing')
      this.history.push({event: 'invalidated', reason, response: clone(this.result)});
    this.revision++; this.status = 'stale'; this.reason = reason; this.result = null;
    return this.revision;
  }
  begin(source) {
    const revision = this.invalidate('new_execution');
    this.source = source; this.status = 'processing'; this.reason = null;
    return revision;
  }
  accept(result, revision, currentSource) {
    if (revision !== this.revision || currentSource !== this.source) {
      this.history.push({event: 'stale_response', response: clone(result)});
      return false;
    }
    this.result = clone(result); this.status = result.status; this.reason = result.reason;
    this.history.push({event: 'execution', response: clone(result)});
    return true;
  }
  exported(view) {
    return clone({schema_version: 'phrase_prosody_export_v1', integration_version: 'phrase_prosody_integration_v1',
      status: this.status, reason: this.reason, current_response: this.result,
      results_current: ['completed', 'partial', 'not_evaluable'].includes(this.status),
      history: this.history, visualization: view});
  }
}
export function displayTime(seconds, duration, axis) {
  return axis === 'percent' ? seconds / duration * 100 : seconds;
}
export function frameValue(frame, unit) {
  const value = unit === 'st' ? frame.f0_st : frame.f0_hz;
  return frame.defined && Number.isFinite(value) ? value : null;
}
export function segments(frames, unit, hop) {
  const result = []; let run = []; let previous = null;
  for (const f of frames) {
    const value = frameValue(f, unit);
    if (value === null || previous && (f.frame_index !== previous.frame_index + 1 ||
        f.time_relative_s - previous.time_relative_s > hop * 1.01)) {
      if (run.length) result.push(run);
      run = [];
    }
    if (value !== null) run.push({frame: f, value});
    previous = f;
  }
  if (run.length) result.push(run);
  return result;
}
export function edgeRegions(frames, duration, hop) {
  if (!frames.length) return [{start_s: 0, end_s: duration, kind: 'edge'}];
  return [{start_s: 0, end_s: Math.max(0, frames[0].time_relative_s - hop/2), kind: 'edge'},
    {start_s: Math.min(duration, frames.at(-1).time_relative_s + hop/2), end_s: duration, kind: 'edge'}]
    .filter(r => r.end_s > r.start_s);
}
export function nearestFrame(frames, time, hop) {
  if (!frames.length || time < frames[0].time_relative_s-hop/2 || time > frames.at(-1).time_relative_s+hop/2) return null;
  let a = 0, b = frames.length - 1;
  while (a < b) {
    const m = Math.floor((a+b)/2);
    if (frames[m].time_relative_s < time) a = m+1; else b = m;
  }
  return a && Math.abs(frames[a-1].time_relative_s-time) < Math.abs(frames[a].time_relative_s-time) ? frames[a-1] : frames[a];
}
