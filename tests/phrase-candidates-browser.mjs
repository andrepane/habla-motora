import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs";
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
const bytes = fs.readFileSync(
  process.env.CANDIDATE_TEST_WAV || "/tmp/phrase-candidates.wav",
);
const browser = await chromium.launch({ headless: true });
let checks = 0;
const check = (x) => assert.ok(x, `7B.2 browser check ${++checks}`);
try {
  const page = await browser.newPage({ acceptDownloads: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let calls = 0;
  page.on("request", (r) => {
    if (r.url().endsWith("/phrase-candidates")) calls++;
  });
  await page.goto(base + "/phrase");
  const card = page.locator("#attempt1");
  const f = (k) => card.locator(`[data-f="${k}"]`),
    c = (k) => card.locator(`[data-c="${k}"]`),
    p = (k) => card.locator(`[data-p="${k}"]`);
  const audit = async () => JSON.parse(await c("audit").textContent());
  const manual = async () => JSON.parse(await p("audit").textContent());
  const source = async () =>
    JSON.parse(await card.locator(".audit").textContent()).response;
  await f("file").setInputFiles({
    name: "controlled.wav",
    mimeType: "audio/wav",
    buffer: bytes,
  });
  await card.locator(".state").filter({ hasText: "WAV conservado" }).waitFor();
  await f("selectionConfirmed").check();
  await card.locator(".analyze").click();
  await card
    .locator(".state")
    .filter({ hasText: "Selección: completed" })
    .waitFor();
  check(calls === 0);
  await f("production").selectOption("present");
  await f("match").selectOption("exact_once");
  await f("words").fill("14");
  await f("wordsConfirmed").check();
  await f("syllables").fill("25");
  await f("syllablesConfirmed").check();
  await f("reviewConfirmed").check();
  await card.locator(".submitReview").click();
  await card
    .locator(".state")
    .filter({ hasText: "Revisión: completed" })
    .waitFor();
  const originalSource = await source();
  await p("confirmed").check();
  await p("calculate").click();
  await p("state").filter({ hasText: "Cálculo: completed" }).waitFor();
  const initialManual = await manual();
  const run = async () => {
    await c("run").click();
    await c("state").filter({ hasText: "Completado:" }).waitFor();
    return audit();
  };
  let a = await run();
  check(a.automatic_candidates.length >= 2);
  await page.setViewportSize({ width: 390, height: 844 });
  await c("run").scrollIntoViewIfNeeded();
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path:
      process.env.CANDIDATE_SCREENSHOT || "/tmp/phrase-candidates-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1280, height: 900 });
  const originals = JSON.stringify(a.automatic_candidates);
  check(
    JSON.stringify((await manual()).current_response) ===
      JSON.stringify(initialManual.current_response),
  );
  check(
    (await card.locator(".candidateOverlay rect").count()) ===
      a.automatic_candidates.length,
  );
  let rows = card.locator("[data-candidate-id]");
  await rows
    .nth(0)
    .getByRole("button", { name: "Rechazar", exact: true })
    .click();
  check((await audit()).candidate_decisions[0].action === "rejected");
  check(
    JSON.stringify((await manual()).current_response) ===
      JSON.stringify(initialManual.current_response),
  );
  await rows
    .nth(1)
    .getByRole("button", { name: "Copiar a revisión manual", exact: true })
    .click();
  check(
    (await manual()).temporal_draft.intervals[0].classification === "uncertain",
  );
  check((await manual()).current_response === null);
  check(!(await p("confirmed").isChecked()));
  check(JSON.stringify((await audit()).automatic_candidates) === originals);
  check(
    (await audit()).candidate_manual_links[0].manual_annotation_id === "p1",
  );
  check((await card.getByRole("button", { name: /Aceptar/ }).count()) === 0);
  await run();
  check((await manual()).temporal_draft.intervals.length === 1);
  check((await audit()).history.some((h) => h.candidate_manual_links?.length));
  rows = card.locator("[data-candidate-id]");
  const first = (await audit()).automatic_candidates[0];
  await rows
    .nth(0)
    .locator('[data-bound="start_sample"]')
    .fill(String(first.start_sample + 1));
  await rows
    .nth(0)
    .getByRole("button", { name: "Editar límites y copiar", exact: true })
    .click();
  a = await audit();
  check(
    a.candidate_manual_links[0].original_bounds.start_sample ===
      first.start_sample,
  );
  check(
    a.candidate_manual_links[0].edited_bounds.start_sample ===
      first.start_sample + 1,
  );
  check(
    (await manual()).temporal_draft.intervals[1].classification === "uncertain",
  );
  await rows
    .nth(0)
    .getByRole("button", { name: "Ampliar candidato", exact: true })
    .click();
  check(
    Number(await card.locator(".wave").getAttribute("data-start-sample")) <
      first.start_sample,
  );
  await rows
    .nth(0)
    .getByRole("button", {
      name: "Escuchar candidato con contexto",
      exact: true,
    })
    .click();
  check((await card.locator(".audio").evaluate((x) => x.currentTime)) > 0);
  // Manual edits leave original automatic evidence intact.
  const before = JSON.stringify((await audit()).automatic_candidates);
  await card
    .locator('[data-interval-id="p1"] [data-key="note"]')
    .fill("manual");
  check(JSON.stringify((await audit()).automatic_candidates) === before);
  check(JSON.stringify(await source()) === JSON.stringify(originalSource));
  const download = page.waitForEvent("download");
  await page.locator("#exportAll").click();
  const d = await download;
  const exported = JSON.parse(fs.readFileSync(await d.path(), "utf8"));
  check(
    exported.attempts[0].candidate_review_7b2.candidate_manual_links.length ===
      1,
  );
  check(
    exported.attempts[0].candidate_review_7b2.history.some((h) =>
      h.candidate_decisions?.some((d) => d.action === "rejected"),
    ),
  );
  check(exported.attempts[0].pause_review_7b1.current_response === null);
  await f("start").fill("1");
  check((await audit()).automatic_candidates === null);
  check((await audit()).status === "stale");
  await page.locator("#tab2").click();
  check(
    (await page.locator('#attempt2 [data-c="state"]').textContent()) ===
      "Desactivado: se ejecuta únicamente al pulsar el botón.",
  );
  await page.locator("#tab1").click();
  // A new WAV invalidates; not_evaluable and failed are never empty successful lists.
  const silent = Buffer.from(bytes);
  silent.fill(0, 44);
  await f("file").setInputFiles({
    name: "silence.wav",
    mimeType: "audio/wav",
    buffer: silent,
  });
  await card.locator(".state").filter({ hasText: "WAV conservado" }).waitFor();
  await f("selectionConfirmed").check();
  await card.locator(".analyze").click();
  await card
    .locator(".state")
    .filter({ hasText: "Selección: completed" })
    .waitFor();
  await c("run").click();
  await c("state").filter({ hasText: "No evaluable:" }).waitFor();
  check((await audit()).automatic_candidates === null);
  await page.route("**/phrase-candidates", (route) =>
    route.fulfill({
      json: {
        status: "failed",
        reason: "execution_failed",
        automatic_candidates: null,
      },
    }),
  );
  await c("run").click();
  await c("state").filter({ hasText: "No se pudo completar" }).waitFor();
  check((await audit()).automatic_candidates === null);
  await page.unroute("**/phrase-candidates");
  // Explicit successful empty output does not supply a manual result or confirmation.
  await page.route("**/phrase-candidates", (route) =>
    route.fulfill({
      json: {
        status: "completed",
        automatic_candidates: [],
        dependencies: {},
        original_execution: { run_id: "empty" },
      },
    }),
  );
  await c("run").click();
  await c("state").filter({ hasText: "Completado: 0" }).waitFor();
  check((await audit()).manual_final_result === null);
  check(!(await p("confirmed").isChecked()));
  await page.unroute("**/phrase-candidates");
  await f("modality").selectOption("auditory_model_with_text_v1");
  check((await audit()).status === "stale");
  check(errors.length === 0);
  console.log(`7B.2 browser: ${checks} checks passed`);
} finally {
  await browser.close();
}
