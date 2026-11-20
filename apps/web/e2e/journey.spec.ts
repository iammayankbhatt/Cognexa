import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

/**
 * Full journeys (Phase 13), fake AI providers:
 * 1. a student: onboarding diagnostic → dashboard → tutor question with trace → report the answer
 *    → concept quiz → recommendation → note → revision sheet → theme switch → sign out;
 * 2. an admin: resolve that report, change the student's quota, act on an LLM proposal.
 * Approving a proposal changes the concept graph, so it runs only in CI's throwaway stack; a
 * local run rejects the proposal instead.
 */
const NAV_TIMEOUT = 60_000;
const token = randomUUID().slice(0, 8);
const REPORT_NOTE = `journey-${token}: the iterative fix is missing`;
let stack: LocalStack | null = null;
let student: { id: string; email: string; password: string } | null = null;
const created: string[] = [];

test.use({ viewport: { width: 1440, height: 900 } });
test.describe.configure({ mode: "serial" });
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

async function signIn(page: Page, email: string, password: string, landing: RegExp) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(landing, { timeout: NAV_TIMEOUT });
}

/** Some answer to the question on screen (first option, True, or text). */
async function answerCurrent(page: Page) {
  const radio = page.getByRole("radio").first();
  const box = page.getByRole("checkbox").first();
  if (await radio.isVisible().catch(() => false)) await radio.click();
  else if (await box.isVisible().catch(() => false)) await box.click();
  else await page.locator("textarea[id^='answer-']").fill("Each call pushes a stack frame.");
}

test("a student goes from sign-up to a revision sheet", async ({ page }) => {
  student = await createUser(stack!, "Jo Journey");
  created.push(student.id);
  await signIn(page, student.email, student.password, /\/app\/onboarding/);

  // onboarding diagnostic
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
  await page.getByRole("button", { name: "Go to my dashboard" }).click({ timeout: NAV_TIMEOUT });
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
  await expect(page.getByRole("region", { name: "Next best step" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });

  // tutor: trace, answer, report
  await page.goto("/app/tutor");
  const box = page.getByLabel("Your question");
  await box.fill("Why does my recursive function crash for big inputs?");
  await box.press("Enter");
  const chat = page.getByRole("region", { name: "Tutor chat" });
  await expect(chat.getByText("Matched:")).toBeVisible({ timeout: NAV_TIMEOUT });
  // After the diagnostic some prerequisites are practised but weak, so the bounded agent may
  // first ask a quick check (by design); answering it continues the same turn.
  const answer = chat.getByText(/Here is what the course notes say/);
  const check = page.getByRole("group", { name: "Quick check" });
  await expect(answer.or(check).first()).toBeVisible({ timeout: NAV_TIMEOUT });
  if (await check.isVisible()) {
    await check.getByLabel("Your answer").fill("it stores values in memory that each call uses");
    await check.getByRole("button", { name: "Answer" }).click();
    await expect(chat.getByText("Continuing:")).toBeVisible({ timeout: NAV_TIMEOUT });
  }
  await expect(answer.first()).toBeVisible({ timeout: NAV_TIMEOUT });
  await chat.getByRole("button", { name: "Report answer" }).click();
  const dialog = page.getByRole("dialog", { name: "Report this answer" });
  await dialog.getByLabel("It is incomplete").check();
  await dialog.getByLabel("Details (optional)").fill(REPORT_NOTE);
  await dialog.getByRole("button", { name: "Send report" }).click();
  await expect(chat.getByText("Reported for review")).toBeVisible({ timeout: NAV_TIMEOUT });

  // concept quiz
  await page.goto("/app/learn/stack");
  await page.getByRole("button", { name: "Practice this concept" }).click({ timeout: NAV_TIMEOUT });
  await expect(page).toHaveURL(/\/app\/quizzes\/[0-9a-f-]+/, { timeout: NAV_TIMEOUT });
  const nav = page.getByRole("navigation", { name: "Questions" }).getByRole("button");
  await expect(nav).toHaveCount(8, { timeout: NAV_TIMEOUT });
  for (let i = 0; i < 8; i++) {
    await answerCurrent(page);
    await page.getByRole("button", { name: "Check answer" }).click();
    await page.getByRole("button", { name: i === 7 ? "See results" : "Next question" }).click();
  }
  await expect(page.getByRole("heading", { name: "Concept quiz results" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  // the recommender reacts to the new quiz result
  await expect(page.getByRole("region", { name: "Next best step" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });

  // note + revision sheet
  await page.goto("/app/learn/recursion");
  await page.getByRole("button", { name: "Add a note" }).click({ timeout: NAV_TIMEOUT });
  await page.getByLabel("Your note").fill("Write the **base case** first.");
  await page.getByRole("button", { name: "Save note" }).click();
  await expect(page.getByText("Note saved.")).toBeVisible();
  await page.goto("/app/notes");
  await page.getByRole("tab", { name: "Revision sheets" }).click({ timeout: NAV_TIMEOUT });
  await page.getByRole("button", { name: "Choose concepts" }).click();
  await page.getByLabel("Recursion", { exact: true }).check();
  await page.getByRole("button", { name: "Write sheet for 1 concept(s)" }).click();
  await expect(page.locator("article.print-sheet")).toContainText(/recursion/i, {
    timeout: NAV_TIMEOUT,
  });

  // theme switch, then sign out
  await page.goto("/app/settings");
  await page.getByRole("radio", { name: /Titanium Light/ }).click({ timeout: NAV_TIMEOUT });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "titanium-light");
  await page.getByRole("button", { name: "Open user menu" }).click();
  await page.getByRole("menuitem", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/, { timeout: NAV_TIMEOUT });
});

test("an admin resolves the report, changes a quota and acts on a proposal", async ({ page }) => {
  test.skip(!student, "needs the student journey above");
  const admin = await createUser(stack!, "Ada Admin");
  created.push(admin.id);
  await setProfile(stack!, admin.id, { role: "admin", onboarding_completed: true });
  await signIn(page, admin.email, admin.password, /\/app$/);

  // resolve the student's report
  await page.goto("/admin/moderation");
  const card = page.getByRole("article").filter({ hasText: REPORT_NOTE });
  await expect(card).toBeVisible({ timeout: NAV_TIMEOUT });
  await card.getByLabel("Resolution note").fill("Added the iterative version to the notes.");
  await card.getByRole("button", { name: "Resolve" }).click();
  await expect(card).toBeHidden({ timeout: NAV_TIMEOUT });
  await page.getByRole("tab", { name: "resolved" }).click();
  await expect(page.getByRole("article").filter({ hasText: REPORT_NOTE })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });

  // change the student's daily quota
  await page.goto("/admin/users");
  await page.getByLabel("Search users").fill(student!.email);
  await page.getByRole("button", { name: "Search" }).click();
  const quota = page.getByLabel(/Daily AI request quota for/);
  await expect(quota).toHaveCount(1, { timeout: NAV_TIMEOUT });
  await quota.fill("7");
  await page.getByRole("button", { name: "Set" }).click();
  await expect(page.getByText("User updated.")).toBeVisible({ timeout: NAV_TIMEOUT });
  await page.reload();
  await page.getByLabel("Search users").fill(student!.email);
  await page.getByRole("button", { name: "Search" }).click();
  const saved = page.getByLabel(/Daily AI request quota for/);
  await expect(saved).toHaveCount(1, { timeout: NAV_TIMEOUT }); // search applied
  await expect(saved).toHaveValue("7");

  // an LLM proposal from uploaded notes
  await page.goto("/admin/proposals");
  const name = `journey-${token}.md`;
  const notes = [
    "# Stacks",
    "",
    `Stacks (${token}) are last-in, first-out: push adds an element on top and pop removes the`,
    "newest one. Browsers keep the pages you visited on a stack, so Back returns to the last one.",
  ].join("\n");
  await page.locator("#ingest-file").setInputFiles({
    name,
    mimeType: "text/markdown",
    buffer: Buffer.from(notes),
  });
  const row = page.getByRole("listitem").filter({ hasText: name });
  await row.getByRole("button", { name: "Show proposals" }).click({ timeout: NAV_TIMEOUT });
  await page.getByRole("list", { name: "Proposals" }).getByRole("button").first().click();
  const detail = page.getByRole("article", { name: "Proposal detail" });
  if (process.env.CI) {
    await detail.getByRole("button", { name: "Approve" }).click();
    await expect(detail).toContainText(/Approved on/, { timeout: NAV_TIMEOUT });
  } else {
    await page.getByLabel("Note (optional)").fill("journey (local run): not applied");
    await detail.getByRole("button", { name: "Reject" }).click();
    await expect(detail).toContainText(/Rejected on/, { timeout: NAV_TIMEOUT });
  }
});
