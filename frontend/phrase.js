import { parseWav, metricText } from "./audio.js";
import { PhraseRecorder } from "./phrase-recorder.js";
import { AttemptState, parseEvents, changeFields } from "./phrase-state.js";
const protocol = await fetch("/phrase-protocol").then((r) => r.json());
const $ = (id) => document.getElementById(id);
const slots = [];
let active = 1;
let busy = false;
let lastStop = null;
const base64 = (buffer) => {
  let s = "";
  const bytes = new Uint8Array(buffer);
  for (let p = 0; p < bytes.length; p += 16384)
    s += String.fromCharCode(...bytes.subarray(p, p + 16384));
  return btoa(s);
};
const sha = async (buffer) =>
  Array.from(
    new Uint8Array(await crypto.subtle.digest("SHA-256", buffer)),
    (x) => x.toString(16).padStart(2, "0"),
  ).join("");
function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
for (let id = 1; id <= 2; id++) {
  const section = document.createElement("section");
  section.id = `attempt${id}`;
  section.hidden = id !== 1;
  section.innerHTML = `<h2>Intento ${id}</h2><label>Frase <select data-f="phrase"><option value="${protocol.stimulus.id}">Frase española 01 · v1</option></select></label>
 <label>Modalidad <select data-f="modality"><option value="direct_reading_v1">Lectura directa · principal</option><option value="auditory_model_with_text_v1">Modelo auditivo con texto · variante</option><option value="auditory_model_only_v1">Modelo auditivo sin texto · variante</option></select></label>
 <p class="instruction"></p><p class="stimulus"></p>
 <fieldset class="model" hidden><legend>Modelo auditivo identificado</legend><p>Variante separada. Aporta el mismo WAV de modelo en todos los intentos comparables. Su hash identifica el modelo; no se sintetiza ni se cambia su velocidad.</p><label>WAV del modelo <input data-f="model" type="file" accept=".wav,audio/wav"></label><audio class="modelAudio" controls></audio><button class="playModel">Escuchar modelo completo</button><p class="modelState">Modelo pendiente.</p></fieldset>
 <fieldset><legend>Grabación o subida del intento</legend><label>WAV original <input data-f="file" type="file" accept=".wav,audio/wav"></label><button class="record">Grabar</button><button class="stop" disabled>Detener</button><button class="cancel" disabled>Cancelar grabación</button><p class="captureState" role="status"></p><audio class="audio" controls></audio><button class="original" disabled>Descargar WAV original</button><label><input data-f="limit" type="checkbox"> La grabación se interrumpió por alcanzar el límite</label></fieldset>
 <fieldset><legend>Selección manual [inicio, fin)</legend><p>Arrastra sobre la onda o introduce índices de muestra. Incluye pausas, repeticiones y reinicios interiores.</p><svg class="wave" viewBox="0 0 800 180" aria-label="Forma de onda y selección manual"></svg><div class="grid"><label>Muestra inicial <input data-f="start" type="number" min="0" step="1"></label><label>Fin exclusivo <input data-f="end" type="number" min="1" step="1"></label></div><p class="times"></p><button class="zoomSelection">Ampliar selección</button><button class="zoomReset">Ver WAV completo</button><button class="markStart">Inicio en cursor de audio</button><button class="markEnd">Fin en cursor de audio</button><button class="playSelection">Escuchar selección</button><label><input data-f="selectionConfirmed" type="checkbox"> Confirmo que los límites incluyen toda la producción que quiero analizar</label><button class="analyze">Validar selección y obtener contexto</button></fieldset>
 <fieldset class="review"><legend>Revisión manual independiente</legend><label>Producción <select data-f="production"><option value="pending">Pendiente</option><option value="present">Hay producción</option><option value="absent">Ausencia confirmada</option></select></label><label>Coincidencia textual <select data-f="match"><option value="pending">Pendiente</option><option value="exact_once">Objetivo completo exactamente una vez</option><option value="different">Diferente del objetivo</option><option value="uncertain">Dudosa</option></select></label><div class="grid"><label>Palabras realmente producidas <input data-f="words" type="number" min="0" step="1" placeholder="Sin recuento"></label><label>Sílabas realmente producidas <input data-f="syllables" type="number" min="0" step="1" placeholder="Sin recuento"></label></div><label><input data-f="wordsConfirmed" type="checkbox"> Confirmo exclusivamente el recuento de palabras</label><label><input data-f="syllablesConfirmed" type="checkbox"> Confirmo exclusivamente el recuento de sílabas</label><p>Cuenta palabras completas, incluidas repeticiones. Los fragmentos no son fracciones de palabra; sus sílabas identificables sí pueden contarse manualmente. «pa-pa-papel»: 1 palabra completa y 4 sílabas. No se copian los recuentos del objetivo.</p><label>Acontecimientos: una línea por tipo y nota (tipo: nota)<textarea data-f="events" placeholder="omission: pequeñas&#10;repetition: papel&#10;substitution: ...&#10;fragment: ...&#10;restart: ..."></textarea></label><p>Tipos: omission, repetition, substitution, fragment, restart, addition, filled_pause, uncertain.</p><label>Notas o transcripción manual <textarea data-f="notes"></textarea></label><label><input data-f="reviewConfirmed" type="checkbox"> Confirmo esta revisión; cada recuento conserva su propia confirmación</label><button class="submitReview">Calcular con revisión manual</button></fieldset>
 <p class="state" role="status">Sin archivo.</p><div class="grid results"></div><details><summary>Auditoría completa de este intento</summary><pre class="audit"></pre></details>`;
  $("attempts").append(section);
  const get = (name) => section.querySelector(`[data-f="${name}"]`),
    q = (s) => section.querySelector(s);
  const s = {
    id,
    section,
    get,
    q,
    state: new AttemptState(id),
    file: null,
    buffer: null,
    wav: null,
    capture: null,
    url: null,
    model: null,
    modelPlayed: false,
    recording: false,
    loadToken: 0,
    request: null,
    assets: [],
    modelAssets: [],
  };
  slots.push(s);
  q(".stimulus").textContent = protocol.stimulus.text;
  const resetReview = () => {
    for (const f of ["wordsConfirmed", "syllablesConfirmed", "reviewConfirmed"])
      get(f).checked = false;
    for (const f of ["words", "syllables", "events", "notes"])
      get(f).value = "";
    get("production").value = "pending";
    get("match").value = "pending";
  };
  s.invalidate = (reason, context = true) => {
    s.request?.abort();
    s.state.invalidate(reason, context);
    if (context) {
      resetReview();
      if (reason !== "selectionConfirmed")
        get("selectionConfirmed").checked = false;
    } else {
      if (reason !== "reviewConfirmed") get("reviewConfirmed").checked = false;
      if (reason === "words") get("wordsConfirmed").checked = false;
      if (reason === "syllables") get("syllablesConfirmed").checked = false;
    }
    q(".results").replaceChildren();
    q(".state").textContent =
      "Resultados invalidados. Revisa y vuelve a calcular.";
    audit(s);
  };
  function modality() {
    const direct = get("modality").value === "direct_reading_v1";
    q(".model").hidden = direct;
    q(".stimulus").hidden = get("modality").value === "auditory_model_only_v1";
    q(".instruction").textContent = direct
      ? protocol.instruction
      : "Escucha el modelo y, tras la señal, di la frase completa una vez, a tu ritmo habitual.";
  }
  modality();
  for (const input of section.querySelectorAll("[data-f]"))
    input.addEventListener(input.type === "file" ? "change" : "input", () => {
      const field = input.dataset.f;
      if (field === "file" || field === "model") return;
      s.state.history.push({
        event: "edit",
        field,
        value: input.type === "checkbox" ? input.checked : input.value,
      });
      s.invalidate(field, changeFields.has(field));
      if (field === "modality") {
        q(".modelAudio").pause();
        q(".modelAudio").currentTime = 0;
        s.modelPlayed = false;
        modality();
      }
      if (field === "start" || field === "end") draw(s);
    });
  s.load = async (file, capture = null) => {
    const token = ++s.loadToken;
    s.invalidate("audio", true);
    s.file = null;
    s.buffer = null;
    s.wav = null;
    s.capture = capture;
    get("file").value = "";
    get("limit").checked = !!capture?.limit_reached;
    q(".original").disabled = true;
    try {
      if (file.size > 4000000) throw Error("Máximo 4.000.000 bytes.");
      const buffer = await file.arrayBuffer();
      const wav = parseWav(buffer);
      if (wav.duration > 20) throw Error("Máximo 20 s.");
      if (token !== s.loadToken) return;
      if (s.url) URL.revokeObjectURL(s.url);
      const hash = await sha(buffer);
      if (token !== s.loadToken) return;
      if (!s.assets.some((x) => x.sha256 === hash))
        s.assets.push({ sha256: hash, file_name: file.name, buffer });
      s.file = file;
      s.buffer = buffer;
      s.wav = wav;
      s.viewStart = 0;
      s.viewEnd = wav.samples.length;
      s.url = URL.createObjectURL(file);
      q(".audio").src = s.url;
      q(".original").disabled = false;
      get("start").value = 0;
      get("end").value = wav.samples.length;
      q(".state").textContent =
        "WAV conservado íntegro. Selecciona y confirma los límites.";
      draw(s);
      audit(s);
    } catch (e) {
      if (token === s.loadToken) {
        q(".audio").removeAttribute("src");
        q(".wave").replaceChildren();
        q(".state").textContent = e.message;
      }
    }
  };
  get("file").addEventListener("change", () => {
    const file = get("file").files[0];
    if (file) s.load(file);
  });
  get("model").addEventListener("change", async () => {
    s.invalidate("model", true);
    s.modelPlayed = false;
    s.model = null;
    const file = get("model").files[0];
    if (!file) return;
    const token = ++s.loadToken;
    try {
      if (file.size > 4000000) throw Error("Modelo demasiado grande.");
      const buffer = await file.arrayBuffer();
      const wav = parseWav(buffer);
      if (wav.duration > 20) throw Error("Modelo de más de 20 s.");
      const hash = await sha(buffer);
      if (token !== s.loadToken) return;
      s.model = { buffer, hash, id: `wav-sha256:${hash}` };
      if (!s.modelAssets.some((a) => a.sha256 === hash))
        s.modelAssets.push({ sha256: hash, file_name: file.name, buffer });
      q(".modelAudio").src = URL.createObjectURL(file);
      q(".modelState").textContent =
        `Modelo identificado: ${hash}. Aún no presentado completo.`;
    } catch (e) {
      q(".modelState").textContent = e.message;
    }
  });
  q(".playModel").onclick = async () => {
    if (!s.model) return;
    q(".modelAudio").currentTime = 0;
    s.modelPlayed = false;
    try {
      await q(".modelAudio").play();
    } catch (e) {
      q(".modelState").textContent = e.message;
    }
  };
  q(".modelAudio").onended = () => {
    s.invalidate("model_presentation", true);
    s.modelPlayed = true;
    q(".modelState").textContent =
      "Modelo reproducido completo. Espera un segundo y usa Grabar.";
  };
  s.recorder = new PhraseRecorder((seconds) => {
    q(".captureState").textContent =
      seconds < 1
        ? "Preparando… espera la señal visual."
        : `Ahora: ${get("modality").value === "direct_reading_v1" ? "lee" : "di"} la frase una vez a tu ritmo habitual. Grabando ${seconds.toFixed(1)} / 20 s.`;
    if (seconds >= 20 && s.recording) stop(false, true);
  });
  function lock(value) {
    busy = value;
    for (const button of [$("tab1"), $("tab2")]) button.disabled = value;
    for (const control of section.querySelectorAll(
      "input,select,textarea,button",
    ))
      control.disabled = value;
    q(".stop").disabled = !value;
    q(".cancel").disabled = !value;
  }
  async function stop(cancel = false, limit = false) {
    if (!s.recording) return;
    s.recording = false;
    try {
      const result = await s.recorder.stop();
      if (!cancel && result) {
        result.capture.limit_reached = limit;
        result.capture.visual_cue_after_recorded_s = 1;
        await s.load(result.file, result.capture);
      }
      q(".captureState").textContent = cancel
        ? "Grabación cancelada."
        : limit
          ? "Límite de 20 s alcanzado; intento interrumpido."
          : "Grabación conservada.";
      lastStop = Date.now();
      updateRest();
    } catch (e) {
      q(".captureState").textContent = e.message;
    } finally {
      lock(false);
    }
  }
  q(".record").onclick = async () => {
    if (get("modality").value !== "direct_reading_v1" && !s.modelPlayed) {
      q(".captureState").textContent = "Escucha primero el modelo completo.";
      return;
    }
    for (const slot of slots) {
      slot.q(".audio").pause();
      slot.q(".modelAudio").pause();
    }
    s.invalidate("recording", true);
    s.recording = true;
    lock(true);
    q(".captureState").textContent = "Esperando permiso de micrófono…";
    try {
      const started = await s.recorder.start();
      if (started && s.recording)
        q(".captureState").textContent = "Preparando… espera la señal visual.";
    } catch (e) {
      s.recording = false;
      lock(false);
      q(".captureState").textContent = e.message;
    }
  };
  q(".stop").onclick = () => stop(false);
  q(".cancel").onclick = () => stop(true);
  q(".original").onclick = () => {
    if (s.file) download(s.file, `frase-intento-${id}.wav`);
  };
  q(".zoomSelection").onclick = () => {
    if (!s.wav) return;
    const a = Number(get("start").value),
      b = Number(get("end").value);
    if (
      Number.isInteger(a) &&
      Number.isInteger(b) &&
      a >= 0 &&
      a < b &&
      b <= s.wav.samples.length
    ) {
      s.viewStart = a;
      s.viewEnd = b;
      draw(s);
    }
  };
  q(".zoomReset").onclick = () => {
    if (!s.wav) return;
    s.viewStart = 0;
    s.viewEnd = s.wav.samples.length;
    draw(s);
  };
  q(".markStart").onclick = () => {
    if (s.wav) {
      get("start").value = Math.round(q(".audio").currentTime * s.wav.rate);
      s.invalidate("start", true);
      draw(s);
    }
  };
  q(".markEnd").onclick = () => {
    if (s.wav) {
      get("end").value = Math.min(
        s.wav.samples.length,
        Math.round(q(".audio").currentTime * s.wav.rate),
      );
      s.invalidate("end", true);
      draw(s);
    }
  };
  q(".playSelection").onclick = () => {
    if (!s.wav) return;
    const end = Number(get("end").value) / s.wav.rate;
    q(".audio").currentTime = Number(get("start").value) / s.wav.rate;
    q(".audio").ontimeupdate = () => {
      if (q(".audio").currentTime >= end) {
        q(".audio").pause();
        q(".audio").ontimeupdate = null;
      }
    };
    q(".audio")
      .play()
      .catch((e) => (q(".state").textContent = e.message));
  };
  let down = null;
  q(".wave").onpointerdown = (e) => {
    if (!s.wav || busy) return;
    down = sampleAt(e, s);
    q(".wave").setPointerCapture(e.pointerId);
  };
  q(".wave").onpointerup = (e) => {
    if (down === null) return;
    const end = sampleAt(e, s);
    get("start").value = Math.min(s.wav.samples.length - 1, down, end);
    get("end").value = Math.min(s.wav.samples.length, Math.max(down + 1, end));
    down = null;
    s.invalidate("selection", true);
    draw(s);
  };
  q(".analyze").onclick = () => send(s, false);
  q(".submitReview").onclick = () => send(s, true);
}
function sampleAt(e, s) {
  const rect = s.q(".wave").getBoundingClientRect();
  return Math.max(
    0,
    Math.min(
      s.wav.samples.length,
      Math.round(
        s.viewStart +
          ((e.clientX - rect.left) / rect.width) * (s.viewEnd - s.viewStart),
      ),
    ),
  );
}
function draw(s) {
  if (!s.wav) return;
  const points = [];
  const n = s.viewEnd - s.viewStart;
  const offset = s.viewStart;
  s.q(".wave").dataset.startSample = String(s.viewStart);
  s.q(".wave").dataset.endSample = String(s.viewEnd);
  for (let x = 0; x < 800; x++) {
    let low = 0,
      high = 0;
    for (
      let j = offset + Math.floor((x * n) / 800);
      j < offset + Math.floor(((x + 1) * n) / 800);
      j++
    ) {
      low = Math.min(low, s.wav.samples[j]);
      high = Math.max(high, s.wav.samples[j]);
    }
    points.push(`M${x},${90 - low * 85}V${90 - high * 85}`);
  }
  const a = Number(s.get("start").value),
    b = Number(s.get("end").value);
  s.q(".wave").innerHTML =
    `<rect x="${((a - offset) / n) * 800}" y="0" width="${Math.max(0, ((b - a) / n) * 800)}" height="180" fill="#d3eceb"/><path d="${points.join(" ")}" stroke="#176876" stroke-width="1"/>`;
  s.q(".times").textContent =
    `${s.wav.rate} Hz · [${a}, ${b}) muestras · ${(a / s.wav.rate).toFixed(6)}–${(b / s.wav.rate).toFixed(6)} s · Duración: ${((b - a) / s.wav.rate).toFixed(6)} s`;
}
function context(s) {
  const mode = s.get("modality").value;
  return {
    phrase_id: s.get("phrase").value,
    modality: mode,
    attempt: s.id,
    selection: {
      start_sample:
        s.get("start").value === "" ? null : Number(s.get("start").value),
      end_sample_exclusive:
        s.get("end").value === "" ? null : Number(s.get("end").value),
    },
    selection_confirmed: s.get("selectionConfirmed").checked,
    recording_limit_reached: s.get("limit").checked,
    administration:
      mode === "direct_reading_v1"
        ? {}
        : {
            model_id: s.model?.id,
            model_sha256: s.model?.hash,
            model_presented_confirmed: s.modelPlayed,
          },
  };
}
function reviewDraft(s) {
  const count = (field, check) => ({
    value: s.get(field).value === "" ? null : Number(s.get(field).value),
    confirmed: s.get(check).checked,
  });
  return {
    context_sha256: s.state.contextResult?.provenance.context_sha256 || null,
    confirmed: s.get("reviewConfirmed").checked,
    production: s.get("production").value,
    target_match: s.get("match").value,
    word_count: count("words", "wordsConfirmed"),
    syllable_count: count("syllables", "syllablesConfirmed"),
    events: parseEvents(s.get("events").value),
    notes: s.get("notes").value,
  };
}
async function send(s, reviewed) {
  if (!s.file) return;
  s.request?.abort();
  const controller = new AbortController();
  s.request = controller;
  const revision = s.state.revision;
  const form = new FormData();
  form.append("file", s.file);
  form.append("context_json", JSON.stringify(context(s)));
  if (reviewed) {
    if (!s.state.contextResult) {
      s.q(".state").textContent = "Primero valida la selección actual.";
      return;
    }
    const review = reviewDraft(s);
    form.append("review_json", JSON.stringify(review));
    form.append(
      "expected_file_sha256",
      s.state.contextResult.provenance.file_sha256,
    );
  }
  s.q(".state").textContent = "Calculando…";
  try {
    const response = await fetch("/phrase-analysis", {
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
    if (s.state.accept(result, revision)) render(s, result);
  } catch (e) {
    if (e.name !== "AbortError" && revision === s.state.revision) {
      s.q(".state").textContent = `Error: ${e.message}`;
      s.q(".results").replaceChildren();
      s.state.result = null;
      s.state.history.push({ event: "error", message: e.message, revision });
      audit(s);
    }
  }
}
function render(s, r) {
  s.q(".state").textContent =
    `Selección: ${r.stages.selection.status} · Revisión: ${r.stages.review.status} · Cálculo: ${r.stages.calculation.status}`;
  s.q(".results").replaceChildren();
  const metrics = { selected_duration_s: r.selected_duration_s, ...r.rates };
  const labels = {
    selected_duration_s: "Duración del tramo (s)",
    reference_word_rate: "Palabras/min · referencia textual",
    reference_syllable_rate: "Sílabas canónicas/s · referencia",
    reviewed_word_rate: "Palabras/min · recuento manual",
    reviewed_syllable_rate: "Sílabas producidas/s · recuento manual",
  };
  for (const [key, m] of Object.entries(metrics)) {
    const div = document.createElement("div");
    div.className = "metric";
    const label = document.createElement("span");
    label.textContent = labels[key];
    const value = document.createElement("strong");
    value.textContent = metricText(m);
    const note = document.createElement("small");
    note.textContent =
      m.reason ||
      m.count_basis ||
      "Por índices de muestra; incluye pausas interiores";
    div.append(label, value, note);
    s.q(".results").append(div);
  }
  audit(s);
}
function audit(s) {
  s.q(".audit").textContent = JSON.stringify(
    {
      attempt: s.id,
      capture: s.capture,
      results_current: !!s.state.result,
      response: s.state.result,
      history: s.state.history,
    },
    null,
    2,
  );
}
function updateRest() {
  const seconds = lastStop
    ? Math.max(0, 20 - Math.floor((Date.now() - lastStop) / 1000))
    : 0;
  $("rest").textContent = seconds
    ? `Descanso recomendado antes del siguiente intento: ${seconds} s.`
    : "";
}
setInterval(updateRest, 1000);
for (let i = 1; i <= 2; i++)
  $(`tab${i}`).onclick = () => {
    if (busy) return;
    active = i;
    for (const s of slots) {
      s.q(".audio").pause();
      s.q(".modelAudio").pause();
      s.section.hidden = s.id !== i;
      $(`tab${s.id}`).setAttribute("aria-pressed", String(s.id === i));
    }
    updateRest();
  };
$("exportAll").onclick = () => {
  const payload = {
    schema_version: "phrase_battery_export_v1",
    protocol,
    validation: "technical_only_human_validation_pending",
    attempts: slots.map((s) => ({
      attempt: s.id,
      file_name: s.file?.name || null,
      wav_base64: s.buffer ? base64(s.buffer) : null,
      model_wav_base64: s.model ? base64(s.model.buffer) : null,
      model_assets: s.modelAssets.map((a) => ({
        sha256: a.sha256,
        file_name: a.file_name,
        wav_base64: base64(a.buffer),
      })),
      original_assets: s.assets.map((a) => ({
        sha256: a.sha256,
        file_name: a.file_name,
        wav_base64: base64(a.buffer),
      })),
      capture: s.capture,
      context: s.wav ? context(s) : null,
      review_draft: reviewDraft(s),
      current_revision: s.state.revision,
      current_response: s.state.result,
      context_response: s.state.contextResult,
      history: s.state.history,
      results_current: !!s.state.result,
    })),
    aggregation: null,
  };
  download(
    new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }),
    "frase-7a-bateria.json",
  );
  $("globalStatus").textContent =
    "Exportados los WAV íntegros, respuestas y revisiones de ambos intentos. Los resultados invalidados están identificados en el historial.";
};
