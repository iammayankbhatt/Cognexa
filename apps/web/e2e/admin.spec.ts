import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { createUser, deleteUser, localStack, setProfile, type LocalStack } from "./helpers";

/**
 * Admin console (Phase 11) on the local stack. Nothing here changes the concept graph: the cycle
 * check is shown but never saved, and uploaded notes are rejected, not approved.
 */
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

async function signInAs(page: Page, role: "reviewer" | "admin") {
  const u = await createUser(stack!, role === "admin" ? "Ada Admin" : "Rae Reviewer");
  created.push(u.id);
  await setProfile(stack!, u.id, { role, onboarding_completed: true });
  await page.goto("/login");
  await page.getByLabel("Email").fill(u.email);
  await page.getByLabel("Password").fill(u.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/app$/, { timeout: NAV_TIMEOUT });
  return u;
}

test("a reviewer sees the content tools, is refused admin-only pages and the editor explains cycles", async ({
  page,
}) => {
  await signInAs(page, "reviewer");
  await page.goto("/admin/users");
  await expect(page.getByText("403: Not allowed")).toBeVisible({ timeout: NAV_TIMEOUT });

  await page.goto("/admin/graph");
  await expect(page.getByRole("heading", { name: "Graph editor" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await page.getByRole("tab", { name: "Table" }).click();
  await page.getByLabel("Filter concepts").fill("recursion");
  await page.getByRole("button", { name: "Recursion", exact: true }).click();
  // Conditionals & Loops -> Functions -> Call Stack -> Recursion already exists
  await page.getByLabel("Relation", { exact: true }).selectOption("this_prereq_of");
  await page.getByLabel("Concept", { exact: true }).selectOption("control_flow");
  const alert = page.getByRole("alert").filter({ hasText: "would create a cycle" });
  await expect(alert).toBeVisible();
  await expect(alert).toContainText("call_stack");
  await expect(page.getByRole("button", { name: "Add edge" })).toBeDisabled();
});

test("uploaded notes become proposals that a reviewer can reject with a note", async ({ page }) => {
  await signInAs(page, "reviewer");
  await page.goto("/admin/proposals");
  await expect(page.getByRole("heading", { name: "Ingest lecture notes" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  const token = randomUUID().slice(0, 8);
  const name = `e2e-notes-${token}.md`;
  const notes = [
    "# Stacks",
    "",
    `A stack (${token}) keeps its elements in last-in, first-out order: push puts an element on`,
    "top and pop removes the most recently pushed one. Function calls use a stack of frames, and",
    "undo features in editors keep the previous states on a stack as well.",
  ].join("\n");
  await page.locator("#ingest-file").setInputFiles({
    name,
    mimeType: "text/markdown",
    buffer: Buffer.from(notes),
  });
  const row = page.getByRole("listitem").filter({ hasText: name });
  await row.getByRole("button", { name: "Show proposals" }).click({ timeout: NAV_TIMEOUT });
  const first = page.getByRole("list", { name: "Proposals" }).getByRole("button").first();
  await first.click();
  await page.getByLabel("Note (optional)").fill("e2e: not needed");
  await page.getByRole("button", { name: "Reject" }).click();
  await expect(page.getByRole("article", { name: "Proposal detail" })).toContainText(
    /Rejected on .*: e2e: not needed/,
    { timeout: NAV_TIMEOUT },
  );
});

test("an admin opens content, moderation and users with usage", async ({ page }) => {
  await signInAs(page, "admin");
  await page.goto("/admin/content?concept=stack");
  await expect(page.getByRole("heading", { name: "Content & questions" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await page.getByRole("tab", { name: /Questions/ }).click();
  await page.getByRole("button", { name: "Edit" }).first().click();
  await expect(page.getByText("Preview (as the student sees it)")).toBeVisible();
  await page.keyboard.press("Escape");

  await page.goto("/admin/moderation");
  await expect(page.getByRole("heading", { name: "Moderation" })).toBeVisible({
    timeout: NAV_TIMEOUT,
  });
  await expect(page.getByRole("heading", { name: "Ratings by concept (30 days)" })).toBeVisible();

  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: "Users" })).toBeVisible({ timeout: NAV_TIMEOUT });
  await page.getByRole("button", { name: "Usage" }).first().click();
  await expect(page.getByText("Chat contents are not shown")).toBeVisible();
});
