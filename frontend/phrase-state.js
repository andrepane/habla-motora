// Independent revisions: context changes remove all confirmations; review edits
// preserve the context token but invalidate displayed dependent measurements.
export class AttemptState {
  constructor(id) {
    this.id = id;
    this.revision = 0;
    this.contextResult = null;
    this.result = null;
    this.history = [];
  }
  invalidate(reason, contextChanged = true) {
    this.revision++;
    if (this.result)
      this.history.push({
        event: "result_invalidated",
        reason,
        response: this.result,
      });
    this.result = null;
    if (contextChanged) this.contextResult = null;
    this.history.push({ event: "change", reason, revision: this.revision });
    return this.revision;
  }
  accept(response, revision) {
    if (revision !== this.revision) return false;
    this.contextResult = response;
    this.result = response;
    this.history.push({ event: "response", revision, response });
    return true;
  }
}
export function parseEvents(text) {
  return text
    .split("\n")
    .filter((x) => x.trim())
    .map((line, i) => {
      const at = line.indexOf(":");
      return {
        id: `e${i + 1}`,
        type: (at < 0 ? line : line.slice(0, at)).trim(),
        note: at < 0 ? "" : line.slice(at + 1).trim(),
      };
    });
}
export const changeFields = new Set([
  "file",
  "start",
  "end",
  "selectionConfirmed",
  "modality",
  "phrase",
  "limit",
  "model",
]);
