import { chromium } from "playwright";
import assert from "node:assert/strict";
import fs from "node:fs";
import { createHash } from "node:crypto";
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
for (let i = 0; i < 40; i++) {
  try {
    if ((await fetch(base + "/health")).ok) break;
  } catch {}
  await new Promise((r) => setTimeout(r, 200));
}
const bytes = fs.readFileSync(
  process.env.PHRASE_TEST_WAV || "/tmp/phrase-8s.wav",
);
const hash = (b) => createHash("sha256").update(b).digest("hex");
const browser = await chromium.launch({
  headless: true,
  args: [
    "--use-fake-device-for-media-stream",
    "--use-fake-ui-for-media-stream",
  ],
});
let checks = 0;
const check = (x) => {
  assert.ok(x, `Browser check ${checks + 1}`);
  checks++;
};
try {
  const ctx = await browser.newContext({
    permissions: ["microphone"],
    acceptDownloads: true,
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(base + "/phrase");
  const card = page.locator("#attempt1"),
    other = page.locator("#attempt2");
  const field = (key, c = card) => c.locator(`[data-f="${key}"]`);
  const click = (cls, c = card) => c.locator("." + cls).click();
  const upload = async (c = card) => {
    await field("file", c).setInputFiles({
      name: "synthetic.wav",
      mimeType: "audio/wav",
      buffer: bytes,
    });
    await c.locator(".state").filter({ hasText: "WAV conservado" }).waitFor();
  };
  const analyze = async (c = card) => {
    await field("selectionConfirmed", c).check();
    await click("analyze", c);
    await c
      .locator(".state")
      .filter({ hasText: "Selección: completed" })
      .waitFor();
  };
  const submit = async (c = card) => {
    await field("reviewConfirmed", c).check();
    await click("submitReview", c);
    await c
      .locator(".state")
      .filter({ hasText: "Revisión: completed" })
      .waitFor();
  };
  const audit = async (c = card) =>
    JSON.parse(await c.locator(".audit").textContent());
  check((await page.title()).includes("7A"));
  check((await field("modality").inputValue()) === "direct_reading_v1");
  check(await card.locator(".stimulus").isVisible());
  check(
    (await card.locator(".instruction").textContent()).startsWith(
      "Lee esta frase",
    ),
  );
  check((await field("words").inputValue()) === "");
  check((await field("syllables").inputValue()) === "");
  await upload();
  check((await card.locator(".wave path").count()) === 1);
  await analyze();
  let a = await audit();
  check(a.response.selected_duration_s.value === 8);
  check(Object.values(a.response.rates).every((x) => x.value === null));
  check(a.response.provenance.file_sha256 === hash(bytes));
  await field("production").selectOption("present");
  await field("match").selectOption("exact_once");
  await submit();
  a = await audit();
  check(a.response.rates.reference_word_rate.value === 105);
  check(a.response.rates.reference_syllable_rate.value === 3.125);
  check(a.response.rates.reviewed_word_rate.value === null);
  check(a.response.rates.reviewed_syllable_rate.value === null);
  await field("words").fill("14");
  check((await card.locator(".results .metric").count()) === 0);
  await field("wordsConfirmed").check();
  await submit();
  a = await audit();
  check(a.response.rates.reviewed_word_rate.value === 105);
  check(a.response.rates.reviewed_syllable_rate.value === null);
  await field("syllables").fill("25");
  await field("syllablesConfirmed").check();
  await submit();
  a = await audit();
  check(a.response.stages.calculation.status === "completed");
  await field("start").fill("48000");
  await field("end").fill("96000");
  await click("zoomSelection");
  check(
    (await card.locator(".wave").getAttribute("data-start-sample")) === "48000",
  );
  check(
    (await card.locator(".wave").getAttribute("data-end-sample")) === "96000",
  );
  await click("zoomReset");
  check(
    (await card.locator(".wave").getAttribute("data-end-sample")) === "384000",
  );
  await field("start").fill("0");
  await field("end").fill("384000");
  await analyze();
  await field("production").selectOption("present");
  await field("words").fill("14");
  await field("wordsConfirmed").check();
  await field("syllables").fill("25");
  await field("syllablesConfirmed").check();
  // Same counts but different sequence: manual mismatch gates references only.
  await field("match").selectOption("different");
  await field("events").fill("substitution: secuencia diferente");
  await submit();
  a = await audit();
  check(a.response.rates.reference_word_rate.reason === "target_mismatch");
  check(a.response.rates.reference_syllable_rate.value === null);
  check(a.response.rates.reviewed_word_rate.value === 105);
  check(a.response.rates.reviewed_syllable_rate.value === 3.125);
  const firstHash = a.response.provenance.context_sha256;
  await page.locator("#tab2").click();
  await upload(other);
  await analyze(other);
  check((await audit(other)).response.context.attempt === 2);
  check((await audit(other)).response.provenance.context_sha256 !== firstHash);
  await page.locator("#tab1").click();
  check((await audit()).response.rates.reviewed_word_rate.value === 105);
  // Modality changes clear every dependent confirmation/result, not just label.
  await field("modality").selectOption("auditory_model_only_v1");
  check((await card.locator(".results .metric").count()) === 0);
  check(!(await field("wordsConfirmed").isChecked()));
  check((await field("words").inputValue()) === "");
  check(!(await card.locator(".stimulus").isVisible()));
  // Explicit model source; play complete WAV, hash is exported, never TTS.
  await field("model").setInputFiles({
    name: "synthetic-model.wav",
    mimeType: "audio/wav",
    buffer: bytes,
  });
  await card
    .locator(".modelState")
    .filter({ hasText: "Modelo identificado" })
    .waitFor();
  await click("playModel");
  await card
    .locator(".modelState")
    .filter({ hasText: "Modelo reproducido completo" })
    .waitFor();
  await analyze();
  a = await audit();
  check(a.response.context.modality === "auditory_model_only_v1");
  check(a.response.context.administration.model_sha256 === hash(bytes));
  await click("playModel");
  await page.waitForFunction(
    () => !document.querySelector("#attempt1 .modelAudio").paused,
  );
  await field("modality").selectOption("direct_reading_v1");
  check(await card.locator(".modelAudio").evaluate((el) => el.paused));
  check(await card.locator(".stimulus").isVisible());
  // Zero and absence: zero count, null rate, positive observation duration.
  await analyze();
  await field("production").selectOption("absent");
  await field("match").selectOption("different");
  await field("words").fill("0");
  await field("wordsConfirmed").check();
  await field("syllables").fill("0");
  await field("syllablesConfirmed").check();
  await submit();
  a = await audit();
  check(a.response.review.word_count.value === 0);
  check(a.response.rates.reviewed_word_rate.reason === "no_production");
  check(a.response.rates.reviewed_word_rate.value === null);
  check(a.response.selected_duration_s.value === 8);
  // Full export contains original WAV bytes and independent trial identities.
  const downloaded = page.waitForEvent("download");
  await page.locator("#exportAll").click();
  const d = await downloaded;
  const exported = JSON.parse(fs.readFileSync(await d.path(), "utf8"));
  check(
    hash(Buffer.from(exported.attempts[0].wav_base64, "base64")) ===
      hash(bytes),
  );
  check(
    hash(Buffer.from(exported.attempts[1].wav_base64, "base64")) ===
      hash(bytes),
  );
  check(exported.attempts[0].original_assets[0].sha256 === hash(bytes));
  check(exported.aggregation === null);
  check(
    exported.attempts[0].history.some((h) => h.event === "result_invalidated"),
  );
  // WAV original download is byte-identical.
  const wd = page.waitForEvent("download");
  await click("original");
  check(hash(fs.readFileSync(await (await wd).path())) === hash(bytes));
  // Limits invalidate and redraw; HTTP failure is distinct from null or zero.
  await field("end").fill("0");
  await click("analyze");
  await card.locator(".state").filter({ hasText: "Error:" }).waitFor();
  check((await card.locator(".results .metric").count()) === 0);
  await field("end").fill("384000");
  await field("start").fill("");
  await click("analyze");
  await card.locator(".state").filter({ hasText: "Error:" }).waitFor();
  check((await card.locator(".results .metric").count()) === 0);
  // Synthetic microphone, text visible throughout recording, no voice claims.
  await click("record");
  await card
    .locator(".captureState")
    .filter({ hasText: /Ahora:|Grabando/ })
    .waitFor();
  check(await card.locator(".stimulus").isVisible());
  await page.waitForTimeout(650);
  await click("stop");
  await card
    .locator(".captureState")
    .filter({ hasText: "Grabación conservada" })
    .waitFor();
  check((await audit()).capture.encoding === "mono PCM16");
  check((await audit()).results_current === false);
  await page.setViewportSize({ width: 390, height: 844 });
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: process.env.PHRASE_SCREENSHOT || "/tmp/phrase-interface.png",
    fullPage: true,
  });
  check(errors.length === 0 || (console.log(errors), false));
  console.log(
    `${checks} phrase browser checks passed (real API, two attempts, manual independent rates, models, invalidation, byte-identical WAV export, microphone, mobile).`,
  );
} finally {
  await browser.close();
}
