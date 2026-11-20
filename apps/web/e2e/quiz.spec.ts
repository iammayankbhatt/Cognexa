import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

/** Quiz flows against the local stack (Supabase auth + API with questions seeded). */
let stack: LocalStack | null = null;
const created: string[] = [];
const NAV_TIMEOUT = 30_000;

test.use({ viewport: { width: 1440, height: 900 } });

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

async function signIn(page: Page, onboarded: boolean) {
  const u = await createUser(stack!, "Quinn Quiz");
  created.push(u.id);
  await setProfile(stack!, u.id, { onboarding_completed: onboarded });
  await page.goto("/login");
  await page.getByLabel("Email").fill(u.email);
  await page.getByLabel("Password").fill(u.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(onboarded ? /\/app$/ : /\/app\/onboarding/, {
    timeout: NAV_TIMEOUT,
  });
  return u;
}

/** Give some answer to the question on screen (first option, True, or text). */
async function answerCurrent(page: Page) {
  const radio = page.getByRole("radio").first();
  const box = page.getByRole("checkbox").first();
  const text = page.locator("textarea[id^='answer-']");
  if (await radio.isVisible().catch(() => false)) await radio.click();
  else if (await box.isVisible().catch(() => false)) await box.click();
  else await text.fill("A stack frame is pushed for each call.");
}

test("take a concept quiz end to end and see mastery on the concept page", async ({ page }) => {
  await signIn(page, true);
  await page.goto("/app/learn/stack");
  await expect(page.getByRole("heading", { name: /Stack/, level: 1 })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByText("Not practised yet")).toBeVisible();
  await expect(page.getByRole("tab", { name: "Python" })).toBeVisible(); // code tabs
  await page.getByRole("button", { name: "Practice this concept" }).click();
  await expect(page).toHaveURL(/\/app\/quizzes\/[0-9a-f-]+/, { timeout: NAV_TIMEOUT });

  const nav = page.getByRole("navigation", { name: "Questions" }).getByRole("button");
  await expect(nav).toHaveCount(8, { timeout: NAV_TIMEOUT });
  const total = 8;
  for (let i = 0; i < total; i++) {
    await answerCurrent(page);
    await page.getByRole("button", { name: "Check answer" }).click();
    await expect(
      page.getByRole("status").filter({ hasText: /Correct|Not quite|Partly|pending/ }),
    ).toBeVisible({
      timeout: NAV_TIMEOUT,
    });
    await page
      .getByRole("button", { name: i === total - 1 ? "See results" : "Next question" })
      .click();
  }
  await expect(page.getByRole("heading", { name: "Concept quiz results" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByRole("img", { name: /Score \d+ percent/ })).toBeVisible();

  await page.goto("/app/learn/stack");
  await expect(page.getByText(/\d+ answers, \d+ correct/)).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(page.getByText("Not practised yet")).toBeHidden();
  await page.goto("/app/quizzes");
  await expect(page.getByRole("cell", { name: "Concept quiz: Stack" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
});

test("the onboarding diagnostic seeds mastery", async ({ page }) => {
  await signIn(page, false);
  await page.getByRole("button", { name: "Get started" }).click();
  await page.getByRole("radio", { name: /Beginner/ }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Start the diagnostic" }).click();
  await expect(page.getByText("Diagnostic · Question 1 of 10")).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  for (let i = 0; i < 10; i++) {
    await answerCurrent(page);
    await page.getByRole("button", { name: i === 9 ? "Submit quiz" : "Next" }).click();
  }
  await expect(page.getByRole("heading", { name: "Your starting point" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await page.getByRole("button", { name: "Go to my dashboard" }).click();
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
  await page.goto("/app/learn");
  await expect(page.getByText(/You have practised (\d+)\./)).not.toHaveText(/practised 0\./, {
    timeout: NAV_TIMEOUT,
  });
});
