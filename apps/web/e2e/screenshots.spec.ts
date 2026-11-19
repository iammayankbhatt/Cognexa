import path from "node:path";

import { test, type Page } from "@playwright/test";

const THEMES = ["neon-noir", "titanium-dark", "titanium-light"] as const;
const SHOTS = path.resolve(__dirname, "../../../docs/screenshots");

async function settle(page: Page) {
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400); // let entrance animations finish
}

for (const theme of THEMES) {
  test(`phase 1 design reference: ${theme}`, async ({ page }) => {
    const out = path.join(SHOTS, "phase1");
    await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);

    await page.goto("/design");
    await page.getByRole("heading", { name: "Cognexa design reference" }).waitFor();
    await settle(page);
    await page.screenshot({ path: path.join(out, `design-${theme}.png`), fullPage: true });

    await page.getByRole("button", { name: "Open dialog" }).click();
    await page.getByRole("dialog").waitFor();
    await settle(page);
    await page.screenshot({ path: path.join(out, `design-dialog-${theme}.png`) });
  });

  test(`phase 4 public pages: ${theme}`, async ({ page }) => {
    const out = path.join(SHOTS, "phase4");
    await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);
    await page.emulateMedia({ reducedMotion: "reduce" }); // stable frames

    const pages: [string, string][] = [
      ["/", "landing"],
      ["/how-it-works", "how-it-works"],
      ["/login", "login"],
      ["/signup", "signup"],
    ];
    for (const [url, name] of pages) {
      await page.goto(url);
      await page.getByRole("heading", { level: 1 }).first().waitFor();
      await settle(page);
      await page.screenshot({ path: path.join(out, `${name}-${theme}.png`), fullPage: true });
    }
  });
}
