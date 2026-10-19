// Manual 7B.1 layer. Never changes 7A selections, reviews, counts or results.
import { metricText } from "./audio.js";
export class PauseState {
  constructor() {
    this.intervals = [];
    this.result = null;
    this.history = [];
    this.revision = 0;
  }
  invalidate(reason, sourceChanged = false) {
    if (this.result || (sourceChanged && this.intervals.length))
      this.history.push({
        event: "invalidated",
        at: new Date().toISOString(),
        reason,
        response: this.result,
        intervals: structuredClone(this.intervals),
      });
    this.result = null;
    if (sourceChanged) this.intervals = [];
    this.history.push({
      event: "change",
      at: new Date().toISOString(),
      reason,
      revision: ++this.revision,
      intervals: structuredClone(this.intervals),
    });
  }
  accept(result, revision) {
    if (revision !== this.revision) return false;
    this.result = result;
    this.history.push({
      event: "response",
      at: new Date().toISOString(),
      result,
    });
    return true;
  }
}
const keys = [
  "file_sha256",
  "context_sha256",
  "review_sha256",
  "config_sha256",
  "engine_sha256",
];
export function dependencies(source) {
  return Object.fromEntries(keys.map((k) => [k, source.provenance[k]]));
}
export function mountPauses(s, redraw) {
  const state = new PauseState();
  const panel = document.createElement("fieldset");
  panel.className = "pausePanel";
  panel.innerHTML = `<legend>7B.1 · Pausas revisadas manualmente</legend>
  <p>Sin detector automático. Pausa: interrupción interna confirmada ≥250 ms; incluye respiración cuando corresponda. «Eh», fragmentos, reinicios y oclusiones permanecen en el tiempo operacional. No es tiempo de fonación ni articulación pura.</p>
  <p>Primero confirma la selección y envía la revisión de contenido de 7A. Revisa toda la selección escuchando el contexto. Si hay duda intrapalabra, marca uncertain. Una interferencia no verbal impide publicar el resumen global.</p>
  <label><input type="checkbox" data-p="editing"> Anotar intervalos sobre la onda de arriba (el arrastre no cambia la selección 7A)</label>
  <div class="grid"><label>Inicio absoluto <input data-p="start" type="number" min="0" step="1"></label><label>Fin exclusivo <input data-p="end" type="number" min="1" step="1"></label></div>
  <button type="button" data-p="cursorStart">Inicio en cursor</button><button type="button" data-p="cursorEnd">Fin en cursor</button><button type="button" data-p="add">Añadir intervalo</button>
  <p>Edición por muestras en cada intervalo; escucha con 250 ms de contexto a cada lado. Ampliar cambia solo la vista. Clasificaciones: pause (pausa), below_threshold (&lt;250 ms), consonantal_closure (oclusión), uncertain (dudoso), other_nonverbal (interferencia).</p>
  <div data-p="rows"></div>
  <label>Estado sin confirmar <select data-p="status"><option value="draft">Borrador</option><option value="not_evaluable">No evaluable</option></select></label>
  <label>Nota global / motivo de no evaluable <textarea data-p="note"></textarea></label>
  <label><input data-p="confirmed" type="checkbox"> He revisado toda la selección, he anotado todas las pausas del protocolo y no quedan regiones inciertas ni interferencias sin resolver</label>
  <button data-p="calculate" type="button">Calcular 7B.1 con revisión temporal</button>
  <p data-p="state" role="status">Revisión temporal pendiente.</p><div data-p="metrics" class="grid"></div>
  <details><summary>Auditoría 7B.1 e historial</summary><pre data-p="audit"></pre></details>`;
  s.section.append(panel);
  const q = (key) => panel.querySelector(`[data-p="${key}"]`);
  let controller,
    nextId = 1;
  let boundDependencies = null;
  const exported = () => ({
    protocol_version: "phrase_pause_review_v1",
    current_response: state.result,
    temporal_draft: draft(),
    history: state.history,
    revision: state.revision,
    results_current: !!state.result,
  });
  function draft() {
    const source = s.state.result;
    return {
      protocol_version: "phrase_pause_review_v1",
      source_dependencies: source ? dependencies(source) : null,
      status: q("confirmed").checked ? "confirmed" : q("status").value,
      reviewed_all: q("confirmed").checked,
      note: q("note").value,
      intervals: structuredClone(state.intervals),
    };
  }
  function audit() {
    q("audit").textContent = JSON.stringify(exported(), null, 2);
  }
  function invalidate(reason, sourceChanged = false) {
    controller?.abort();
    if (sourceChanged)
      state.history.push({
        event: "source_changed",
        at: new Date().toISOString(),
        previous_draft: draft(),
        bound_dependencies: boundDependencies,
      });
    state.invalidate(reason, sourceChanged);
    if (sourceChanged) boundDependencies = null;
    q("confirmed").checked = false;
    if (sourceChanged) {
      q("status").value = "draft";
      q("note").value = "";
      rows();
      redraw(s);
    }
    q("metrics").replaceChildren();
    q("state").textContent = "7B.1 invalidado. Revisa y confirma de nuevo.";
    audit();
  }
  function edit(reason) {
    invalidate(reason);
    state.history.push({
      event: "draft_edit",
      at: new Date().toISOString(),
      draft: draft(),
    });
    audit();
    redraw(s);
  }
  q("status").oninput = () => edit("temporal_status");
  q("note").oninput = () => edit("temporal_note");
  q("confirmed").onchange = () => {
    const checked = q("confirmed").checked;
    invalidate("temporal_confirmation");
    q("confirmed").checked = checked;
    if (checked) q("status").value = "draft";
    state.history.push({
      event: "confirmation",
      at: new Date().toISOString(),
      draft: draft(),
    });
    audit();
  };
  function numeric(input) {
    return input.value === "" ? null : Number(input.value);
  }
  for (const [button, input] of [
    ["cursorStart", "start"],
    ["cursorEnd", "end"],
  ])
    q(button).onclick = () => {
      if (s.wav)
        q(input).value = Math.round(s.q(".audio").currentTime * s.wav.rate);
    };
  q("add").onclick = () => {
    if (!s.wav) return;
    const a = numeric(q("start")),
      b = numeric(q("end"));
    if (!Number.isInteger(a) || !Number.isInteger(b) || a >= b) {
      q("state").textContent = "Error: introduce índices enteros inicio < fin.";
      return;
    }
    state.intervals.push({
      id: `p${nextId++}`,
      start_sample: a,
      end_sample_exclusive: b,
      classification: "uncertain",
      breath_present: "uncertain",
      within_word: false,
      nonarticulatory_confirmed: false,
      note: "",
    });
    edit("interval_added");
    rows();
  };
  function rows() {
    q("rows").replaceChildren();
    for (const event of state.intervals) {
      const row = document.createElement("fieldset");
      row.dataset.intervalId = event.id;
      const legend = document.createElement("legend");
      legend.textContent = event.id;
      row.append(legend);
      const number = (key, label) => {
        const l = document.createElement("label");
        l.textContent = label;
        const input = document.createElement("input");
        input.type = "number";
        input.step = "1";
        input.dataset.key = key;
        input.value = event[key];
        input.oninput = () => {
          event[key] = numeric(input);
          edit(key);
        };
        l.append(input);
        row.append(l);
      };
      number("start_sample", "Inicio absoluto");
      number("end_sample_exclusive", "Fin exclusivo");
      for (const [key, label, values] of [
        [
          "classification",
          "Clasificación",
          [
            "pause",
            "below_threshold",
            "consonantal_closure",
            "uncertain",
            "other_nonverbal",
          ],
        ],
        ["breath_present", "Respiración", ["yes", "no", "uncertain"]],
      ]) {
        const l = document.createElement("label");
        l.textContent = label;
        const select = document.createElement("select");
        select.dataset.key = key;
        for (const v of values) {
          const option = document.createElement("option");
          option.value = option.textContent = v;
          select.append(option);
        }
        select.value = event[key];
        select.oninput = () => {
          event[key] = select.value;
          edit(key);
        };
        l.append(select);
        row.append(l);
      }
      for (const [key, label] of [
        ["within_word", "Interrupción dentro de una palabra"],
        [
          "nonarticulatory_confirmed",
          "Confirmo interrupción NO articulatoria, claramente separada del gesto consonántico y del resto de la producción",
        ],
      ]) {
        const l = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.dataset.key = key;
        input.checked = event[key];
        input.oninput = () => {
          event[key] = input.checked;
          edit(key);
        };
        l.append(input, document.createTextNode(label));
        row.append(l);
      }
      const note = document.createElement("textarea");
      note.dataset.key = "note";
      note.placeholder = "Contexto y justificación manual";
      note.setAttribute("aria-label", `Nota ${event.id}`);
      note.value = event.note;
      note.oninput = () => {
        event.note = note.value;
        edit("interval_note");
      };
      row.append(note);
      for (const [label, action] of [
        [
          "Ampliar intervalo",
          () => {
            if (
              !s.wav ||
              !Number.isInteger(event.start_sample) ||
              !Number.isInteger(event.end_sample_exclusive) ||
              event.start_sample < 0 ||
              event.end_sample_exclusive > s.wav.samples.length ||
              event.start_sample >= event.end_sample_exclusive
            )
              return;
            s.viewStart = event.start_sample;
            s.viewEnd = event.end_sample_exclusive;
            redraw(s);
          },
        ],
        [
          "Escuchar con contexto",
          () => {
            if (
              !s.wav ||
              !Number.isInteger(event.start_sample) ||
              !Number.isInteger(event.end_sample_exclusive)
            )
              return;
            const audio = s.q(".audio");
            const a = Math.max(0, event.start_sample / s.wav.rate - 0.25),
              b = Math.min(
                s.wav.duration,
                event.end_sample_exclusive / s.wav.rate + 0.25,
              );
            audio.currentTime = a;
            audio.ontimeupdate = () => {
              if (audio.currentTime >= b) {
                audio.pause();
                audio.ontimeupdate = null;
              }
            };
            audio.play().catch((e) => {
              q("state").textContent = `Error: ${e.message}`;
            });
          },
        ],
        [
          "Eliminar",
          () => {
            state.intervals = state.intervals.filter((e) => e.id !== event.id);
            edit("interval_deleted");
            rows();
          },
        ],
      ]) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = label;
        b.onclick = action;
        row.append(b);
      }
      q("rows").append(row);
    }
  }
  function overlay() {
    s.q(".wave .pauseOverlay")?.remove();
    if (!s.wav) return;
    const ns = "http://www.w3.org/2000/svg";
    const group = document.createElementNS(ns, "g");
    group.classList.add("pauseOverlay");
    group.style.pointerEvents = "none";
    const colors = {
      pause: "#d89717",
      below_threshold: "#499bd1",
      consonantal_closure: "#8265ab",
      uncertain: "#d94949",
      other_nonverbal: "#555",
    };
    for (const e of state.intervals) {
      if (
        !Number.isInteger(e.start_sample) ||
        !Number.isInteger(e.end_sample_exclusive)
      )
        continue;
      const a = Math.max(s.viewStart, e.start_sample),
        b = Math.min(s.viewEnd, e.end_sample_exclusive);
      if (a >= b) continue;
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute(
        "x",
        (800 * (a - s.viewStart)) / (s.viewEnd - s.viewStart),
      );
      rect.setAttribute("width", (800 * (b - a)) / (s.viewEnd - s.viewStart));
      rect.setAttribute("y", 0);
      rect.setAttribute("height", 180);
      rect.setAttribute("fill", colors[e.classification]);
      rect.setAttribute("opacity", ".3");
      const title = document.createElementNS(ns, "title");
      title.textContent = `${e.id}: ${e.classification} [${e.start_sample}, ${e.end_sample_exclusive})`;
      rect.append(title);
      group.append(rect);
    }
    s.q(".wave").append(group);
  }
  q("calculate").onclick = async () => {
    const source = s.state.result;
    if (!s.file || !source) {
      q("state").textContent =
        "Primero envía la selección y revisión actual de 7A.";
      return;
    }
    controller?.abort();
    controller = new AbortController();
    const revision = state.revision;
    const form = new FormData();
    form.append("file", s.file);
    form.append("context_json", JSON.stringify(source.context));
    if (source.review)
      form.append("review_json", JSON.stringify(source.review));
    form.append("expected_file_sha256", source.provenance.file_sha256);
    form.append("temporal_json", JSON.stringify(draft()));
    q("state").textContent = "Calculando 7B.1…";
    try {
      const response = await fetch("/phrase-pause-analysis", {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok)
        throw Error(
          typeof result.detail === "string"
            ? result.detail
            : JSON.stringify(result.detail),
        );
      if (!state.accept(result, revision)) return;
      q("state").textContent =
        `7B.1 · Revisión: ${result.stages.temporal_review} · Cálculo: ${result.stages.calculation}`;
      q("metrics").replaceChildren();
      const labels = {
        pause_duration_s: "Pausas revisadas (s)",
        operational_speech_time_s: "Tiempo de habla operacional (s)",
        pause_percent: "Porcentaje de pausa",
        pause_count: "Número de pausas",
        pause_mean_duration_s: "Duración media (s)",
        pause_median_duration_s: "Duración mediana (s)",
        reviewed_syllable_articulation_rate:
          "Sílabas/s · articulatoria operacional",
        reviewed_word_articulation_rate:
          "Palabras/min · articulatoria operacional",
      };
      for (const [key, m] of Object.entries(result.metrics)) {
        const div = document.createElement("div");
        div.className = "metric";
        const label = document.createElement("span"),
          value = document.createElement("strong"),
          note = document.createElement("small");
        label.textContent = labels[key];
        value.textContent = metricText(m);
        note.textContent = m.reason || m.unit;
        div.append(label, value, note);
        q("metrics").append(div);
      }
      audit();
    } catch (e) {
      if (e.name !== "AbortError" && revision === state.revision) {
        state.result = null;
        q("metrics").replaceChildren();
        q("state").textContent = `Error: ${e.message}`;
        state.history.push({
          event: "error",
          at: new Date().toISOString(),
          message: e.message,
        });
        audit();
      }
    }
  };
  audit();
  return {
    invalidate,
    sourceUpdated() {
      const current = dependencies(s.state.result);
      if (
        boundDependencies &&
        JSON.stringify(boundDependencies) !== JSON.stringify(current)
      )
        invalidate("7A:response_replaced", true);
      boundDependencies = current;
    },
    overlay,
    exported,
    get editing() {
      return q("editing").checked;
    },
    drag(a, b) {
      q("start").value = Math.min(a, b);
      q("end").value = Math.max(a, b);
      q("state").textContent =
        "Límites de intervalo preparados. Añade y clasifica manualmente; 7A no ha cambiado.";
    },
  };
}
