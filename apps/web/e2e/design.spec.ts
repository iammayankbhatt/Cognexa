import { expect, test } from "@playwright/test";

const THEMES = ["neon-noir", "titanium-dark", "titanium-light"] as const;

test("home page renders in the default theme", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Cognexa" })).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "neon-noir");
});

test("theme switcher changes the theme and it survives a reload", async ({ page }) => {
  await page.goto("/design");
  await page
    .getByRole("radio", { name: /Titanium Light/ })
    .first()
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "titanium-light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "titanium-light");
});

for (const theme of THEMES) {
  test(`no flash of wrong theme on load (${theme})`, async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);
    // Check as soon as the document is parsed, before React has hydrated.
    await page.goto("/design", { waitUntil: "domcontentloaded" });
    expect(await page.evaluate(() => document.documentElement.dataset.theme)).toBe(theme);
  });
}

test("design page renders every section without console errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/design");
  for (const id of ["themes", "colors", "type", "buttons", "inputs", "cards", "tabs", "states"]) {
    await expect(page.locator(`#${id}`)).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test("dialog opens and toast appears", async ({ page }) => {
  await page.goto("/design");
  await page.getByRole("button", { name: "Open dialog" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.getByRole("button", { name: "Success toast" }).click();
  await expect(page.getByText("Quiz saved")).toBeVisible();
});
