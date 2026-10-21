import { CandidateState } from "./phrase-candidate-state.js";
export function mountCandidates(s, redraw) {
  const state = new CandidateState();
  const panel = document.createElement("fieldset");
  panel.className = "candidatePanel";
  panel.innerHTML = `<legend>Ayuda experimental opcional</legend>
  <button type="button" data-c="run">Proponer candidatos automáticamente (experimental)</button>
  <p>Puede proponer cierres consonánticos o interrupciones breves y omitir regiones. Los límites pueden requerir corrección. La revisión manual sigue siendo obligatoria.</p>
  <p>Revisar todos los candidatos no equivale a revisar toda la selección. Cero candidatos no equivale a cero pausas. Solo la revisión manual confirmada produce las métricas definitivas.</p>
  <p data-c="state" role="status">Desactivado: se ejecuta únicamente al pulsar el botón.</p>
  <div data-c="rows"></div><details><summary>Detalles técnicos e historial experimental</summary><pre data-c="audit"></pre></details>`;
  s.section.append(panel);
  const q = (k) => panel.querySelector(`[data-c="${k}"]`);
  let controller,
    selected = null;
  const exported = () => state.exported(s.pauses.exported());
  function audit() {
    q("audit").textContent = JSON.stringify(exported(), null, 2);
  }
  function display() {
    q("state").textContent = {
      idle: "Desactivado: se ejecuta únicamente al pulsar el botón.",
      processing: "Procesando propuestas experimentales…",
      completed: `Completado: ${state.run?.automatic_candidates?.length ?? 0} candidatos sin confirmar. No es un recuento de pausas.`,
      not_evaluable:
        "No evaluable: no se ofrecen candidatos; no implica ausencia de pausas.",
      failed:
        "No se pudo completar la propuesta. La revisión manual sigue disponible.",
      stale:
        "Propuestas invalidadas por cambio de dependencias o nueva ejecución.",
    }[state.status];
    q("run").disabled = state.status === "processing";
    rows();
    redraw(s);
    audit();
  }
  function invalidate(reason) {
    s.profileBridge?.invalidate(['candidates'], reason, s.id);
    controller?.abort();
    state.invalidate(reason);
    selected = null;
    display();
  }
  q("run").onclick = async () => {
    const source = s.state.contextResult;
    if (!s.file || !source || !source.context.selection_confirmed) {
      q("state").textContent = "Primero valida la selección confirmada de 7A.";
      return;
    }
    controller?.abort();
    controller = new AbortController();
    const signal = controller.signal;
    const requestDependencies = {
      file_sha256: source.provenance.file_sha256,
      context_sha256: source.provenance.context_sha256,
      context: structuredClone(source.context),
      detector_version: "pause_detector_energy_v1",
    };
    let protocol = null;
    const revision = state.begin(requestDependencies);
    selected = null;
    display();
    const file = s.file,
      context = structuredClone(source.context),
      provenance = source.provenance;
    try {
      const protocolResponse = await fetch("/phrase-candidate-protocol", {
        signal,
      });
      if (!protocolResponse.ok) throw Error("protocol");
      protocol = await protocolResponse.json();
      if (revision !== state.revision) return;
      state.history.push({
        event: "detector_identified",
        revision,
        protocol: structuredClone(protocol),
      });
      const form = new FormData();
      form.append("file", file);
      form.append("context_json", JSON.stringify(context));
      form.append(
        "expected_dependencies_json",
        JSON.stringify({
          file_sha256: provenance.file_sha256,
          context_sha256: provenance.context_sha256,
          config_sha256: protocol.config_sha256,
          engine_sha256: protocol.engine_sha256,
        }),
      );
      const response = await fetch("/phrase-candidates", {
        method: "POST",
        body: form,
        signal,
      });
      if (!response.ok) throw Error("request");
      const body = await response.json();
      if (state.complete(body, revision)) {
        s.profileBridge?.save('candidates', body, file, s.capture, null, s.id);
        display();
      }
    } catch (e) {
      if (
        e.name !== "AbortError" &&
        state.complete(
          {
            status: "failed",
            reason: "request_failed",
            automatic_candidates: null,
            dependencies: {
              ...requestDependencies,
              config_sha256: protocol?.config_sha256 ?? null,
              engine_sha256: protocol?.engine_sha256 ?? null,
            },
            configuration: protocol?.configuration ?? null,
          },
          revision,
        )
      )
        display();
    }
  };
  function rows() {
    q("rows").replaceChildren();
    for (const c of state.run?.automatic_candidates ?? []) {
      const row = document.createElement("fieldset");
      row.dataset.candidateId = c.candidate_id;
      const title = document.createElement("legend");
      title.textContent = "Candidato automático — requiere revisión manual";
      row.append(title);
      const info = document.createElement("p");
      info.textContent = `Propuesta de ${c.duration_s.toFixed(3)} s · requiere revisión manual`;
      row.append(info);
      const bounds = {};
      for (const [key, label] of [
        ["start_sample", "Inicio absoluto propuesto"],
        ["end_sample_exclusive", "Fin exclusivo propuesto"],
      ]) {
        const l = document.createElement("label"),
          input = document.createElement("input");
        l.textContent = label;
        input.type = "number";
        input.step = "1";
        input.value = c[key];
        input.dataset.bound = key;
        bounds[key] = input;
        l.append(input);
        row.append(l);
      }
      const decision = state.decisions.find(
        (d) => d.candidate_id === c.candidate_id,
      );
      if (decision) {
        const note = document.createElement("p");
        note.textContent =
          decision.action === "rejected"
            ? "Propuesta rechazada; no modifica 7B.1."
            : "Copiado como uncertain. Clasifica y revisa después en 7B.1.";
        row.append(note);
      }
      const button = (label, action, terminal = false) => {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = label;
        b.disabled = terminal && !!decision;
        b.onclick = action;
        row.append(b);
      };
      button("Seleccionar candidato", () => {
        selected = c.candidate_id;
        redraw(s);
      });
      button("Escuchar candidato con contexto", () => {
        const audio = s.q(".audio");
        audio.currentTime = Math.max(0, c.start_sample / s.wav.rate - 0.25);
        const end = Math.min(
          s.wav.duration,
          c.end_sample_exclusive / s.wav.rate + 0.25,
        );
        audio.ontimeupdate = () => {
          if (audio.currentTime >= end) {
            audio.pause();
            audio.ontimeupdate = null;
          }
        };
        audio.play().catch(() => {
          q("state").textContent =
            "No se pudo iniciar la escucha; utiliza el reproductor del WAV.";
        });
      });
      button("Ampliar candidato", () => {
        s.viewStart = Math.max(
          0,
          c.start_sample - Math.round(0.25 * s.wav.rate),
        );
        s.viewEnd = Math.min(
          s.wav.samples.length,
          c.end_sample_exclusive + Math.round(0.25 * s.wav.rate),
        );
        selected = c.candidate_id;
        redraw(s);
      });
      button(
        "Rechazar",
        () => {
          state.decide(c.candidate_id, "rejected");
          display();
        },
        true,
      );
      const copy = (edited) => {
        const b = edited
          ? Object.fromEntries(
              Object.entries(bounds).map(([k, v]) => [
                k,
                v.value === "" ? null : Number(v.value),
              ]),
            )
          : {
              start_sample: c.start_sample,
              end_sample_exclusive: c.end_sample_exclusive,
            };
        const selection = state.run.dependencies.context.selection;
        if (
          !Number.isInteger(b.start_sample) ||
          !Number.isInteger(b.end_sample_exclusive) ||
          !(
            selection.start_sample < b.start_sample &&
            b.start_sample < b.end_sample_exclusive &&
            b.end_sample_exclusive < selection.end_sample_exclusive
          )
        ) {
          q("state").textContent =
            "Introduce límites enteros internos a la selección antes de copiar.";
          return;
        }
        const id = s.pauses.copyUncertain(b);
        state.decide(c.candidate_id, "copied", b, id);
        display();
      };
      button("Copiar a revisión manual", () => copy(false), true);
      button("Editar límites y copiar", () => copy(true), true);
      q("rows").append(row);
    }
  }
  function overlay() {
    s.q(".wave .candidateOverlay")?.remove();
    if (!s.wav) return;
    const ns = "http://www.w3.org/2000/svg",
      g = document.createElementNS(ns, "g");
    g.classList.add("candidateOverlay");
    g.style.pointerEvents = "none";
    for (const c of state.run?.automatic_candidates ?? []) {
      const a = Math.max(s.viewStart, c.start_sample),
        b = Math.min(s.viewEnd, c.end_sample_exclusive);
      if (a >= b) continue;
      const r = document.createElementNS(ns, "rect");
      for (const [k, v] of Object.entries({
        x: (800 * (a - s.viewStart)) / (s.viewEnd - s.viewStart),
        width: (800 * (b - a)) / (s.viewEnd - s.viewStart),
        y: 3,
        height: 174,
        fill: "none",
        stroke: c.candidate_id === selected ? "#b244b5" : "#197c82",
        "stroke-width": 3,
        "stroke-dasharray": "7 4",
      }))
        r.setAttribute(k, v);
      const t = document.createElementNS(ns, "title");
      t.textContent = "Candidato automático — requiere revisión manual";
      r.append(t);
      g.append(r);
    }
    s.q(".wave").append(g);
  }
  audit();
  return { invalidate, overlay, exported };
}
