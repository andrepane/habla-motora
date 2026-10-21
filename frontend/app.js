import {mountTaskSteps} from './clinical-task-flow.js';
import { taskBridge } from './profile-bridge.js';
globalThis.hablaMotorProfileBridge = taskBridge('vowel');
import {
  MAX_BYTES,
  REQUESTED,
  parseWav,
  encodeWav,
  centralInterval,
  metricText,
} from "./audio.js";
const $ = (id) => document.getElementById(id),
  state = {
    audio: null,
    file: null,
    url: null,
    result: null,
    generation: 0,
    controller: null,
    recording: null,
    capture: null,
  };
const reasons = {
  praat_undefined: "Praat no pudo calcular la medida.",
  f0_not_detected: "F0 no detectada.",
  no_analysis_frames: "No hay frames en el intervalo.",
  insufficient_voiced_frames:
    "Frames insuficientes para calcular la desviación típica.",
};
const message = (s, error = false) => {
  $("status").textContent = s;
  $("status").className = error ? "error" : "";
};
function invalidate() {
  globalThis.hablaMotorProfileBridge?.invalidate(['vowel'], 'vocal_input_or_selection_changed');
  state.generation++;
  state.controller?.abort();
  state.controller = null;
  state.result = null;
  $("results").hidden = true;
  message("");
}
function selection() {
  return centralInterval(
    Number($("start").value),
    Number($("end").value),
    state.audio?.duration ?? 0,
  );
}
function updateSelection() {
  const c = selection();
  $("analyze").disabled = !state.file || !c || !!state.recording;
  $("selection").textContent = c
    ? `Ventana central: ${c.start_s.toFixed(3)}–${c.end_s.toFixed(3)} s · emisión: ${(Number($("end").value) - Number($("start").value)).toFixed(3)} s`
    : "La emisión debe estar dentro del audio y durar al menos 3 segundos.";
  drawWave();
}
function drawWave() {
  const canvas = $("wave"),
    w = canvas.clientWidth || 800,
    h = 160;
  canvas.width = w * devicePixelRatio;
  canvas.height = h * devicePixelRatio;
  const ctx = canvas.getContext("2d");
  ctx.scale(devicePixelRatio, devicePixelRatio);
  ctx.clearRect(0, 0, w, h);
  if (!state.audio) return;
  const { samples, duration } = state.audio;
  const x = (t) => (t / duration) * w,
    a = Number($("start").value),
    b = Number($("end").value);
  ctx.fillStyle = "#e1ebed";
  ctx.fillRect(x(a), 0, x(b - a), h);
  const c = selection();
  if (c) {
    ctx.fillStyle = "#c6e9f0";
    ctx.fillRect(x(c.start_s), 0, x(3), h);
  }
  ctx.strokeStyle = "#52858e";
  ctx.beginPath();
  for (let i = 0; i < w; i++) {
    const left = Math.floor((i * samples.length) / w),
      right = Math.max(left + 1, Math.floor(((i + 1) * samples.length) / w));
    let low = 1,
      high = -1;
    for (let j = left; j < Math.min(samples.length, right); j++) {
      low = Math.min(low, samples[j]);
      high = Math.max(high, samples[j]);
    }
    ctx.moveTo(i, 80 - low * 65);
    ctx.lineTo(i, 80 - high * 65);
  }
  ctx.stroke();
  ctx.strokeStyle = "#176c78";
  ctx.lineWidth = 2;
  for (const t of [a, b]) {
    ctx.beginPath();
    ctx.moveTo(x(t), 0);
    ctx.lineTo(x(t), 160);
    ctx.stroke();
  }
  ctx.fillStyle = "#16313b";
  ctx.font = "12px system-ui";
  ctx.fillText("0 s", 8, 150);
  ctx.fillText(`${duration.toFixed(2)} s`, w - 65, 150);
}
function clear() {
  invalidate();
  if (state.url) URL.revokeObjectURL(state.url);
  state.audio = null;
  state.file = null;
  state.url = null;
  state.capture = null;
  $("player").pause();
  $("player").removeAttribute("src");
  $("player").hidden = true;
  $("downloadAudio").hidden = true;
  $("start").value = "";
  $("end").value = "";
  $("start").disabled = $("end").disabled = true;
  $("file").value = "";
  $("audioInfo").textContent = "Todavía no hay audio.";
  $("captureInfo").textContent = "Sin grabación.";
  updateSelection();
}
async function load(file, capture = null) {
  clear();
  const gen = state.generation;
  try {
    const data = await file.arrayBuffer();
    if (gen !== state.generation) return;
    const audio = parseWav(data);
    state.file = file;
    state.audio = audio;
    state.capture = capture;
    state.url = URL.createObjectURL(file);
    $("player").src = state.url;
    $("player").hidden = false;
    $("audioInfo").textContent =
      `${file.name} · ${audio.duration.toFixed(3)} s · ${audio.rate} Hz · PCM${audio.bits} mono`;
    $("start").disabled = $("end").disabled = false;
    $("start").value = 0;
    $("end").value = audio.duration;
    $("start").max = $("end").max = audio.duration;
    if (capture) {
      $("downloadAudio").href = state.url;
      $("downloadAudio").download = "vocal.wav";
      $("downloadAudio").hidden = false;
      $("captureInfo").textContent = JSON.stringify(capture, null, 2);
    }
    updateSelection();
  } catch (e) {
    message(e.message, true);
  }
}
$("file").addEventListener("change", (e) => {
  if (e.target.files[0]) load(e.target.files[0]);
});
for (const id of ["start", "end"])
  $(id).addEventListener("input", () => {
    invalidate();
    updateSelection();
  });
$("reset").onclick = () => clear();
let drag = null;
$("wave").onpointerdown = (e) => {
  if (!state.audio || state.recording) return;
  const rect = $("wave").getBoundingClientRect(),
    t = ((e.clientX - rect.left) / rect.width) * state.audio.duration;
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
  const rect = $("wave").getBoundingClientRect(),
    t = Math.max(
      0,
      Math.min(
        state.audio.duration,
        ((e.clientX - rect.left) / rect.width) * state.audio.duration,
      ),
    );
  $(drag).value = t === state.audio.duration ? String(t) : t.toFixed(3);
  invalidate();
  updateSelection();
}
$("wave").onpointermove = move;
$("wave").onpointerup = $("wave").onpointercancel = () => {
  drag = null;
};
window.addEventListener("resize", drawWave);
function captureButtons(active) {
  $("record").disabled = active;
  $("stop").disabled = !active;
  $("file").disabled = active;
  $("reset").disabled = active;
  $("start").disabled = $("end").disabled = active || !state.audio;
  $("analyze").disabled = active || !selection();
}
async function dispose(rec) {
  rec.node?.disconnect();
  rec.source?.disconnect();
  rec.stream?.getTracks().forEach((t) => t.stop());
  if (rec.ctx && rec.ctx.state !== "closed") await rec.ctx.close();
}
$("record").onclick = async () => {
  clear();
  captureButtons(true);
  message("Preparando micrófono…");
  const rec = { chunks: [], count: 0, started: performance.now() };
  state.recording = rec;
  try {
    if (!navigator.mediaDevices?.getUserMedia || !window.AudioWorkletNode)
      throw Error(
        "La grabación necesita un navegador compatible y localhost o HTTPS.",
      );
    rec.stream = await navigator.mediaDevices.getUserMedia({
      audio: REQUESTED,
    });
    if (state.recording !== rec) {
      await dispose(rec);
      return;
    }
    rec.ctx = new AudioContext();
    if (![44100, 48000].includes(rec.ctx.sampleRate))
      throw Error(
        "El navegador captura a una frecuencia incompatible. Usa un WAV compatible.",
      );
    rec.capture = {
      requested_constraints: REQUESTED,
      track_settings: rec.stream.getAudioTracks()[0].getSettings(),
      track_constraints: rec.stream.getAudioTracks()[0].getConstraints(),
      audio_context_sample_rate: rec.ctx.sampleRate,
      encoding: "WAV mono PCM16",
      channel_policy: "first_channel_only_if_browser_provides_multiple",
      observed_input_channels: [],
    };
    await rec.ctx.audioWorklet.addModule("/static/recorder-worklet.js");
    if (state.recording !== rec) {
      await dispose(rec);
      return;
    }
    rec.source = rec.ctx.createMediaStreamSource(rec.stream);
    rec.node = new AudioWorkletNode(rec.ctx, "pcm-recorder");
    rec.node.port.onmessage = (e) => {
      if (state.recording !== rec || rec.stopping) return;
      const { samples, channels } = e.data;
      if (!rec.capture.observed_input_channels.includes(channels))
        rec.capture.observed_input_channels.push(channels);
      rec.chunks.push(samples);
      rec.count += samples.length;
      message(
        `Grabando /a/ · ${(rec.count / rec.ctx.sampleRate).toFixed(1)} s`,
      );
      if (44 + rec.count * 2 >= MAX_BYTES - 4096) stopRecording();
    };
    rec.source.connect(rec.node);
    rec.node.connect(rec.ctx.destination);
    await rec.ctx.resume();
    if (state.recording !== rec) {
      await dispose(rec);
      return;
    }
    message("Grabando /a/…");
  } catch (e) {
    const current = state.recording === rec;
    if (current) state.recording = null;
    await dispose(rec);
    if (!current) return;
    captureButtons(false);
    message(e.message, true);
  }
};
async function stopRecording() {
  const rec = state.recording;
  if (!rec || rec.stopping) return;
  rec.stopping = true;
  $("stop").disabled = true;
  const rate = rec.ctx?.sampleRate;
  state.recording = null;
  await dispose(rec);
  captureButtons(false);
  if (!rec.count) {
    message("No se han capturado muestras. Repite la grabación.", true);
    return;
  }
  const samples = new Float32Array(rec.count);
  let offset = 0;
  for (const chunk of rec.chunks) {
    samples.set(chunk, offset);
    offset += chunk.length;
  }
  try {
    await load(
      new File([encodeWav(samples, rate)], "vocal.wav", { type: "audio/wav" }),
      rec.capture,
    );
  } catch (e) {
    message(e.message, true);
  }
}
$("stop").onclick = stopRecording;
function el(tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}
function chart(id, frames, key, interval) {
  const svg = $(id);
  svg.replaceChildren();
  const ns = "http://www.w3.org/2000/svg",
    add = (tag, attrs, text) => {
      const n = document.createElementNS(ns, tag);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
      if (text) n.textContent = text;
      svg.append(n);
    };
  const valid = frames.filter((f) => Number.isFinite(f[key]));
  if (!valid.length) {
    add("text", { x: 30, y: 100, fill: "#607981" }, "Sin valores calculables");
    return;
  }
  let low = Math.min(...valid.map((f) => f[key])),
    high = Math.max(...valid.map((f) => f[key]));
  const padding = Math.max((high - low) * 0.15, key === "f0_hz" ? 1 : 0.5);
  low -= padding;
  high += padding;
  const x = (t) =>
      55 + ((t - interval.start_s) / (interval.end_s - interval.start_s)) * 525,
    y = (v) => 170 - ((v - low) / (high - low)) * 140;
  for (let i = 0; i < 3; i++) {
    const v = low + ((high - low) * i) / 2;
    add("line", { x1: 55, x2: 580, y1: y(v), y2: y(v), stroke: "#dce6e8" });
    add(
      "text",
      { x: 3, y: y(v) + 4, "font-size": 11, fill: "#607981" },
      v.toFixed(1),
    );
  }
  for (const t of [interval.start_s, interval.end_s])
    add(
      "text",
      { x: x(t) - 20, y: 198, "font-size": 11, fill: "#607981" },
      `${t.toFixed(2)} s`,
    );
  let d = "",
    previous = null;
  for (const f of frames) {
    if (!Number.isFinite(f[key])) {
      previous = null;
      continue;
    }
    d += `${previous && f.frame_index === previous.frame_index + 1 ? "L" : "M"}${x(f.time_s)} ${y(f[key])} `;
    previous = f;
    add("circle", { cx: x(f.time_s), cy: y(f[key]), r: 1.3, fill: "#197e8e" });
  }
  add("path", { d, fill: "none", stroke: "#197e8e", "stroke-width": 1.5 });
}
function describedMetric(metric, unit, absent = "Módulo no disponible") {
  if (metric?.value != null) return `${metricText(metric)} ${unit}`;
  return `No calculable (${reasons[metric?.reason] ?? metric?.reason ?? absent})`;
}
function summary() {
  const r = state.result,
    s = r.modules.shimmer.result,
    h = r.modules.hnr.result;
  return [
    `Evaluación de vocal sostenida — experimental`,
    `Ventana: ${r.analysis_interval.start_s.toFixed(3)}–${r.analysis_interval.end_s.toFixed(3)} s`,
    ...specs.map(
      ([label, key, unit, module]) =>
        `${label}: ${metricText((module === "shimmer" ? s : h)?.acoustic[key])}${(module === "shimmer" ? s : h)?.acoustic[key]?.value != null ? " " + unit : ""}`,
    ),
    `Cobertura F0: ${describedMetric(s?.quality.f0_coverage_percent, "%")}`,
    `Cobertura HNR: ${describedMetric(h?.quality.hnr_coverage_percent, "%")}`,
    ...Object.entries(r.modules)
      .filter(([, m]) => m.status === "failed")
      .map(([name, m]) => `Módulo ${name} fallido: ${m.error.message}`),
    "Sin interpretación diagnóstica.",
  ].join("\n");
}
const specs = [
  ["F0 media", "f0_mean_hz", "Hz", "shimmer"],
  ["DT F0", "f0_sd_hz", "Hz", "shimmer"],
  ["Jitter local", "jitter_local_percent", "%", "shimmer"],
  ["Shimmer local", "shimmer_local_percent", "%", "shimmer"],
  ["HNR medio", "hnr_mean_db", "dB", "hnr"],
];
function render(r) {
  globalThis.hablaMotorProfileBridge?.save('vowel', r, state.file, state.capture);
  state.result = r;
  $("results").hidden = false;
  $("resultState").textContent =
    r.status === "partial"
      ? "Resultado parcial: revisa el módulo fallido."
      : "Análisis completado · ventana central de 3 segundos";
  $("cards").replaceChildren();
  for (const [label, key, unit, module] of specs) {
    const m = r.modules[module],
      metric = m.result?.acoustic[key],
      card = el("div", undefined, "card");
    card.append(el("h3", label), el("div", metricText(metric), "value"));
    card.append(
      el(
        "div",
        metric?.value != null
          ? unit
          : m.status === "failed"
            ? `Módulo ${module} fallido`
            : (reasons[metric?.reason] ?? metric?.reason ?? "No disponible"),
        "reason",
      ),
    );
    $("cards").append(card);
  }
  const s = r.modules.shimmer.result,
    h = r.modules.hnr.result;
  $("coverage").replaceChildren(
    el(
      "span",
      `Cobertura F0: ${describedMetric(s?.quality.f0_coverage_percent, "%")}`,
    ),
    el(
      "span",
      `Cobertura HNR: ${describedMetric(h?.quality.hnr_coverage_percent, "%")}`,
    ),
  );
  $("warnings").replaceChildren();
  const seen = new Set();
  for (const [name, m] of Object.entries(r.modules)) {
    if (m.error)
      $("warnings").append(
        el(
          "p",
          `${name}: análisis no disponible. ${m.error.message}`,
          "notice",
        ),
      );
    for (const w of m.result?.quality.technical_warnings ?? []) {
      const identity = w.code + "|" + w.message;
      if (seen.has(identity)) continue;
      seen.add(identity);
      $("warnings").append(el("p", w.message, "notice"));
    }
  }
  chart("pitchChart", s?.tracking_frames ?? [], "f0_hz", r.analysis_interval);
  chart(
    "hnrChart",
    h?.tracking_hnr_frames ?? [],
    "hnr_db",
    r.analysis_interval,
  );
  $("technical").textContent = JSON.stringify(
    { ...r, recording: state.capture },
    null,
    2,
  );
}
$("analyze").onclick = async () => {
  if (!selection() || !state.file) return;
  invalidate();
  const gen = state.generation,
    controller = new AbortController();
  state.controller = controller;
  $("analyze").disabled = true;
  message("Analizando F0, jitter, shimmer y HNR…");
  const form = new FormData();
  form.append("file", state.file);
  form.append("emission_start_s", $("start").value);
  form.append("emission_end_s", $("end").value);
  try {
    const response = await fetch("/vowel-analysis", {
      method: "POST",
      body: form,
      signal: controller.signal,
    });
    const r = await response.json();
    if (gen !== state.generation) return;
    if (!response.ok)
      throw Error(
        typeof r.detail === "string"
          ? r.detail
          : "El servidor no pudo analizar el audio.",
      );
    render(r);
    message(
      r.status === "partial" ? "Análisis parcial." : "Análisis completado.",
    );
  } catch (e) {
    if (gen === state.generation && e.name !== "AbortError") {
      globalThis.hablaMotorProfileBridge?.failed('vowel', e.message);
      message(e.message, true);
    }
  } finally {
    if (gen === state.generation) {
      state.controller = null;
      updateSelection();
    }
  }
};
$("copy").onclick = async () => {
  try {
    await navigator.clipboard.writeText(summary());
    message("Resumen copiado.");
  } catch {
    message("No se pudo acceder al portapapeles.", true);
  }
};
$("json").onclick = () => {
  const url = URL.createObjectURL(
    new Blob(
      [JSON.stringify({ ...state.result, recording: state.capture }, null, 2)],
      { type: "application/json" },
    ),
  );
  const a = el("a");
  a.href = url;
  a.download = "vocal-analysis.json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

globalThis.hablaMotorProfileBridge?.ready?.then(()=>mountTaskSteps('vowel',globalThis.hablaMotorProfileBridge));
