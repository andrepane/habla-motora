import { chromium } from "./browser-runtime.mjs";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createHash } from "node:crypto";
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
const bytes = fs.readFileSync(
  process.env.PHRASE_TEST_WAV || "/tmp/phrase-8s.wav",
);
const hash = (b) => createHash("sha256").update(b).digest("hex");
const browser = await chromium.launch({ headless: true });
let checks = 0;
const check = (x) => {
  assert.ok(x, `7B.1 browser check ${++checks}`);
};
try {
  const page = await browser.newPage({ acceptDownloads: true });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(base + "/phrase");
  const card = page.locator("#attempt1"),
    other = page.locator("#attempt2");
  const f = (k) => card.locator(`[data-f="${k}"]`),
    p = (k) => card.locator(`[data-p="${k}"]`);
  const source = async () =>
    JSON.parse(await card.locator(".audit").textContent()).response;
  const audit = async () => JSON.parse(await p("audit").textContent());
  const calculate = async (status) => {
    await p("calculate").click();
    await p("state").filter({ hasText: status }).waitFor();
    return (await audit()).current_response;
  };
  await f("file").setInputFiles({
    name: "synthetic.wav",
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
  const original = await source();
  check(original.rates.reference_word_rate.value === 105);
  let out = await calculate("Cálculo: blocked");
  check(Object.values(out.metrics).every((m) => m.value === null));
  await p("confirmed").check();
  out = await calculate("Cálculo: completed");
  check(out.metrics.pause_count.value === 0);
  check(out.metrics.pause_duration_s.value === 0);
  check(out.metrics.pause_mean_duration_s.reason === "no_pauses");
  check(out.metrics.pause_median_duration_s.value === null);
  check(out.metrics.operational_speech_time_s.value === 8);
  check(out.metrics.reviewed_syllable_articulation_rate.value === 3.125);
  const add = async (a, b) => {
    await p("start").fill(String(a));
    await p("end").fill(String(b));
    await p("add").click();
    return card.locator("[data-interval-id]").last();
  };
  let row = await add(48000, 72000);
  const e = (k) => row.locator(`[data-key="${k}"]`);
  check(!(await p("confirmed").isChecked()));
  check((await p("metrics").locator(".metric").count()) === 0);
  check((await e("classification").inputValue()) === "uncertain");
  check((await card.locator(".wave .pauseOverlay rect").count()) === 1);
  await p("confirmed").check();
  await calculate("Error:");
  check((await audit()).current_response === null);
  await e("classification").selectOption("pause");
  await e("breath_present").selectOption("yes");
  await e("within_word").check();
  await p("confirmed").check();
  await calculate("Error:");
  check((await p("state").textContent()).includes("Intrapalabra"));
  await e("nonarticulatory_confirmed").check();
  await p("confirmed").check();
  out = await calculate("Cálculo: completed");
  check(out.metrics.pause_duration_s.value === 0.5);
  check(out.metrics.operational_speech_time_s.value === 7.5);
  check(out.metrics.pause_percent.value === 6.25);
  check(out.metrics.reviewed_word_articulation_rate.value === 112);
  check(out.metrics.reviewed_syllable_articulation_rate.value === 25 / 7.5);
  check(JSON.stringify(await source()) === JSON.stringify(original));
  check(JSON.stringify(out.source_7a) === JSON.stringify(original));
  await row
    .getByRole("button", { name: "Ampliar intervalo", exact: true })
    .click();
  check(
    (await card.locator(".wave").getAttribute("data-start-sample")) === "48000",
  );
  check(
    (await card.locator(".wave").getAttribute("data-end-sample")) === "72000",
  );
  await row
    .getByRole("button", { name: "Escuchar con contexto", exact: true })
    .click();
  await page.waitForFunction(
    () => !document.querySelector("#attempt1 .audio").paused,
  );
  check(
    await card
      .locator(".audio")
      .evaluate((a) => a.currentTime >= 0.75 && a.currentTime < 2),
  );
  await card.locator(".audio").evaluate((a) => a.pause());
  await card.locator(".zoomReset").click();
  await p("editing").check();
  await card.locator(".wave").scrollIntoViewIfNeeded();
  const wave = await card.locator(".wave").boundingBox();
  await page.mouse.move(wave.x + wave.width * 0.3, wave.y + 40);
  await page.mouse.down();
  await page.mouse.move(wave.x + wave.width * 0.4, wave.y + 40);
  await page.mouse.up();
  check(Number(await p("start").inputValue()) > 100000);
  check(JSON.stringify(await source()) === JSON.stringify(original));
  await p("editing").uncheck();
  const second = await add(144000, 216000);
  await second
    .locator('[data-key="classification"]')
    .selectOption("other_nonverbal");
  await p("status").selectOption("not_evaluable");
  await p("note").fill("Voz ajena: región no evaluable.");
  out = await calculate("Cálculo: blocked");
  check(out.temporal_review.status === "not_evaluable");
  check(Object.values(out.metrics).every((m) => m.value === null));
  check(out.audit.accepted_pause_samples_partial === 24000);
  check(out.audit.partial_evidence_is_not_global_summary);
  await p("confirmed").check();
  await calculate("Error:");
  check((await audit()).current_response === null);
  await second.locator('[data-key="classification"]').selectOption("pause");
  await p("confirmed").check();
  out = await calculate("Cálculo: completed");
  check(out.metrics.pause_count.value === 2);
  check(out.metrics.pause_duration_s.value === 2);
  check(out.metrics.pause_median_duration_s.value === 1);
  check(out.metrics.operational_speech_time_s.value === 6);
  check(out.metrics.reviewed_word_articulation_rate.value === 140);
  // Boundary edit invalidates both metrics and confirmation, server rejects overlap.
  await second.locator('[data-key="start_sample"]').fill("60000");
  check(!(await p("confirmed").isChecked()));
  await p("confirmed").check();
  await calculate("Error:");
  check((await p("state").textContent()).includes("solapados"));
  await second.locator('[data-key="start_sample"]').fill("144000");
  await p("confirmed").check();
  await calculate("Cálculo: completed");
  // Complete export holds identical audio, 7A response, temporal result and history.
  const downloading = page.waitForEvent("download");
  await page.locator("#exportAll").click();
  const saved = JSON.parse(
    fs.readFileSync(await (await downloading).path(), "utf8"),
  );
  check(
    hash(Buffer.from(saved.attempts[0].wav_base64, "base64")) === hash(bytes),
  );
  check(
    saved.attempts[0].pause_review_7b1.current_response.metrics.pause_count
      .value === 2,
  );
  check(
    saved.attempts[0].pause_review_7b1.history.some(
      (h) => h.event === "invalidated",
    ),
  );
  check(saved.attempts[1].pause_review_7b1.current_response === null);
  check(
    saved.attempts[0].current_response.rates.reference_word_rate.value === 105,
  );
  const trial = saved.attempts[0],
    replay = new FormData();
  replay.append(
    "file",
    new Blob([Buffer.from(trial.wav_base64, "base64")]),
    "replay.wav",
  );
  replay.append("context_json", JSON.stringify(trial.current_response.context));
  replay.append("review_json", JSON.stringify(trial.current_response.review));
  replay.append(
    "expected_file_sha256",
    trial.current_response.provenance.file_sha256,
  );
  replay.append(
    "temporal_json",
    JSON.stringify(trial.pause_review_7b1.current_response.temporal_review),
  );
  const replayResponse = await fetch(base + "/phrase-pause-analysis", {
    method: "POST",
    body: replay,
  });
  check(replayResponse.ok);
  const reproduced = await replayResponse.json();
  check(
    JSON.stringify(reproduced.metrics) ===
      JSON.stringify(trial.pause_review_7b1.current_response.metrics),
  );
  check(
    reproduced.provenance.temporal_review_sha256 ===
      trial.pause_review_7b1.current_response.provenance.temporal_review_sha256,
  );
  await page.locator("#tab2").click();
  check((await other.locator('[data-p="rows"] fieldset').count()) === 0);
  await page.locator("#tab1").click();
  check((await p("rows").locator("fieldset").count()) === 2);
  // Re-running unreviewed 7A replaces source and invalidates 7B even without field edits.
  await card.locator(".analyze").click();
  await card
    .locator(".state")
    .filter({ hasText: "Revisión: not_requested" })
    .waitFor();
  check((await audit()).current_response === null);
  check(!(await p("confirmed").isChecked()));
  check((await p("rows").locator("fieldset").count()) === 0);
  // Content edits invalidate all temporal dependencies, never overwrite 7A counts.
  await f("reviewConfirmed").check();
  await card.locator(".submitReview").click();
  await card
    .locator(".state")
    .filter({ hasText: "Revisión: completed" })
    .waitFor();
  row = await add(48000, 72000);
  await e("classification").selectOption("pause");
  await p("confirmed").check();
  await calculate("Cálculo: completed");
  await f("notes").fill("Nueva revisión");
  check((await audit()).current_response === null);
  check((await p("rows").locator("fieldset").count()) === 0);
  check((await f("words").inputValue()) === "14");
  // Modality/source edits clear temporal state even if no current 7A result remains.
  row = await add(48000, 72000);
  await f("modality").selectOption("auditory_model_only_v1");
  check((await p("rows").locator("fieldset").count()) === 0);
  check((await audit()).current_response === null);
  check(!(await card.locator(".stimulus").isVisible()));
  check((await card.locator(".wave .pauseOverlay rect").count()) === 0);
  await f("modality").selectOption("direct_reading_v1");
  await page.setViewportSize({ width: 390, height: 844 });
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: process.env.PAUSE_SCREENSHOT || "/tmp/phrase-pauses-interface.png",
    fullPage: true,
  });
  check(errors.length === 0 || (console.log(errors), false));
  console.log(
    `${checks} 7B.1 browser checks passed (real API, manual intervals, intraword safeguard, global interference blocking, exact samples, unchanged 7A, invalidation, two attempts, export, mobile).`,
  );
} finally {
  await browser.close();
}
