import { expect, test, type Page } from "@playwright/test";

import {
  accessTokenFor,
  API,
  createUser,
  deleteUser,
  localStack,
  setProfile,
  type LocalStack,
} from "./helpers";

/** User-study flow and the admin evaluation / study pages (local stack). */
let stack: LocalStack | null = null;
const created: string[] = [];
const NAV_TIMEOUT = 60_000;

test.use({ viewport: { width: 1440, height: 900 } });
test.describe.configure({ mode: "serial" }); // the study switch is global: keep these together
test.beforeAll(async () => {
  stack = await localStack();
});
test.afterAll(async () => {
  if (stack) await Promise.all(created.map((id) => deleteUser(stack!, id)));
});
test.beforeEach(() => {
  test.skip(!stack, "local Supabase / API are not running");
  test.slow();
});

async function user(role: "student" | "admin") {
  const u = await createUser(stack!, role === "admin" ? "Ada Admin" : "Sam Study");
  created.push(u.id);
  await setProfile(stack!, u.id, { role, onboarding_completed: true });
  return u;
}

async function signIn(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
}

async function setStudy(adminEmail: string, enabled: boolean) {
  const token = await accessTokenFor(stack!, adminEmail);
  const res = await fetch(`${API}/admin/study`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error(`could not switch the study: ${res.status}`);
}

test("a student consents and starts the timed pre-test", async ({ page }) => {
  const admin = await user("admin");
  const student = await user("student");
  await setStudy(admin.email, true);
  try {
    await signIn(page, student.email, student.password);
    const banner = page.getByRole("region", { name: "Study" });
    await expect(banner.getByText("You're invited to a short study")).toBeVisible({
      timeout: NAV_TIMEOUT,
    });
    await banner.getByRole("link", { name: "Read more" }).click();
    await expect(page.getByRole("heading", { name: "What taking part means" })).toBeVisible({
      timeout: NAV_TIMEOUT,
    });
    await page.getByRole("button", { name: "I agree to take part" }).click();
    await expect(page.getByRole("heading", { name: "Take the pre-test" })).toBeVisible();
    await page.getByRole("button", { name: "Start the pre-test" }).click();
    await expect(page).toHaveURL(/\/app\/quizzes\/[0-9a-f-]+/, { timeout: NAV_TIMEOUT });
    await expect(page.getByText(/Pre-test · Question 1 of 20/)).toBeVisible({
      timeout: NAV_TIMEOUT,
    });
    await expect(page.getByText("Exam mode")).toBeVisible();
    await expect(page.getByLabel(/Time left/)).toBeVisible();
  } finally {
    await setStudy(admin.email, false);
  }
});

test("admins see the study funnel and evaluation runs", async ({ page }) => {
  const admin = await user("admin");
  await signIn(page, admin.email, admin.password);
  await page.goto("/admin/study");
  await expect(page.getByRole("heading", { name: "Enrolment and completion" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByRole("button", { name: "Export anonymised CSV" })).toBeVisible();
  await page.goto("/admin/evaluation");
  await expect(page.getByRole("heading", { name: /Evaluation/ }).first()).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  // a run exists on the dev database (evaluation/ragas_eval.py --push), or the empty state shows
  await expect(page.getByText(/Headline \(paired|No evaluation runs yet/)).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
});
