import { createRequire } from "node:module";
const { chromium } = createRequire(import.meta.url)("playwright");
import assert from "node:assert/strict";
import fs from "node:fs";
import { createHash } from "node:crypto";
const base = process.env.BASE_URL || "http://127.0.0.1:8000";
for (let attempt = 0; attempt < 30; attempt++) {
  try {
    if ((await fetch(base + "/health")).ok) break;
  } catch {}
  await new Promise((resolve) => setTimeout(resolve, 200));
}
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
  await page.goto(base);
  check((await page.title()) === "Evaluación de vocal sostenida");
  await page.locator("#file").setInputFiles({
    name: "vocal.wav",
    mimeType: "audio/wav",
    buffer: fs.readFileSync(process.env.TEST_WAV || "/tmp/vocal-6s.wav"),
  });
  await page.waitForFunction(
    () => !document.getElementById("analyze").disabled,
  );
  check(
    (await page.locator("#selection").textContent()).includes("1.500–4.500"),
  );
  const req = page.waitForRequest((r) => r.url().endsWith("/vowel-analysis"));
  await page.locator("#analyze").click();
  const request = await req;
  check(request.method() === "POST");
  await page.locator("#results").waitFor({ state: "visible" });
  check((await page.locator(".card").count()) === 5);
  check((await page.locator("#pitchChart path").count()) > 0);
  check((await page.locator("#hnrChart path").count()) > 0);
  await page.locator("#copy").click();
  check(
    (await page.evaluate(() => navigator.clipboard.readText())).includes(
      "F0 media",
    ),
  );
  const downloaded = page.waitForEvent("download");
  await page.locator("#json").click();
  const download = await downloaded;
  const file = await download.path();
  const response = JSON.parse(fs.readFileSync(file, "utf8"));
  check(response.status === "completed");
  check(
    response.input.file_sha256 ===
      createHash("sha256")
        .update(fs.readFileSync(process.env.TEST_WAV || "/tmp/vocal-6s.wav"))
        .digest("hex"),
  );
  await page.screenshot({
    path: process.env.SCREENSHOT || "/tmp/vowel-interface.png",
    fullPage: true,
  });
  await page.locator("#start").fill("1");
  check(await page.locator("#results").isHidden());
  await page.locator("#end").fill("2");
  check(await page.locator("#analyze").isDisabled());
  // UI must preserve native negatives, zeros, nulls and module failures.
  const mock = structuredClone(response);
  mock.modules.hnr.result.acoustic.hnr_mean_db.value = -10;
  mock.modules.shimmer.result.acoustic.f0_sd_hz.value = 0;
  mock.modules.shimmer.result.acoustic.jitter_local_percent = {
    value: null,
    reason: "praat_undefined",
  };
  await page.route("**/vowel-analysis", (route) =>
    route.fulfill({ json: mock }),
  );
  await page.locator("#start").fill("0");
  await page.locator("#end").fill("6");
  await page.locator("#analyze").click();
  await page.locator("#results").waitFor({ state: "visible" });
  check((await page.locator(".card").nth(4).textContent()).includes("-10"));
  check((await page.locator(".card").nth(1).textContent()).includes("0"));
  check(
    (await page.locator(".card").nth(2).textContent()).includes(
      "No calculable",
    ),
  );
  mock.status = "partial";
  mock.modules.hnr = {
    status: "failed",
    result: null,
    error: {
      code: "ANALYSIS_FAILED",
      message: "Praat execution failed or timed out",
    },
  };
  await page.locator("#analyze").click();
  await page.locator("#results").waitFor({ state: "visible" });
  check((await page.locator("#resultState").textContent()).includes("parcial"));
  check(
    (await page.locator(".card").nth(4).textContent()).includes(
      "Módulo hnr fallido",
    ),
  );
  await page.unroute("**/vowel-analysis");
  let release;
  const gate = new Promise((r) => (release = r));
  await page.route("**/vowel-analysis", async (route) => {
    await gate;
    await route.fulfill({ json: response }).catch(() => {});
  });
  await page.locator("#analyze").click();
  await page.locator("#start").fill(".5");
  release();
  await page.waitForTimeout(200);
  check(await page.locator("#results").isHidden());
  await page.unroute("**/vowel-analysis");
  await page.locator("#file").setInputFiles({
    name: "invalid.wav",
    mimeType: "audio/wav",
    buffer: Buffer.from("invalid"),
  });
  await page.waitForFunction(() =>
    document.getElementById("status").textContent.includes("inválido"),
  );
  check(await page.locator("#analyze").isDisabled());
  await page.locator("#record").click();
  await page.waitForFunction(() =>
    document
      .getElementById("status")
      .textContent.includes("Grabando /a/ · 3.5"),
  );
  await page.locator("#stop").click();
  await page.waitForFunction(
    () => !document.getElementById("analyze").disabled,
  );
  const capture = JSON.parse(await page.locator("#captureInfo").textContent());
  check(capture.requested_constraints.autoGainControl === false);
  check([44100, 48000].includes(capture.audio_context_sample_rate));
  check(await page.locator("#downloadAudio").isVisible());
  await page.locator("#analyze").click();
  await page.locator("#results").waitFor({ state: "visible" });
  check((await page.locator(".card").count()) === 5);
  await page.setViewportSize({ width: 390, height: 844 });
  check(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  check(errors.length === 0);
  console.log(
    `${checks} browser checks passed (real API, synthetic microphone, partial results, invalidation, export, mobile).`,
  );
} finally {
  await browser.close();
}
