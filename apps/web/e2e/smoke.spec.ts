import { expect, test } from "@playwright/test";

test("home renders the console shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /cloudops intelligence/i })).toBeVisible();
  // API may or may not be running in this environment; the pill must render either way.
  await expect(page.getByTestId("api-status")).toHaveAttribute("data-state", /ok|degraded|offline/);
});

test("uses the dark graphite surface, not pure black", async ({ page }) => {
  await page.goto("/");
  const bg = await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor);
  expect(bg).not.toBe("rgb(0, 0, 0)");
  expect(bg).toBe("rgb(14, 16, 19)");
});
