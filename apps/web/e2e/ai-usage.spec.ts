import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

let stack: LocalStack | null = null;
const created: string[] = [];

test.beforeAll(async () => {
  stack = await localStack();
});
test.afterAll(async () => {
  if (stack) await Promise.all(created.map((id) => deleteUser(stack!, id)));
});
test.beforeEach(() => {
  test.skip(!stack, "local Supabase / API are not running");
  test.slow(); // real sign-in plus first-request compiles on a cold dev server
});

const NAV_TIMEOUT = 30_000;

async function signInAs(page: Page, role: "student" | "admin") {
  const u = await createUser(stack!, role === "admin" ? "Ada Admin" : "Sam Student");
  created.push(u.id);
  await setProfile(stack!, u.id, { role, onboarding_completed: true });
  await page.goto("/login");
  await page.getByLabel("Email").fill(u.email);
  await page.getByLabel("Password").fill(u.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
  return u;
}

test("a student sees their AI usage and limits in settings", async ({ page }) => {
  await signInAs(page, "student");
  await page.goto("/app/settings");
  const card = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: "AI usage" }) });
  await expect(card.getByText("Used today")).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(card.getByText("0 / 40")).toBeVisible();
  await expect(card.getByRole("img", { name: /Last 30 days: 0 requests/ })).toBeVisible();
  await card.getByRole("button", { name: "Show table" }).click();
  await expect(card.getByRole("table")).toBeVisible();
  await expect(card.getByRole("row")).toHaveCount(31); // header + 30 days
});

test("an admin runs a live LLM check and sees it in the usage dashboard", async ({ page }) => {
  await signInAs(page, "admin");
  await page.goto("/admin/usage");
  await expect(page.getByRole("heading", { name: "AI usage", level: 1 })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByText(/Primary: fake/)).toBeVisible();
  await page.getByRole("button", { name: "Run live check" }).click();
  await expect(page.getByText(/fake \/ fake-model answered in \d+ ms/)).toBeVisible();
  await expect(page.getByText(/^1\/200/)).toBeVisible(); // top-bar meter refreshed (BUG-021)
  // The dashboard refreshes: the call appears in the per-model table.
  await expect(page.getByRole("cell", { name: "fake / fake-model" })).toBeVisible();
  await page.getByRole("radio", { name: "7 days" }).click();
  await expect(page.getByRole("img", { name: /Last 7 days: \d+ requests/ })).toBeVisible();
});

test("an admin edits AI settings with validation", async ({ page }) => {
  await signInAs(page, "admin");
  await page.goto("/admin/settings");
  const quota = page
    .locator("form")
    .filter({ has: page.getByRole("heading", { name: "Global daily cap" }) });
  await expect(quota).toBeVisible({ timeout: NAV_TIMEOUT });
  const field = quota.getByLabel("AI requests per day (all users)");
  await field.fill("");
  await quota.getByRole("button", { name: "Save" }).click();
  await expect(quota.getByText("Enter a number")).toBeVisible(); // empty is not zero
  const current = "1500";
  await field.fill(current);
  await quota.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Settings saved")).toBeVisible();
  await expect(page.getByText(/groq: (set|missing)/)).toBeVisible(); // key status, never values
});
