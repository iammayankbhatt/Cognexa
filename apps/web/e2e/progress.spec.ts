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

/** Dashboard, knowledge map, notes and revision sheets (local stack, fake LLM). */
let stack: LocalStack | null = null;
const created: string[] = [];
const NAV_TIMEOUT = 60_000;

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

async function signIn(page: Page) {
  const u = await createUser(stack!, "Dana Dash");
  created.push(u.id);
  await setProfile(stack!, u.id, { onboarding_completed: true });
  await page.goto("/login");
  await page.getByLabel("Email").fill(u.email);
  await page.getByLabel("Password").fill(u.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
  return u;
}

/** Take a concept quiz through the API with no answers (all wrong), as seeded activity. */
async function seedQuiz(email: string, concept: string) {
  const token = await accessTokenFor(stack!, email);
  const h = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  const s = (await (
    await fetch(`${API}/quiz/sessions`, {
      method: "POST",
      headers: h,
      body: JSON.stringify({
        mode: "concept",
        concept_id: concept,
        count: 5,
        feedback_mode: "exam",
      }),
    })
  ).json()) as { id: string };
  await fetch(`${API}/quiz/sessions/${s.id}/submit`, { method: "POST", headers: h, body: "{}" });
}

test("the dashboard renders progress for a learner with activity", async ({ page }) => {
  const u = await signIn(page);
  await seedQuiz(u.email, "stack");
  await seedQuiz(u.email, "stack");
  await page.reload();
  await expect(
    page
      .getByRole("region", { name: "Recent activity" })
      .getByText(/Concept quiz: Stack/)
      .first(),
  ).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByText("Overall mastery")).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Weak spots" }).getByRole("link", { name: /Stack/ }).first(),
  ).toBeVisible();
  await expect(page.getByRole("region", { name: "Next best step" })).toBeVisible();
  await page
    .getByRole("region", { name: "Clusters" })
    .getByRole("button", { name: "Show table" })
    .click();
  await expect(page.getByRole("cell", { name: "Linear structures" })).toBeVisible();
});

test("the knowledge map opens a concept drawer", async ({ page }) => {
  await signIn(page);
  await page.goto("/app/graph");
  await expect(page.getByRole("img", { name: /Knowledge map with \d+ concepts/ })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.locator('canvas[data-id="layer2-node"]')).toBeVisible({ timeout: NAV_TIMEOUT });
  await page.getByText("List view").click();
  await page.getByRole("button", { name: "Recursion", exact: true }).click();
  const drawer = page.getByRole("complementary", { name: "Recursion details" });
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole("link", { name: "Learn Recursion" })).toHaveAttribute(
    "href",
    "/app/learn/recursion",
  );
  await page.getByRole("button", { name: "Show my path" }).click();
  await expect(page.getByText("Your path:")).toBeVisible();
});

test("notes, bookmarks and a revision sheet", async ({ page }) => {
  await signIn(page);
  await page.goto("/app/learn/recursion");
  await page.getByRole("button", { name: "Bookmark" }).click();
  await expect(page.getByRole("button", { name: "Bookmarked" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await page.getByRole("button", { name: "Add a note" }).click();
  await page.getByLabel("Your note").fill("Always write the **base case** first.");
  await page.getByRole("button", { name: "Save note" }).click();
  await expect(page.getByText("Note saved.")).toBeVisible();

  await page.goto("/app/notes");
  await expect(page.getByRole("link", { name: "Recursion" })).toBeVisible({ timeout: NAV_TIMEOUT });
  await expect(page.getByText("base case")).toBeVisible();
  await page.getByLabel("Search notes").fill("nothing-matches-this");
  await expect(page.getByRole("heading", { name: "No matching notes" })).toBeVisible();

  await page.getByRole("tab", { name: "Revision sheets" }).click();
  await page.getByRole("button", { name: "Choose concepts" }).click();
  await page.getByLabel("Recursion", { exact: true }).check();
  await page.getByRole("button", { name: "Write sheet for 1 concept(s)" }).click();
  await expect(page).toHaveURL(/\/app\/notes\/sheets\/[0-9a-f-]+/, { timeout: NAV_TIMEOUT });
  await expect(page.locator("article.print-sheet")).toContainText(/Recursion|recursion/, {
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByRole("button", { name: "Markdown" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Print / PDF" })).toBeVisible();
});
