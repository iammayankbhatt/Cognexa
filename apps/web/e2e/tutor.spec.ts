import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

/**
 * Tutor flows against the local stack: Supabase auth + the API in FakeProvider mode
 * (LLM_PRIMARY_PROVIDER=fake) with the DSA graph seeded in Neo4j and Postgres.
 */
let stack: LocalStack | null = null;
const created: string[] = [];
const NAV_TIMEOUT = 30_000;
const CANONICAL =
  "Why does my recursive function crash for big inputs with maximum recursion depth exceeded?";

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

async function signInAs(page: Page, role: "student" | "admin" = "student") {
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

async function setMastery(userId: string, conceptId: string, score: number) {
  const res = await fetch(`${stack!.url}/rest/v1/mastery`, {
    method: "POST",
    headers: {
      apikey: stack!.serviceKey,
      Authorization: `Bearer ${stack!.serviceKey}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify({
      user_id: userId,
      concept_id: conceptId,
      subject_id: "dsa",
      score,
      attempts: 5,
      correct: 1,
    }),
  });
  if (!res.ok) throw new Error(`could not set mastery: ${res.status} ${await res.text()}`);
}

async function ask(page: Page, text: string) {
  const box = page.getByLabel("Your question");
  await box.fill(text);
  await box.press("Enter");
}

test("ask → trace → answer → why panel → report → persists after reload", async ({ page }) => {
  await signInAs(page);
  await page.goto("/app/tutor");
  await expect(page.getByRole("heading", { name: "What are you stuck on?" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(
    page
      .getByText(/Start here|Next in the syllabus|Fix the root cause|Focused review|Due for review/)
      .first(),
  ).toBeVisible({ timeout: NAV_TIMEOUT });

  await ask(page, CANONICAL);
  await expect(page).toHaveURL(/\/app\/tutor\?thread=/, { timeout: NAV_TIMEOUT });
  const chat = page.getByRole("region", { name: "Tutor chat" });
  await expect(chat.getByText("Matched:")).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(chat.getByText("walking prerequisites")).toBeVisible();
  await expect(chat.getByText(/Here is what the course notes say/)).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(chat.getByLabel("Suggested follow-up questions")).toBeVisible();
  // citation chip links to the concept page
  await expect(chat.getByRole("link", { name: /Recursion|Call Stack/ }).first()).toHaveAttribute(
    "href",
    /\/app\/learn\/[a-z_]+/,
  );

  // Why this answer? (open by default on desktop)
  const why = page.getByRole("complementary", { name: "Why this answer" });
  await expect(why.getByText("LLM classifier")).toBeVisible();
  await expect(why.getByRole("img", { name: /Traversed graph/ })).toBeVisible();
  const firstChunk = why.getByRole("button", { expanded: false }).first();
  await firstChunk.click();
  await expect(why.getByRole("button", { expanded: true }).first()).toBeVisible();
  // provider: the fake model, or the response cache when this question was answered before
  await expect(why.getByText(/^(fake|cache)$/)).toBeVisible();

  // report the answer
  await chat.getByRole("button", { name: "Report answer" }).click();
  const dialog = page.getByRole("dialog", { name: "Report this answer" });
  await dialog.getByLabel("It is incomplete").check();
  await dialog.getByLabel("Details (optional)").fill("Missing the iterative fix.");
  await dialog.getByRole("button", { name: "Send report" }).click();
  await expect(page.getByText("Thanks — a reviewer will check this.")).toBeVisible();
  await expect(chat.getByText("Reported for review")).toBeVisible();

  // persists after reload
  await page.reload();
  await expect(chat.getByText(CANONICAL, { exact: true })).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(chat.getByText("Reported for review")).toBeVisible();
  const history = page.getByRole("navigation", { name: "Chat history" });
  await expect(
    history.getByRole("button", { name: /^Why does my recursive function crash/ }),
  ).toBeVisible();
});

test("a weak practised prerequisite triggers a quick check that continues the turn", async ({
  page,
}) => {
  const u = await signInAs(page);
  await setMastery(u.id, "call_stack", 0.3);
  await page.goto("/app/tutor");
  await ask(page, "Why does my recursive function crash?");
  const check = page.getByRole("group", { name: "Quick check" });
  await expect(check).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(check.getByText(/call stack/i)).toBeVisible();
  await check.getByLabel("Your answer").fill("each call adds a stack frame");
  await check.getByRole("button", { name: "Answer" }).click();
  const chat = page.getByRole("region", { name: "Tutor chat" });
  await expect(chat.getByText("Continuing:")).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(check.getByText("Answered below.")).toBeVisible();
});

test("an admin compares GraphRAG with plain RAG side by side", async ({ page }) => {
  await signInAs(page, "admin");
  await page.goto("/app/tutor");
  await page.getByRole("button", { name: "Compare with plain RAG" }).click();
  await ask(page, CANONICAL);
  await expect(page.getByRole("region", { name: "GraphRAG (Cognexa)" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByRole("region", { name: "Plain RAG (baseline)" })).toBeVisible();
  await expect(page.getByText(/Plain RAG: \d+ chunks by similarity/)).toBeVisible();
});

test("the plain-RAG switch sends plain_rag turns, and students without the flag never see it (BUG-057)", async ({
  page,
  browser,
}) => {
  await signInAs(page, "admin");
  await page.goto("/app/tutor");
  const toggle = page.getByRole("button", { name: "Plain RAG baseline" });
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-pressed", "true");
  const sent = page.waitForRequest((r) => /\/tutor\/threads\/[^/]+\/messages$/.test(r.url()));
  await ask(page, "explain binary search");
  expect((await sent).postDataJSON()).toMatchObject({ mode: "plain_rag" });
  await expect(page.getByText(/Plain RAG: \d+ chunks by similarity/)).toBeVisible({
    timeout: NAV_TIMEOUT,
  });

  const other = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await signInAs(other, "student");
  await other.goto("/app/tutor");
  await expect(other.getByLabel("Your question")).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(other.getByRole("button", { name: "Plain RAG baseline" })).toHaveCount(0);
  await other.close();
});

test("threads can be renamed and deleted with undo", async ({ page }) => {
  await signInAs(page);
  await page.goto("/app/tutor");
  await ask(page, "What is a hash table?");
  const history = page.getByRole("navigation", { name: "Chat history" });
  const item = history.getByRole("button", { name: "What is a hash table", exact: true });
  await expect(item).toBeVisible({ timeout: NAV_TIMEOUT });

  await history
    .getByRole("button", { name: /Actions for/ })
    .first()
    .click();
  await page.getByRole("menuitem", { name: "Rename" }).click();
  const field = history.getByLabel("Chat title");
  await field.fill("Hashing notes");
  await field.press("Enter");
  await expect(history.getByRole("button", { name: "Hashing notes", exact: true })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });

  await history.getByRole("button", { name: /Actions for Hashing notes/ }).click();
  await page.getByRole("menuitem", { name: "Delete" }).click();
  await expect(history.getByRole("button", { name: "Hashing notes", exact: true })).toBeHidden();
  await page.getByRole("button", { name: "Undo" }).click();
  await expect(history.getByRole("button", { name: "Hashing notes", exact: true })).toBeVisible();
});

test("New chat followed by an immediate question starts a new thread (BUG-027)", async ({
  page,
}) => {
  await signInAs(page);
  await page.goto("/app/tutor");
  await ask(page, "What is a queue?");
  await expect(page).toHaveURL(/thread=/, { timeout: NAV_TIMEOUT });
  const first = new URL(page.url()).searchParams.get("thread");
  const chat = page.getByRole("region", { name: "Tutor chat" });
  await expect(chat.getByLabel("Suggested follow-up questions")).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await page.getByRole("button", { name: "New chat" }).first().click();
  await ask(page, "What is a stack?"); // no wait in between
  await expect(page).not.toHaveURL(new RegExp(`thread=${first}`), { timeout: NAV_TIMEOUT });
  await expect(page).toHaveURL(/thread=/);
  const history = page.getByRole("navigation", { name: "Chat history" });
  await expect(history.getByRole("button", { name: "What is a stack", exact: true })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(history.getByRole("button", { name: "What is a queue", exact: true })).toBeVisible();
  await expect(chat.getByText("What is a queue?", { exact: true })).toBeHidden();
});
