import fs from "node:fs";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url),
  enabled = process.env.VISUAL_AUDIT === "1";
const dir = process.env.VISUAL_EVIDENCE_DIR || "/tmp/h103-visual";
const findings = [];
const reflows = [];
export async function checkpoint(page, name) {
  if (!enabled) return;
  fs.mkdirSync(dir, { recursive: true });
  const original = page.viewportSize();
  for (const width of [1440, 1024, 390, 320]) {
    await page.setViewportSize({ width, height: width < 600 ? 844 : 1000 });
    await page.evaluate(() => document.fonts.ready);
    await page.evaluate(
      () =>
        new Promise((r) =>
          requestAnimationFrame(() => requestAnimationFrame(r)),
        ),
    );
    const geometry = await page.evaluate(() => ({
      viewport: innerWidth,
      document: document.documentElement.scrollWidth,
      overflow: [...document.querySelectorAll("main *")]
        .filter(
          (e) =>
            e.getBoundingClientRect().width &&
            e.getBoundingClientRect().right > innerWidth + 1 &&
            !e.closest(".tableScroll,pre"),
        )
        .slice(0, 8)
        .map((e) => ({
          tag: e.tagName,
          id: e.id,
          cls: e.className,
          width: e.getBoundingClientRect().width,
          right: e.getBoundingClientRect().right,
        })),
    }));
    await page.evaluate(() => scrollTo(0, 0));
    await page.evaluate(() => new Promise((r) => requestAnimationFrame(r)));
    await page.screenshot({
      path: `${dir}/${name}-${width}.png`,
      fullPage: true,
    });
    assert.ok(
      geometry.document <= geometry.viewport,
      `${name} ${width}: page overflow ${JSON.stringify(geometry)}`,
    );
    await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
    for (const table of await page.locator(".tableScroll:visible").all()) {
      assert.equal(
        await table.getAttribute("role"),
        "region",
        "Focusable table scroll region is named semantically",
      );
      assert.ok(await table.getAttribute("aria-label"), "Scroll region label");
    }
    const axe = await page.evaluate(() =>
      axe.run(document, {
        runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
      }),
    );
    const violations = axe.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      description: v.description,
      nodes: v.nodes.map((n) => ({
        target: n.target,
        summary: n.failureSummary,
      })),
    }));
    findings.push({
      screen: name,
      width,
      geometry,
      violations,
      passes: axe.passes.length,
      incomplete: axe.incomplete.map((v) => ({
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    });
    fs.writeFileSync(
      dir + "/accessibility.json",
      JSON.stringify(findings, null, 2),
    );
    assert.equal(
      violations.length,
      0,
      `${name} ${width}: axe ${JSON.stringify(violations)}`,
    );
    // Exercise native keyboard disclosure; restore its initial presentation state.
    const summary = page.locator("details>summary:visible").first();
    if (await summary.count()) {
      const wasOpen = await summary.evaluate((e) => e.parentElement.open);
      await summary.focus();
      await page.keyboard.press("Enter");
      assert.notEqual(
        await summary.evaluate((e) => e.parentElement.open),
        wasOpen,
        `${name}: keyboard disclosure`,
      );
      await page.keyboard.press("Enter");
      assert.equal(
        await summary.evaluate((e) => e.parentElement.open),
        wasOpen,
        `${name}: disclosure restored`,
      );
    }
    // Focus must remain visible, keyboard activation is covered by the actual journey.
    await page.keyboard.press("Tab");
    const nav = page.locator("main>nav a").first();
    await nav.focus();
    const focus = await nav.evaluate((e) => ({
      active: document.activeElement === e,
      outline: getComputedStyle(e).outlineStyle,
    }));
    assert.ok(
      focus.active && focus.outline !== "none",
      `${name} ${width}: visible keyboard focus`,
    );
  }
  // Reflow with 200% CSS zoom, in addition to the four native viewport widths.
  await page.setViewportSize({ width: 640, height: 1000 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
    scrollTo(0, 0);
  });
  const reflow = await page.evaluate(() => ({
    viewport: innerWidth,
    document: document.documentElement.scrollWidth,
  }));
  assert.ok(
    reflow.document <= reflow.viewport,
    `${name}: 200% reflow overflow ${JSON.stringify(reflow)}`,
  );
  reflows.push({
    screen: name,
    zoom: "200% CSS zoom",
    ...reflow,
    passed: true,
  });
  fs.writeFileSync(dir + "/reflow.json", JSON.stringify(reflows, null, 2));
  await page.evaluate(() => (document.documentElement.style.zoom = ""));
  await page.setViewportSize(original);
  console.log(
    `Visual checkpoint ${name}: 1440/1024/390/320, no page overflow, axe AA clear`,
  );
}
