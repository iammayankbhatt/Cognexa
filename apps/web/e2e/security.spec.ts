import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

/**
 * Security headers are sent and the Content-Security-Policy does not block anything the app
 * uses (Phase 13): every CSP violation shows up as a console error, which fails the test.
 */
const NAV_TIMEOUT = 60_000;

function watchCsp(page: Page): string[] {
  const violations: string[] = [];
  page.on("console", (msg) => {
    if (/Content Security Policy|Refused to (load|connect|execute|apply)/i.test(msg.text())) {
      violations.push(msg.text());
    }
  });
  return violations;
}

test("public pages send security headers and load without CSP violations", async ({ page }) => {
  const violations = watchCsp(page);
  const res = await page.goto("/");
  const headers = res!.headers();
  expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
  expect(headers["x-frame-options"]).toBe("DENY");
  expect(headers["x-content-type-options"]).toBe("nosniff");
  expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  expect(headers["x-powered-by"]).toBeUndefined();
  for (const path of ["/how-it-works", "/login", "/about"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
  }
  const missing = await page.goto("/no-such-page");
  expect(missing!.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "This page is not on the map" })).toBeVisible();
  expect(violations).toEqual([]);
});

let stack: LocalStack | null = null;
const created: string[] = [];
test.describe("signed in", () => {
  test.beforeAll(async () => {
    stack = await localStack();
  });
  test.afterAll(async () => {
    if (stack) await Promise.all(created.map((id) => deleteUser(stack!, id)));
  });

  test("app pages (graph, charts, tutor, KaTeX) load without CSP violations", async ({ page }) => {
    test.skip(!stack, "local Supabase / API are not running");
    test.slow();
    const u = await createUser(stack!, "Casey CSP");
    created.push(u.id);
    await setProfile(stack!, u.id, { onboarding_completed: true });
    const violations = watchCsp(page);
    await page.goto("/login");
    await page.getByLabel("Email").fill(u.email);
    await page.getByLabel("Password").fill(u.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
    for (const path of ["/app/graph", "/app/learn/recursion", "/app/tutor"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle", { timeout: NAV_TIMEOUT });
    }
    const box = page.getByLabel("Your question");
    await box.fill("Why does my recursive function crash?");
    await box.press("Enter");
    await expect(page.getByText(/call stack/i).first()).toBeVisible({ timeout: NAV_TIMEOUT });
    expect(violations).toEqual([]);
  });
});
