import path from "node:path";

import { test } from "@playwright/test";

const THEMES = ["neon-noir", "titanium-dark", "titanium-light"] as const;
const OUT = path.resolve(__dirname, "../../../docs/screenshots/phase1");

for (const theme of THEMES) {
  test(`screenshots: ${theme}`, async ({ page }) => {
    await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);

    await page.goto("/");
    await page.screenshot({ path: path.join(OUT, `home-${theme}.png`) });

    await page.goto("/design");
    await page.getByRole("heading", { name: "Cognexa design reference" }).waitFor();
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(OUT, `design-${theme}.png`), fullPage: true });

    await page.getByRole("button", { name: "Open dialog" }).click();
    await page.getByRole("dialog").waitFor();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(OUT, `design-dialog-${theme}.png`) });
  });
}
