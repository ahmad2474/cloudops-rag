import { expect, test } from "@playwright/test";

// These run against the built app; the API may be down, in which case the login page must
// still render and explain itself. With the API up (CI job "web" starts none), tests stay green.

test("login page renders the console shell and role choices", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
  await expect(page.getByText(/decided before retrieval/i)).toBeVisible();
  await expect(page.getByRole("button", { name: /^sign in$/i })).toBeVisible();
});

test("protected routes redirect to login when signed out", async ({ page }) => {
  await page.goto("/incidents");
  await page.waitForURL(/\/login\?next=%2Fincidents/);
  await expect(page.getByRole("heading", { name: /sign in/i })).toBeVisible();
});

test("uses the dark graphite ground, not pure black, with the accent on focus", async ({ page }) => {
  await page.goto("/login");
  const bg = await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor);
  expect(bg).toBe("rgb(14, 16, 19)");
  const accent = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--accent").trim());
  expect(accent).toBe("#4fd1c5");
});
