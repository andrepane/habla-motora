import { chromium } from "./browser-runtime.mjs";
import assert from "node:assert/strict";
import fs from "node:fs";
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
for (let attempt = 0; attempt < 30; attempt++) {
  try {
    if ((await fetch(base + "/health")).ok) break;
  } catch {}
  await new Promise((r) => setTimeout(r, 200));
}
const wav = fs.readFileSync(process.env.DDK_TEST_WAV || "/tmp/ddk-clean.wav");
const browser = await chromium.launch({
  headless: true,
  args: [
    "--use-fake-device-for-media-stream",
    "--use-fake-ui-for-media-stream",
  ],
});
let checks = 0;
const check = (v) => {
  assert.ok(v);
  checks++;
};
try {
  const context = await browser.newContext({
    permissions: ["microphone", "clipboard-read", "clipboard-write"],
    acceptDownloads: true,
  });
  const page = await context.newPage(),
    errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(base + "/ddk");
  check((await page.title()).includes("DDK"));
  await page
    .locator("#file")
    .setInputFiles({
      name: "synthetic.wav",
      mimeType: "audio/wav",
      buffer: wav,
    });
  await page.waitForFunction(
    () => !document.getElementById("analyze").disabled,
  );
  const request = page.waitForRequest((r) => r.url().endsWith("/ddk-analysis"));
  await page.locator("#analyze").click();
  await request;
  await page.locator("#results").waitFor({ state: "visible" });
  check(
    (await page.locator("#automaticCards").textContent()).includes(
      "Núcleos candidatos",
    ),
  );
  check((await page.locator("#editTable tbody tr").count()) === 21);
  check((await page.locator("#energyChart circle").count()) > 20);
  check(
    (await page.locator("#stageState").textContent()).includes("not_requested"),
  );
  const original = JSON.parse(await page.locator("#technical").textContent())
    .response.automatic_original.detection;
  const first = original.events[0].id;
  await page.locator("#anchor").selectOption(first);
  check(await page.locator("#reviewSection").isHidden());
  await page.locator("#group").click();
  await page.locator("#reviewSection").waitFor({ state: "visible" });
  check((await page.locator("#groupInfo").textContent()).includes("7 tríadas"));
  check(
    JSON.stringify(
      JSON.parse(await page.locator("#technical").textContent()).response
        .automatic_original.detection,
    ) === JSON.stringify(original),
  );
  // Acknowledgement alone cannot turn unknown labels into reviewed phonetic identity.
  await page.locator("#confirmed").check();
  await page.locator("#calculateReview").click();
  await page.waitForFunction(() =>
    document.getElementById("status").textContent.includes("etiquetas"),
  );
  check(await page.locator("#reviewedCards").isHidden());
  await page.locator("#confirmed").uncheck();
  // Synthetic fixture labels are imposed manually only to verify review mechanics, not speech recognition.
  for (let i = 0; i < 21; i++)
    await page
      .locator("#editTable tbody tr")
      .nth(i)
      .locator("select")
      .selectOption(["pa", "ta", "ka"][i % 3]);
  await page.locator("#calculateReview").click();
  await page.waitForFunction(() =>
    document.getElementById("status").textContent.includes("completado"),
  );
  check(await page.locator("#reviewedCards").isHidden());
  await page.locator("#addTime").fill("0.1");
  await page.locator("#addEvent").click();
  check((await page.locator("#editTable tbody tr").count()) === 22);
  await page
    .locator("#editTable tbody tr")
    .first()
    .getByRole("button", { name: "Eliminar" })
    .click();
  const oldTime = original.events[0].time_s;
  const t = page
    .locator("#editTable tbody tr")
    .first()
    .locator("input[type=number]");
  await t.fill(String(oldTime + 0.005));
  await t.dispatchEvent("change");
  await page
    .locator("#editTable tbody tr")
    .nth(6)
    .locator("input[type=checkbox]")
    .check();
  await page.locator("#confirmed").check();
  await page.locator("#calculateReview").click();
  await page.locator("#reviewedCards").waitFor({ state: "visible" });
  check(
    (await page.locator("#reviewedCards").textContent()).includes(
      "Sílabas revisadas",
    ),
  );
  let exported = JSON.parse(await page.locator("#technical").textContent());
  check(exported.response.reviewed_result.metrics.group_count.value === 7);
  check(
    exported.response.reviewed_result.metrics.excluded_group_transitions
      .length === 1,
  );
  check(
    JSON.stringify(exported.response.automatic_original.detection) ===
      JSON.stringify(original),
  );
  check(exported.response.manual_modifications.operations.length === 25);
  check((await page.locator("#eventChart line").count()) > 20);
  check((await page.locator("#intervalTable tbody tr").count()) > 20);
  await page.locator("#copy").click();
  check(
    (await page.evaluate(() => navigator.clipboard.readText())).includes(
      "revisados",
    ),
  );
  const downloadPromise = page.waitForEvent("download");
  await page.locator("#json").click();
  const download = await downloadPromise;
  const downloadPath = await download.path();
  check(
    JSON.parse(fs.readFileSync(downloadPath, "utf8")).response.provenance
      .file_sha256 === exported.response.provenance.file_sha256,
  );
  await page.screenshot({
    path: process.env.DDK_SCREENSHOT || "/tmp/ddk-interface.png",
    fullPage: true,
  });
  // Editing immediately invalidates reviewed metrics, including during a pending request.
  await page
    .locator("#editTable tbody tr")
    .first()
    .locator("select")
    .selectOption("other");
  check(await page.locator("#reviewedCards").isHidden());
  await page.locator("#discardReview").click();
  check(
    JSON.parse(await page.locator("#technical").textContent()).pending_review
      .operations.length === 0,
  );
  check(
    (await page
      .locator("#editTable tbody tr")
      .first()
      .locator("select")
      .inputValue()) === "unknown",
  );
  let release;
  const gate = new Promise((r) => (release = r));
  await page.route("**/ddk-analysis", async (route) => {
    await gate;
    await route.fulfill({ json: exported.response }).catch(() => {});
  });
  await page.locator("#analyze").click();
  await page.locator("#start").fill(".1");
  release();
  await page.waitForTimeout(150);
  check(await page.locator("#results").isHidden());
  await page.unroute("**/ddk-analysis");
  const silence = Buffer.from(wav);
  silence.fill(0, 44);
  await page
    .locator("#file")
    .setInputFiles({
      name: "silence.wav",
      mimeType: "audio/wav",
      buffer: silence,
    });
  await page.waitForFunction(
    () => !document.getElementById("analyze").disabled,
  );
  await page.locator("#analyze").click();
  await page.locator("#results").waitFor({ state: "visible" });
  check((await page.locator("#stageState").textContent()).includes("empty"));
  check(
    (await page.locator("#automaticCards").textContent()).includes(
      "No calculable",
    ),
  );
  const failed = JSON.parse(
    await page.locator("#technical").textContent(),
  ).response;
  failed.stages.detection = {
    status: "failed",
    reason: "detector_failed",
    message: "Fallo de prueba",
  };
  failed.stages.grouping = { status: "blocked" };
  failed.stages.calculation = { status: "blocked" };
  failed.automatic_original.metrics.event_count = {
    value: null,
    reason: "detector_failed",
  };
  await page.route("**/ddk-analysis", (route) =>
    route.fulfill({ json: failed }),
  );
  await page.locator("#analyze").click();
  await page.waitForFunction(() =>
    document.getElementById("stageState").textContent.includes("failed"),
  );
  check(
    (await page.locator("#warnings").textContent()).includes("Fallo de prueba"),
  );
  check(await page.locator("#reviewedCards").isHidden());
  await page.unroute("**/ddk-analysis");
  await page
    .locator("#file")
    .setInputFiles({
      name: "invalid.wav",
      mimeType: "audio/wav",
      buffer: Buffer.from("invalid"),
    });
  await page.waitForFunction(() =>
    document.getElementById("status").textContent.includes("inválido"),
  );
  check(await page.locator("#analyze").isDisabled());
  await page
    .locator("#file")
    .setInputFiles({
      name: "big.wav",
      mimeType: "audio/wav",
      buffer: Buffer.alloc(4000001),
    });
  await page.waitForFunction(() =>
    document.getElementById("status").textContent.includes("4.000.000"),
  );
  check(await page.locator("#analyze").isDisabled());
  await page.locator("#record").click();
  await page.waitForFunction(() =>
    document.getElementById("status").textContent.includes("Grabando · 1.0"),
  );
  await page.locator("#stop").click();
  await page.waitForFunction(
    () => !document.getElementById("analyze").disabled,
  );
  check(
    JSON.parse(await page.locator("#captureInfo").textContent())
      .requested_constraints.autoGainControl === false,
  );
  check(await page.locator("#downloadAudio").isVisible());
  await page.locator("#analyze").click();
  await page.locator("#results").waitFor({ state: "visible" });
  check(
    (await page.locator("#automaticCards").textContent()).includes(
      "Núcleos candidatos",
    ),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  check(errors.length === 0);
  console.log(
    `${checks} DDK browser checks passed (real API, synthetic audio/microphone, audit, manual replay, exports, invalidation, mobile).`,
  );
} finally {
  await browser.close();
}
