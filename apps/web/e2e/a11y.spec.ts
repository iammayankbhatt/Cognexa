import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

/**
 * Accessibility (Phase 13): axe on every main page, in every theme where colours matter.
 * Serious and critical violations fail the test; the message lists rule, page and element.
 */
const NAV_TIMEOUT = 60_000;
const THEMES = ["neon-noir", "titanium-dark", "titanium-light"] as const;
type Theme = (typeof THEMES)[number];

const PUBLIC = ["/", "/how-it-works", "/about", "/login", "/signup", "/privacy", "/terms", "/nope"];
const STUDENT = [
  "/app",
  "/app/tutor",
  "/app/learn",
  "/app/learn/recursion",
  "/app/graph",
  "/app/quizzes",
  "/app/review",
  "/app/notes",
  "/app/settings",
];
const ADMIN = [
  "/admin",
  "/admin/graph",
  "/admin/proposals",
  "/admin/content?concept=stack",
  "/admin/moderation",
  "/admin/evaluation",
  "/admin/users",
  "/admin/usage",
  "/admin/settings",
  "/admin/study",
];

async function scan(page: Page, path: string, theme: Theme): Promise<string[]> {
  await page.goto(path);
  await page.waitForLoadState("networkidle", { timeout: NAV_TIMEOUT });
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return result.violations
    .filter((v) => v.impact === "serious" || v.impact === "critical")
    .flatMap((v) =>
      v.nodes.slice(0, 3).map((n) => {
        // first line of axe's explanation, e.g. "Element has insufficient color contrast of 3.9"
        const why = (n.failureSummary ?? "").split(/\r?\n/)[1]?.trim().slice(0, 140) ?? "";
        return `${theme} ${path} [${v.id}] ${n.target.join(" ")} :: ${why}`;
      }),
    );
}

for (const theme of THEMES) {
  test(`public pages have no serious a11y violations (${theme})`, async ({ page }) => {
    test.slow();
    await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);
    const problems: string[] = [];
    for (const path of PUBLIC) problems.push(...(await scan(page, path, theme)));
    expect(problems).toEqual([]);
  });
}

let stack: LocalStack | null = null;
const created: string[] = [];
test.describe("signed in", () => {
  test.beforeAll(async () => {
    stack = await localStack();
  });
  test.afterAll(async () => {
    if (stack) await Promise.all(created.map((id) => deleteUser(stack!, id)));
  });

  async function signIn(page: Page, role: "student" | "admin", theme: Theme) {
    const u = await createUser(stack!, role === "admin" ? "Ada Admin" : "Sam Student");
    created.push(u.id);
    await setProfile(stack!, u.id, { role, onboarding_completed: true, theme });
    await page.addInitScript((t) => localStorage.setItem("cognexa-theme", t), theme);
    await page.goto("/login");
    await page.getByLabel("Email").fill(u.email);
    await page.getByLabel("Password").fill(u.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
  }

  for (const theme of THEMES) {
    test(`student pages have no serious a11y violations (${theme})`, async ({ page }) => {
      test.skip(!stack, "local Supabase / API are not running");
      test.slow();
      await signIn(page, "student", theme);
      const problems: string[] = [];
      for (const path of STUDENT) problems.push(...(await scan(page, path, theme)));
      expect(problems).toEqual([]);
    });
  }

  for (const theme of ["neon-noir", "titanium-light"] as const) {
    test(`admin pages have no serious a11y violations (${theme})`, async ({ page }) => {
      test.skip(!stack, "local Supabase / API are not running");
      test.slow();
      await signIn(page, "admin", theme);
      const problems: string[] = [];
      for (const path of ADMIN) problems.push(...(await scan(page, path, theme)));
      expect(problems).toEqual([]);
    });
  }
});

test("pages fit every screen width without sideways scrolling", async ({ page }) => {
  test.slow();
  const problems: string[] = [];
  for (const width of [360, 768, 1280, 1920]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/", "/how-it-works", "/login", "/signup", "/about"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      if (overflow > 1) problems.push(`${width}px ${path}: ${overflow}px too wide`);
    }
  }
  expect(problems).toEqual([]);
});

test("keyboard focus is always visible on the sign-in form", async ({ page }) => {
  await page.goto("/login");
  await page.waitForLoadState("networkidle");
  const seen: string[] = [];
  for (let i = 0; i < 8; i++) {
    await page.keyboard.press("Tab");
    const info = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return null;
      const s = getComputedStyle(el);
      const ring =
        s.boxShadow !== "none" || (s.outlineStyle !== "none" && s.outlineWidth !== "0px");
      return {
        name: `${el.tagName.toLowerCase()} ${el.textContent?.trim().slice(0, 20) ?? ""}`,
        ring,
      };
    });
    if (!info) continue;
    seen.push(info.name);
    expect(info.ring, `no visible focus indicator on ${info.name}`).toBe(true);
  }
  expect(seen.length).toBeGreaterThan(3);
});
