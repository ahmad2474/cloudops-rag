// Capture review screenshots: desktop + mobile, bench with an answer, incidents, explorer.
// usage: node scripts/capture.mjs  (API on :8000, web on :3000, demo password acme-demo)
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const OUT = new URL("../../../.impeccable/review/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const base = process.env.WEB_URL ?? "http://localhost:3000";

async function session(viewport, tag) {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport, colorScheme: "dark", reducedMotion: "reduce" });
  const page = await ctx.newPage();
  await page.goto(`${base}/login`);
  await page.getByRole("row", { name: /developer/ }).getByRole("button", { name: "sign in" }).click();
  await page.waitForURL(`${base}/`);
  await page.getByRole("button", { name: "Why are my EKS pods stuck in Pending?" }).click();
  await page.getByText(/answered|abstained|withheld|blocked/i).first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(800);
  await page.getByLabel("Question").focus();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await page.screenshot({ path: `${OUT}${tag}.png`, fullPage: true });
  await page.goto(`${base}/incidents`);
  await page.getByRole("table").waitFor();
  await page.screenshot({ path: `${OUT}${tag}-incidents.png`, fullPage: false });
  await page.goto(`${base}/explorer`);
  await page.getByText("visible to your role").waitFor();
  await page.screenshot({ path: `${OUT}${tag}-explorer.png`, fullPage: false });
  await browser.close();
  console.log("captured", tag);
}

await session({ width: 1440, height: 900 }, "desktop");
await session({ width: 390, height: 844 }, "mobile");
