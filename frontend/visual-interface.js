// Presentation only. No requests, storage, source writes, analysis or metric calculations.
const page = document.body.dataset.page;
const active = {
  evaluation: "evaluation",
  vowel: "vowel",
  ddk: "ddk",
  phrase: "phrase",
  profile: "profile",
}[page];
function set(node, key, value) {
  if (node.getAttribute(key) !== value) node.setAttribute(key, value);
}
function read(node) {
  try {
    return JSON.parse(node?.textContent || "{}");
  } catch {
    return {};
  }
}
function paint() {
  const manager = document.querySelector(".profile-management");
  if (manager) {
    const open = !new URLSearchParams(location.search).get("evaluation_id");
    if (manager.dataset.context !== String(open)) {
      manager.open = open;
      manager.dataset.context = String(open);
    }
  }
  for (const card of document.querySelectorAll(".profile-card")) {
    const details = card.querySelector(":scope>details");
    const repeated = [...card.querySelectorAll(":scope>p")].find(
      (p) => p.textContent === "Validación humana pendiente.",
    );
    if (repeated && details) details.append(repeated);
  }
  for (const panel of document.querySelectorAll(".pausePanel")) {
    if (panel.querySelector(".interval-guide")) continue;
    const paragraphs = [...panel.querySelectorAll(":scope>p")].filter(
      (p) => !p.dataset.p,
    );
    const secondary = paragraphs.slice(1);
    if (!secondary.length) continue;
    const details = document.createElement("details");
    details.className = "interval-guide";
    const summary = document.createElement("summary");
    summary.textContent =
      "Criterios de revisión: dudas, interferencias y muestras";
    details.append(summary);
    panel.append(details);
    for (const p of secondary) details.append(p);
  }

  for (const a of document.querySelectorAll(
    "main>nav a[data-evaluation-task]",
  )) {
    if (a.dataset.evaluationTask === active) set(a, "aria-current", "page");
    else if (a.getAttribute("aria-current") === "page")
      a.removeAttribute("aria-current");
  }
  for (const slot of document.querySelectorAll("#attempts>section")) {
    const source = read(slot.querySelector(".audit")).response,
      pauses = read(slot.querySelector('[data-p="audit"]')).current_response;
    const finished = {
      recording: !!source?.context?.selection_confirmed,
      content: !!source?.review?.confirmed,
      pauses: ["confirmed", "not_evaluable"].includes(
        pauses?.temporal_review?.status,
      ),
      prosody: ["completed", "partial", "not_evaluable"].includes(
        slot.querySelector(".prosodyPanel")?.dataset.status,
      ),
    };
    for (const [i, b] of [
      ...slot.querySelectorAll("[data-phrase-step]"),
    ].entries()) {
      const status =
        b.getAttribute("aria-current") === "step"
          ? "current"
          : b.disabled
            ? "locked"
            : finished[b.dataset.phraseStep]
              ? "completed"
              : "available";
      const label = {
        current: "Paso actual",
        locked: "Bloqueado",
        completed: "Completado",
        available: "Disponible",
      }[status];
      set(b, "data-step-number", String(i + 1));
      set(b, "data-visual-state", status);
      let note = b.querySelector(".step-state");
      if (!note) {
        note = document.createElement("span");
        note.className = "step-state";
        b.append(note);
      }
      if (note.textContent !== label) note.textContent = label;
    }
  }
  for (const input of document.querySelectorAll(
    '#editTable tbody input[type="number"]',
  ))
    if (!input.getAttribute("aria-label"))
      input.setAttribute("aria-label", "Tiempo del acontecimiento en segundos");
  for (const input of document.querySelectorAll("#editTable tbody select"))
    if (!input.getAttribute("aria-label"))
      input.setAttribute("aria-label", "Etiqueta manual del acontecimiento");
  for (const input of document.querySelectorAll(
    '#editTable tbody input[type="checkbox"]',
  ))
    if (!input.getAttribute("aria-label"))
      input.setAttribute("aria-label", "Reinicio antes del acontecimiento");
  for (const node of document.querySelectorAll(".tableScroll")) {
    set(node, "tabindex", "0");
    set(node, "role", "region");
    if (!node.getAttribute("aria-label"))
      set(
        node,
        "aria-label",
        (node.querySelector("caption")?.textContent.trim() || "Tabla") +
          " · desplazable horizontalmente",
      );
  }
}
let scheduled = false;
const update = () => {
  if (scheduled) return;
  scheduled = true;
  requestAnimationFrame(() => {
    scheduled = false;
    paint();
  });
};
new MutationObserver(update).observe(document.querySelector("main"), {
  childList: true,
  subtree: true,
  attributes: true,
  attributeFilter: ["disabled", "aria-current", "hidden", "data-status"],
});
paint();
