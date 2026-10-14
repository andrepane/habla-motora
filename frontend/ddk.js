import { parseWav, metricText } from "./audio.js";
import { DdkRecorder } from "./ddk-recorder.js";
const $ = (id) => document.getElementById(id);
const state = {
  file: null,
  audio: null,
  url: null,
  result: null,
  events: [],
  ops: [],
  capture: null,
  generation: 0,
  controller: null,
  busy: false,
  recording: false,
};
let playbackTimer, drag;
const say = (text, error = false) => {
  $("status").textContent = text;
  $("status").className = error ? "error" : "";
};
const elem = (tag, text) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  return n;
};
const explanations = {
  no_evidence: "Sin evidencia suficiente",
  no_groups: "Sin grupos completos",
  anchor_not_requested: "Anclaje no solicitado",
  insufficient_intervals: "Intervalos insuficientes",
  no_intervals: "Sin intervalos",
  detector_failed: "Detector fallido",
  boundary_incomplete: "Borde incompleto",
  below_threshold: "Bajo el umbral",
  insufficient_dip: "Contraste insuficiente",
  minimum_separation: "Separación insuficiente",
  ACOUSTIC_CANDIDATES_NOT_PHONETIC_RECOGNITION:
    "Son candidatos acústicos: no se ha reconocido la identidad de las sílabas.",
  POSSIBLE_DIGITAL_CLIPPING:
    "Posible saturación digital. Revisa el audio y los marcadores.",
};
const explain = (reason) => explanations[reason] || reason;
const selected = () => {
  const a = Number($("start").value),
    b = Number($("end").value);
  return (
    state.audio &&
    Number.isFinite(a) &&
    Number.isFinite(b) &&
    a >= 0 &&
    b <= state.audio.duration &&
    b - a >= 0.02
  );
};
function invalidate() {
  state.generation++;
  state.controller?.abort();
  state.controller = null;
  state.busy = false;
  state.result = null;
  state.events = [];
  state.ops = [];
  for (const id of ["results", "reviewSection", "exportSection"])
    $(id).hidden = true;
  $("confirmed").checked = $("absence").checked = false;
  say("");
  update();
}
function update() {
  $("analyze").disabled = state.recording || state.busy || !selected();
  $("selection").textContent = selected()
    ? `Tramo completo: ${Number($("start").value).toFixed(3)}–${Number($("end").value).toFixed(3)} s · ${(Number($("end").value) - Number($("start").value)).toFixed(3)} s`
    : "Selecciona un tramo válido de al menos 20 ms.";
  drawWave();
}
function clear() {
  invalidate();
  clearTimeout(playbackTimer);
  $("player").pause();
  if (state.url) URL.revokeObjectURL(state.url);
  Object.assign(state, { file: null, audio: null, url: null, capture: null });
  $("player").removeAttribute("src");
  $("player").hidden = $("downloadAudio").hidden = true;
  $("file").value = "";
  $("start").value = $("end").value = "";
  $("start").disabled = $("end").disabled = true;
  $("audioInfo").textContent = "Todavía no hay audio.";
  $("captureInfo").textContent = "Sin grabación.";
  update();
}
async function load(file, capture = null) {
  clear();
  const gen = state.generation;
  try {
    if (file.size > 4000000) throw Error("DDK admite hasta 4.000.000 bytes.");
    const buffer = await file.arrayBuffer();
    if (gen !== state.generation) return;
    const audio = parseWav(buffer);
    if (audio.duration > 15) throw Error("DDK admite hasta 15 segundos.");
    Object.assign(state, {
      file,
      audio,
      capture,
      url: URL.createObjectURL(file),
    });
    $("player").src = state.url;
    $("player").hidden = false;
    $("audioInfo").textContent =
      `${file.name} · ${audio.duration.toFixed(3)} s · ${audio.rate} Hz · PCM${audio.bits}`;
    $("start").disabled = $("end").disabled = false;
    $("start").value = 0;
    $("end").value = audio.duration;
    $("start").max = $("end").max = audio.duration;
    $("downloadAudio").href = state.url;
    $("downloadAudio").download = "ddk.wav";
    $("downloadAudio").hidden = !capture;
    $("captureInfo").textContent = capture
      ? JSON.stringify(capture, null, 2)
      : "Archivo subido: sin metadatos de captura.";
    update();
  } catch (e) {
    if (gen === state.generation) say(e.message, true);
  }
}
$("file").onchange = (e) => {
  if (e.target.files[0]) load(e.target.files[0]);
};
$("reset").onclick = clear;
for (const id of ["start", "end"]) $(id).oninput = invalidate;
function drawWave() {
  const canvas = $("wave"),
    w = canvas.clientWidth || 800,
    h = 160;
  canvas.width = w * devicePixelRatio;
  canvas.height = h * devicePixelRatio;
  const c = canvas.getContext("2d");
  c.scale(devicePixelRatio, devicePixelRatio);
  c.clearRect(0, 0, w, h);
  if (!state.audio) return;
  const { samples, duration } = state.audio,
    x = (t) => (t / duration) * w;
  c.fillStyle = "#c6e9f0";
  c.fillRect(
    x(Number($("start").value)),
    0,
    x(Number($("end").value) - Number($("start").value)),
    h,
  );
  c.strokeStyle = "#52858e";
  c.beginPath();
  for (let i = 0; i < w; i++) {
    let low = 1,
      high = -1;
    for (
      let j = Math.floor((i * samples.length) / w);
      j <
      Math.min(
        samples.length,
        Math.max(1, Math.floor(((i + 1) * samples.length) / w)),
      );
      j++
    ) {
      low = Math.min(low, samples[j]);
      high = Math.max(high, samples[j]);
    }
    c.moveTo(i, 80 - low * 65);
    c.lineTo(i, 80 - high * 65);
  }
  c.stroke();
  c.strokeStyle = "#176c78";
  for (const id of ["start", "end"]) {
    c.beginPath();
    c.moveTo(x(Number($(id).value)), 0);
    c.lineTo(x(Number($(id).value)), h);
    c.stroke();
  }
}
$("wave").onpointerdown = (e) => {
  if (!state.audio || state.recording) return;
  const r = $("wave").getBoundingClientRect(),
    t = ((e.clientX - r.left) / r.width) * state.audio.duration;
  drag =
    Math.abs(t - Number($("start").value)) <
    Math.abs(t - Number($("end").value))
      ? "start"
      : "end";
  $("wave").setPointerCapture(e.pointerId);
  move(e);
};
function move(e) {
  if (!drag) return;
  const r = $("wave").getBoundingClientRect(),
    t = Math.max(
      0,
      Math.min(
        state.audio.duration,
        ((e.clientX - r.left) / r.width) * state.audio.duration,
      ),
    );
  $(drag).value = t === state.audio.duration ? String(t) : t.toFixed(3);
  invalidate();
}
$("wave").onpointermove = move;
$("wave").onpointerup = $("wave").onpointercancel = () => {
  drag = null;
};
window.addEventListener("resize", drawWave);
function captureButtons(active) {
  state.recording = active;
  $("record").disabled = active;
  $("stop").disabled = !active;
  $("file").disabled = $("reset").disabled = active;
  $("start").disabled = $("end").disabled = active || !state.audio;
  update();
}
const recorder = new DdkRecorder((seconds) => {
  say(`Grabando · ${seconds.toFixed(1)} s`);
  if (seconds >= 15) stop();
});
$("record").onclick = async () => {
  clear();
  captureButtons(true);
  say("Preparando micrófono…");
  try {
    if (await recorder.start()) say("Grabando /pa-ta-ka/…");
  } catch (e) {
    captureButtons(false);
    say(e.message, true);
  }
};
async function stop() {
  if (!state.recording) return;
  $("stop").disabled = true;
  try {
    const captured = await recorder.stop();
    captureButtons(false);
    if (captured) await load(captured.file, captured.capture);
    else say("No se han capturado muestras. Repite el intento.", true);
  } catch (e) {
    captureButtons(false);
    say(e.message, true);
  }
}
$("stop").onclick = stop;
async function request(mode = "automatic") {
  if (!selected() || !state.file || state.busy) return;
  const gen = ++state.generation;
  state.controller?.abort();
  const controller = new AbortController();
  state.controller = controller;
  state.busy = true;
  update();
  say("Procesando DDK…");
  const form = new FormData();
  form.append("file", state.file);
  form.append("emission_start_s", $("start").value);
  form.append("emission_end_s", $("end").value);
  if (mode !== "automatic" && $("anchor").value)
    form.append("anchor_id", $("anchor").value);
  if (mode === "review") {
    form.append("expected_file_sha256", state.result.provenance.file_sha256);
    form.append(
      "review_json",
      JSON.stringify({
        operations: state.ops,
        confirmed: $("confirmed").checked,
        confirm_absence: $("absence").checked,
      }),
    );
  }
  try {
    const response = await fetch("/ddk-analysis", {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    const result = await response.json();
    if (gen !== state.generation) return;
    if (!response.ok)
      throw Error(
        typeof result.detail === "string"
          ? result.detail
          : "El servidor no pudo completar DDK.",
      );
    state.result = result;
    if (mode === "automatic" || mode === "group") {
      state.ops = [];
      state.events = structuredClone(
        result.automatic_original.detection.events,
      );
      $("confirmed").checked = $("absence").checked = false;
    }
    if (mode === "review")
      state.events = structuredClone(result.reviewed_result.events);
    render();
    say(
      result.status === "partial"
        ? "Ejecución parcial: revisa los estados y las medidas no calculables."
        : "Procesamiento completado. Revisión humana y cierre 6A pendientes.",
    );
  } catch (e) {
    if (gen === state.generation && e.name !== "AbortError")
      say(e.message, true);
  } finally {
    if (gen === state.generation) {
      state.busy = false;
      state.controller = null;
      update();
    }
  }
}
$("analyze").onclick = () => request();
$("group").onclick = () => request("group");
$("calculateReview").onclick = () => request("review");
$("anchor").onchange = () => {
  if (state.result) {
    state.generation++;
    state.controller?.abort();
    state.busy = false;
    state.result = null;
    state.events = [];
    state.ops = [];
    $("confirmed").checked = $("absence").checked = false;
    for (const id of ["reviewSection", "exportSection"]) $(id).hidden = true;
    $("automaticCards").replaceChildren();
    $("groupInfo").textContent =
      "Anclaje cambiado: recalcula la salida automática. Se descartarán las modificaciones manuales.";
    update();
  }
};
// An anchor change keeps the file and requested selector but invalidates all derived data.
function edit(op) {
  state.generation++;
  state.controller?.abort();
  state.busy = false;
  state.ops.push(op);
  $("confirmed").checked = $("absence").checked = false;
  state.result.reviewed_result = null;
  state.result.manual_modifications = null;
  renderEditor();
  renderAudit();
  update();
}
$("addEvent").onclick = () => {
  if (!state.result) return;
  const t = Number($("addTime").value),
    r = state.result.analysis_interval;
  if (
    !$("addTime").value ||
    !Number.isFinite(t) ||
    t < r.start_s ||
    t >= r.end_s ||
    state.events.some((e) => e.time_s === t)
  ) {
    say("Tiempo nuevo inválido o coincidente.", true);
    return;
  }
  const id = "m" + crypto.randomUUID();
  state.events.push({ id, time_s: t, label: "unknown", restart: false });
  state.events.sort((a, b) => a.time_s - b.time_s);
  edit({ action: "add", id, time_s: t });
};
$("discardReview").onclick = () => {
  if (!state.result) return;
  state.generation++;
  state.controller?.abort();
  state.busy = false;
  state.events = structuredClone(
    state.result.automatic_original.detection.events,
  );
  state.ops = [];
  state.result.reviewed_result = null;
  state.result.manual_modifications = null;
  $("confirmed").checked = $("absence").checked = false;
  renderEditor();
  renderAudit();
  update();
};
for (const id of ["confirmed", "absence"])
  $(id).onchange = () => {
    if (state.result) {
      state.generation++;
      state.controller?.abort();
      state.busy = false;
      state.result.reviewed_result = null;
      state.result.manual_modifications = null;
      renderEditor(false);
      renderAudit();
      update();
    }
  };
function cards(target, metrics, reviewed = false) {
  $(target).replaceChildren();
  const entries = [
    [
      reviewed ? "Sílabas revisadas" : "Núcleos candidatos",
      metrics.event_count,
      "",
    ],
    [
      reviewed ? "Sílabas revisadas/s" : "Tasa automática estimada",
      metrics.event_rate_per_s,
      reviewed ? "sílabas/s" : "núcleos/s",
    ],
    [
      reviewed ? "Ciclos revisados" : "Tríadas candidatas",
      metrics.group_count,
      "",
    ],
    [
      reviewed ? "Ciclos revisados/s" : "Tasa de tríadas estimada",
      metrics.group_rate_per_s,
      "/s",
    ],
    ["DT entre acontecimientos", metrics.event_regularity.sd_ms, "ms"],
    ["CV entre acontecimientos", metrics.event_regularity.cv_percent, "%"],
    ["DT entre agrupaciones", metrics.group_regularity.sd_ms, "ms"],
    ["CV entre agrupaciones", metrics.group_regularity.cv_percent, "%"],
  ];
  for (const [label, metric, unit] of entries) {
    const card = elem("div");
    card.className = "card";
    card.append(elem("h3", label));
    const value = elem("div", metricText(metric));
    value.className = "value";
    card.append(
      value,
      elem("small", metric.value === null ? explain(metric.reason) : unit),
    );
    $(target).append(card);
  }
}
function play(t) {
  clearTimeout(playbackTimer);
  $("player").currentTime = Math.max(0, t - 0.2);
  $("player")
    .play()
    .catch(() => say("No se pudo reproducir el audio.", true));
  playbackTimer = setTimeout(() => $("player").pause(), 650);
}
function render() {
  for (const id of ["results", "reviewSection", "exportSection"])
    $(id).hidden = false;
  const r = state.result,
    a = r.automatic_original;
  $("stageState").textContent = Object.entries(r.stages)
    .map(
      ([k, v]) => `${k}: ${v.status}${v.reason ? " (" + v.reason + ")" : ""}`,
    )
    .join(" · ");
  cards("automaticCards", a.metrics);
  const anchor = $("anchor");
  anchor.replaceChildren(new Option("Sin anclaje", ""));
  for (const e of a.detection.events)
    anchor.add(new Option(`${e.id} · ${e.time_s.toFixed(3)} s`, e.id));
  anchor.value = a.anchor_id || "";
  $("groupInfo").textContent =
    a.groups === null
      ? "Agrupación no solicitada. Elige el primer núcleo del grupo inicial tras escuchar."
      : `${a.groups.length} tríadas candidatas · ${a.detection.events.length - a.groups.length * 3} acontecimientos sin agrupar (incluye anteriores al anclaje).`;
  $("warnings").replaceChildren();
  for (const warning of a.detection.warnings) {
    const p = elem("p", explain(warning));
    p.className = "notice";
    $("warnings").append(p);
  }
  if (r.stages.detection.status === "failed")
    $("warnings").append(elem("p", r.stages.detection.message));
  const tbody = $("candidateTable").tBodies[0];
  tbody.replaceChildren();
  for (const c of a.detection.candidates) {
    const tr = elem("tr");
    for (const value of [
      c.id,
      c.time_s.toFixed(6),
      c.energy_db.toFixed(3),
      c.dip_db.toFixed(3),
      c.accepted ? "Aceptado" : explain(c.reason),
    ])
      tr.append(elem("td", value));
    const td = elem("td"),
      button = elem("button", "Escuchar");
    button.onclick = () => play(c.time_s);
    td.append(button);
    tr.append(td);
    tbody.append(tr);
  }
  energyChart();
  renderEditor();
  renderAudit();
}
function svgNode(svg, tag, attrs, text) {
  const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text !== undefined) n.textContent = text;
  svg.append(n);
  return n;
}
function energyChart() {
  const svg = $("energyChart");
  svg.replaceChildren();
  const r = state.result,
    frames = r.automatic_original.detection.frames;
  if (!frames.length) {
    svgNode(svg, "text", { x: 20, y: 80 }, "Sin contorno disponible");
    return;
  }
  const a = r.analysis_interval,
    x = (t) => 45 + ((t - a.start_s) / a.duration_s) * 820;
  const low = Math.min(...frames.map((f) => f.energy_db)),
    high = Math.max(
      ...frames.map((f) => f.energy_db),
      r.automatic_original.detection.threshold_db,
      low + 1,
    ),
    y = (v) => 180 - ((v - low) / (high - low)) * 150;
  svgNode(svg, "path", {
    d: frames
      .map((f, i) => `${i ? "L" : "M"}${x(f.time_s)} ${y(f.energy_db)}`)
      .join(" "),
    fill: "none",
    stroke: "#52858e",
  });
  const th = r.automatic_original.detection.threshold_db;
  svgNode(svg, "line", {
    x1: 45,
    x2: 865,
    y1: y(th),
    y2: y(th),
    stroke: "#c89845",
  });
  svgNode(svg, "text", { x: 8, y: 18 }, `${high.toFixed(1)} dB digital`);
  svgNode(
    svg,
    "text",
    { x: 8, y: 195 },
    `${low.toFixed(1)} dB · ${a.start_s.toFixed(3)}–${a.end_s.toFixed(3)} s`,
  );
  for (const c of r.automatic_original.detection.candidates) {
    const n = svgNode(svg, "circle", {
      cx: x(c.time_s),
      cy: y(c.energy_db),
      r: 4,
      fill: c.accepted ? "#166c78" : "#a23627",
      "data-time": c.time_s,
      tabindex: 0,
      role: "button",
      "aria-label": `Escuchar ${c.id}`,
    });
    n.onclick = () => play(c.time_s);
    n.onkeydown = (e) => {
      if (e.key === "Enter" || e.key === " ") play(c.time_s);
    };
  }
}
function renderEditor(rebuild = true) {
  const r = state.result;
  if (!r) return;
  if (rebuild) {
    const tbody = $("editTable").tBodies[0];
    tbody.replaceChildren();
    for (const event of state.events) {
      const tr = elem("tr");
      tr.dataset.id = event.id;
      tr.append(elem("td", event.id));
      const time = elem("input");
      time.type = "number";
      time.step = "any";
      time.value = event.time_s;
      time.setAttribute("aria-label", `Tiempo ${event.id}`);
      time.onchange = () => {
        const t = Number(time.value),
          a = r.analysis_interval;
        if (
          !time.value ||
          !Number.isFinite(t) ||
          t < a.start_s ||
          t >= a.end_s ||
          state.events.some((e) => e.id !== event.id && e.time_s === t)
        ) {
          time.value = event.time_s;
          say("Tiempo inválido o coincidente.", true);
          return;
        }
        if (t === event.time_s) return;
        event.time_s = t;
        state.events.sort((a, b) => a.time_s - b.time_s);
        edit({ action: "move", id: event.id, time_s: t });
      };
      const td = elem("td");
      td.append(time);
      tr.append(td);
      const select = elem("select");
      select.setAttribute("aria-label", `Etiqueta ${event.id}`);
      for (const label of ["unknown", "pa", "ta", "ka", "other"])
        select.add(
          new Option(
            label === "unknown"
              ? "Sin revisar"
              : label === "other"
                ? "Otra sílaba"
                : label,
            label,
          ),
        );
      select.value = event.label;
      select.onchange = () => {
        event.label = select.value;
        edit({ action: "label", id: event.id, label: select.value });
      };
      const labelCell = elem("td");
      labelCell.append(select);
      tr.append(labelCell);
      const restart = elem("input");
      restart.type = "checkbox";
      restart.checked = event.restart;
      restart.setAttribute("aria-label", `Reinicio ${event.id}`);
      restart.onchange = () => {
        event.restart = restart.checked;
        edit({ action: "restart", id: event.id, restart: restart.checked });
      };
      const restartCell = elem("td");
      restartCell.append(restart);
      tr.append(restartCell);
      const actions = elem("td"),
        listen = elem("button", "Escuchar"),
        remove = elem("button", "Eliminar");
      listen.onclick = () => play(event.time_s);
      remove.onclick = () => {
        state.events = state.events.filter((e) => e.id !== event.id);
        edit({ action: "delete", id: event.id });
      };
      actions.append(listen, remove);
      tr.append(actions);
      tbody.append(tr);
    }
  }
  const reviewed = r.reviewed_result?.confirmed;
  $("reviewedCards").hidden = !reviewed;
  $("reviewState").textContent = reviewed
    ? "Revisión completa: sílabas/ciclos revisados. No valida el detector en habla humana."
    : "Borrador: no hay sílabas/ciclos revisados publicados.";
  $("absence").disabled = state.events.length > 0;
  if (reviewed) cards("reviewedCards", r.reviewed_result.metrics, true);
  eventChart();
  intervalsChart(
    reviewed ? r.reviewed_result.metrics : r.automatic_original.metrics,
  );
}
function eventChart() {
  const svg = $("eventChart");
  svg.replaceChildren();
  const r = state.result,
    a = r.analysis_interval,
    x = (t) => 45 + ((t - a.start_s) / a.duration_s) * 820;
  const events = state.events;
  for (const e of events) {
    svgNode(svg, "line", {
      x1: x(e.time_s),
      x2: x(e.time_s),
      y1: 20,
      y2: 80,
      stroke: e.restart ? "#c89845" : "#166c78",
    });
    svgNode(
      svg,
      "text",
      { x: x(e.time_s) - 8, y: 98, "font-size": 10 },
      e.label === "unknown" ? "?" : e.label,
    );
  }
  const groups = r.reviewed_result?.confirmed
    ? r.reviewed_result.groups
    : r.automatic_original.groups;
  for (const g of groups || []) {
    const last = events.find((e) => e.id === g.event_ids[2]);
    if (last)
      svgNode(svg, "line", {
        x1: x(g.time_s),
        x2: x(last.time_s),
        y1: 115,
        y2: 115,
        stroke: "#52858e",
        "stroke-width": 4,
      });
  }
  svgNode(
    svg,
    "text",
    { x: 15, y: 135, "font-size": 11 },
    r.reviewed_result?.confirmed
      ? "Agrupaciones revisadas"
      : "Tríadas originales propuestas (revisión pendiente)",
  );
}
function intervalsChart(metrics) {
  const svg = $("intervalChart"),
    tbody = $("intervalTable").tBodies[0];
  svg.replaceChildren();
  tbody.replaceChildren();
  let rows = [];
  for (const [name, key] of [
    ["Acontecimientos", "event_regularity"],
    ["Agrupaciones", "group_regularity"],
  ])
    metrics[key].intervals_s.forEach((v, i) =>
      rows.push({ name, id: i + 1, v, use: "Utilizado" }),
    );
  for (const [name, key] of [
    ["Acontecimientos", "excluded_event_transitions"],
    ["Agrupaciones", "excluded_group_transitions"],
  ])
    for (const e of metrics[key])
      rows.push({
        name,
        id: `${e.from_id} → ${e.to_id}`,
        v: e.duration_s,
        use: e.reason,
      });
  const max = Math.max(0.001, ...rows.map((e) => e.v));
  rows.forEach((e, i) => {
    const tr = elem("tr");
    for (const value of [e.name, e.id, (e.v * 1000).toFixed(6), e.use])
      tr.append(elem("td", value));
    tbody.append(tr);
    svgNode(svg, "circle", {
      cx: 35 + (i / Math.max(1, rows.length - 1)) * 830,
      cy: 165 - (e.v / max) * 140,
      r: 3,
      fill:
        e.use === "Utilizado"
          ? e.name === "Acontecimientos"
            ? "#166c78"
            : "#637cbb"
          : "#c89845",
    });
  });
  svgNode(
    svg,
    "text",
    { x: 10, y: 18, "font-size": 12 },
    `Intervalos: máximo ${(max * 1000).toFixed(1)} ms · verde núcleos · azul grupos · naranja excluidos`,
  );
}
function exported() {
  return {
    response: state.result,
    recording: state.capture,
    pending_review: {
      operations: state.ops,
      confirmed: $("confirmed").checked,
      confirm_absence: $("absence").checked,
    },
  };
}
function renderAudit() {
  $("technical").textContent = JSON.stringify(exported(), null, 2);
}
$("json").onclick = () => {
  if (!state.result) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(exported(), null, 2)], {
      type: "application/json",
    }),
  );
  const a = elem("a");
  a.href = url;
  a.download = "ddk-analysis.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};
$("copy").onclick = async () => {
  if (!state.result) return;
  const reviewed = state.result.reviewed_result?.confirmed,
    m = reviewed
      ? state.result.reviewed_result.metrics
      : state.result.automatic_original.metrics;
  const text = [
    reviewed
      ? "DDK: sílabas/ciclos revisados"
      : "DDK: núcleos/tríadas candidatos",
    `Conteo: ${metricText(m.event_count)}`,
    `Tasa ${reviewed ? "revisada" : "automática estimada"}: ${metricText(m.event_rate_per_s)} /s`,
    `Grupos: ${metricText(m.group_count)}`,
    `CV temporal: ${metricText(m.event_regularity.cv_percent)} %`,
    "Validación en habla humana pendiente (6B). Sin diagnóstico.",
  ].join("\n");
  try {
    await navigator.clipboard.writeText(text);
    say("Resumen copiado.");
  } catch {
    say("No se pudo acceder al portapapeles.", true);
  }
};
update();
