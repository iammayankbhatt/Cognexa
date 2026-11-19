import path from "node:path";

import { test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile } from "./helpers";

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

test.describe("phase 5 admin AI pages (needs local Supabase + API)", () => {
  for (const theme of ["neon-noir", "titanium-light"] as const) {
    test(`phase 5: ${theme}`, async ({ page }) => {
      const stack = await localStack();
      test.skip(!stack, "local Supabase / API are not running");
      test.slow();
      const out = path.join(SHOTS, "phase5");
      const u = await createUser(stack!, "Ada Admin");
      try {
        // The profile theme wins over localStorage after sign-in (theme sync), so set it there.
        await setProfile(stack!, u.id, { role: "admin", onboarding_completed: true, theme });
        await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);
        await page.emulateMedia({ reducedMotion: "reduce" });
        await page.goto("/login");
        await page.getByLabel("Email").fill(u.email);
        await page.getByLabel("Password").fill(u.password);
        await page.getByRole("button", { name: "Sign in" }).click();
        await page.waitForURL(/\/app$/, { timeout: 30_000 });
        await page.goto("/admin/usage");
        await page.getByRole("button", { name: "Run live check" }).click();
        await page.getByText(/answered in \d+ ms/).waitFor({ timeout: 30_000 });
        await page.getByRole("cell", { name: u.email, exact: true }).waitFor({ timeout: 30_000 });
        await settle(page);
        await page.screenshot({ path: path.join(out, `admin-usage-${theme}.png`), fullPage: true });
        await page.goto("/admin/settings");
        await page.getByRole("heading", { name: "Student quotas" }).waitFor({ timeout: 30_000 });
        await settle(page);
        await page.screenshot({
          path: path.join(out, `admin-settings-${theme}.png`),
          fullPage: true,
        });
        await page.goto("/app/settings");
        await page.getByText("Used today").waitFor({ timeout: 30_000 });
        await settle(page);
        await page.screenshot({
          path: path.join(out, `settings-usage-${theme}.png`),
          fullPage: true,
        });
      } finally {
        await deleteUser(stack!, u.id);
      }
    });
  }
});
