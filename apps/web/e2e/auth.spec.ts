import { expect, test, type Page } from "@playwright/test";

import {
  accessTokenFor,
  API,
  createUser,
  deleteUser,
  localStack,
  messagesTo,
  PASSWORD,
  type LocalStack,
} from "./helpers";

let stack: LocalStack | null = null;
const created: string[] = [];

test.beforeAll(async () => {
  stack = await localStack();
});
test.afterAll(async () => {
  if (stack) await Promise.all(created.map((id) => deleteUser(stack!, id)));
});

async function signIn(page: Page, email: string, password = PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

// The dev server compiles /app and /app/onboarding on first request, which can take
// longer than the default 5 s on a cold start (BUG-015). Navigation waits use this.
const NAV_TIMEOUT = 30_000;

async function finishOnboarding(page: Page) {
  await expect(page).toHaveURL(/\/app\/onboarding/, { timeout: NAV_TIMEOUT });
  await page.getByRole("button", { name: "Get started" }).click();
  await page.getByRole("radio", { name: /Intermediate/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Skip for now" }).click();
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
}

test.describe("route protection (no backend needed)", () => {
  test("signed-out visitors are sent to sign-in, with the page they wanted", async ({ page }) => {
    await page.goto("/app/settings");
    await expect(page).toHaveURL(/\/login\?next=%2Fapp%2Fsettings/);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });

  test("admin area is also protected", async ({ page }) => {
    await page.goto("/admin/users");
    await expect(page).toHaveURL(/\/login/);
  });

  test("public pages stay public", async ({ page }) => {
    for (const path of ["/", "/login", "/signup", "/forgot-password"]) {
      const res = await page.goto(path);
      expect(res?.status(), path).toBe(200);
      await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/$" : path}`));
    }
  });
});

test.describe("sign-in forms (validation)", () => {
  test("shows field errors without calling the server", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(
      page.getByText("Enter a valid email address").or(page.getByText("Enter your email")),
    ).toBeVisible();
    await expect(page.getByText("Enter your password")).toBeVisible();
  });

  test("sign-up checks password length and confirmation", async ({ page }) => {
    await page.goto("/signup");
    await page.getByLabel("Name").fill("Ada");
    await page.getByLabel("Email").fill("ada@example.com");
    await page.getByLabel("Password", { exact: true }).fill("short");
    await page.getByLabel("Confirm password").fill("different");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Use at least 8 characters")).toBeVisible();
    await expect(page.getByText("Passwords do not match")).toBeVisible();
  });
});

test.describe("full auth cycle (needs local Supabase + API)", () => {
  test.beforeEach(() => {
    test.skip(!stack, "local Supabase / API are not running");
    // Real sign-ins + onboarding, plus first-request compiles on a cold dev server.
    test.slow();
  });

  test("wrong password shows a friendly error", async ({ page }) => {
    const u = await createUser(stack!);
    created.push(u.id);
    await signIn(page, u.email, "not-the-password");
    await expect(page.getByRole("alert").filter({ hasText: "don't match" })).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("sign in, onboard, see the dashboard, sign out", async ({ page }) => {
    const u = await createUser(stack!, "Grace Hopper");
    created.push(u.id);
    await signIn(page, u.email);
    await finishOnboarding(page);
    await expect(page.getByRole("heading", { name: "Welcome, Grace" })).toBeVisible();
    await expect(page.getByText(/0\/40/).first()).toBeVisible(); // usage meter
    await page.getByRole("button", { name: "Open user menu" }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await expect(page).toHaveURL(/\/login/);
    await page.goto("/app");
    await expect(page).toHaveURL(/\/login/); // session really ended
  });

  test("a student cannot use the admin area (UI) or the admin API", async ({ page }) => {
    const u = await createUser(stack!);
    created.push(u.id);
    await signIn(page, u.email);
    await finishOnboarding(page);
    await page.goto("/admin/users");
    await expect(page.getByRole("heading", { name: /403/ })).toBeVisible();
    // The API enforces it independently of the UI.
    const headers = { Authorization: `Bearer ${await accessTokenFor(stack!, u.email)}` };
    const list = await fetch(`${API}/admin/users`, { headers });
    expect(list.status).toBe(403);
    expect(((await list.json()) as { error: { code: string } }).error.code).toBe("forbidden");
    const patch = await fetch(`${API}/admin/users/${u.id}`, {
      method: "PATCH",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ role: "admin" }),
    });
    expect(patch.status).toBe(403); // cannot promote yourself
    expect((await fetch(`${API}/admin/users`)).status).toBe(401); // and no token means 401
  });

  test("theme choice is saved to the profile and follows the user to a new browser", async ({
    page,
    browser,
  }) => {
    const u = await createUser(stack!);
    created.push(u.id);
    await signIn(page, u.email);
    await finishOnboarding(page);
    await page.goto("/app/settings");
    // Listen before clicking: the PATCH can finish before a later waitForResponse is set up.
    const saved = page.waitForResponse(
      (r) => r.url().endsWith("/me") && r.request().method() === "PATCH",
    );
    await page.getByRole("radio", { name: /Titanium Light/ }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "titanium-light");
    expect((await saved).ok()).toBe(true);

    const other = await browser.newContext(); // fresh storage: no local theme
    const page2 = await other.newPage();
    await signIn(page2, u.email);
    await expect(page2).toHaveURL(/\/app/, { timeout: NAV_TIMEOUT });
    await expect(page2.locator("html")).toHaveAttribute("data-theme", "titanium-light", {
      timeout: NAV_TIMEOUT,
    });
    await other.close();
  });

  test("sign-up sends a confirmation email and asks the user to check their inbox", async ({
    page,
  }) => {
    const email = `e2e-signup-${Date.now()}@example.com`;
    await page.goto("/signup");
    await page.getByLabel("Name").fill("New Student");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByLabel("Confirm password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByRole("heading", { name: "Check your inbox" })).toBeVisible();
    await expect.poll(async () => (await messagesTo(stack!, email)).length).toBeGreaterThan(0);
    // Unconfirmed accounts cannot sign in yet.
    await signIn(page, email);
    await expect(page.getByRole("alert").filter({ hasText: "confirm your email" })).toBeVisible();
    // clean up the created user
    const res = await fetch(`${stack!.url}/auth/v1/admin/users?per_page=200`, {
      headers: { apikey: stack!.serviceKey, Authorization: `Bearer ${stack!.serviceKey}` },
    });
    const list = (await res.json()) as { users: { id: string; email: string }[] };
    const mine = list.users.find((x) => x.email === email);
    if (mine) created.push(mine.id);
  });
});
