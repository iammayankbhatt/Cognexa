import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ContentEditor } from "@/components/admin/content-editor";
import { ModerationQueue } from "@/components/admin/moderation-queue";
import { adminNavFor } from "@/components/app/nav";
import type { AdminQuestion, ConceptContent, Report } from "@/lib/admin";

const apiMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: apiMock,
}));
const replace = vi.fn();
let search = new URLSearchParams();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  usePathname: () => "/admin/content",
  useSearchParams: () => search,
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() } }));

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const report: Report = {
  id: "11111111-1111-1111-1111-111111111111",
  reason: "incorrect",
  comment: "It says recursion never overflows.",
  status: "open",
  resolution_note: null,
  reported_at: "2026-11-20T10:00:00Z",
  reporter: "student@example.com",
  message: {
    id: "m1",
    content: "Recursion uses the **call stack**.",
    mode: "graphrag",
    answered_at: "2026-11-20T09:59:00Z",
    question: "Why does my recursive function crash?",
    concepts: [
      { id: "recursion", name: "Recursion", role: "matched" },
      { id: "call_stack", name: "Call Stack", role: "prerequisite" },
    ],
    trace: {
      mode: "graphrag",
      classification_path: "llm",
      concepts: [],
      chunks: [
        {
          id: "recursion#pitfalls",
          concept_id: "recursion",
          kind: "pitfalls",
          tokens: 90,
          score: null,
        },
      ],
      controller: [],
    },
  },
};

describe("ModerationQueue", () => {
  beforeEach(() => {
    apiMock.mockReset();
    apiMock.mockImplementation((path: string) => {
      if (path.startsWith("/admin/reports?")) return Promise.resolve({ items: [report], total: 1 });
      if (path.startsWith("/admin/feedback/by-concept"))
        return Promise.resolve({
          items: [
            {
              concept_id: "recursion",
              name: "Recursion",
              thumbs_down: 3,
              thumbs_up: 1,
              reports: 1,
            },
          ],
        });
      if (path === `/admin/reports/${report.id}`)
        return Promise.resolve({ id: report.id, status: "resolved" });
      return Promise.reject(new Error(`unexpected ${path}`));
    });
  });

  it("shows the reported answer with its question, comment and a fix-content link", async () => {
    wrap(<ModerationQueue />);
    expect(await screen.findByText("Why does my recursive function crash?")).toBeInTheDocument();
    expect(screen.getByText(/never overflows/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Fix content: Recursion/ })).toHaveAttribute(
      "href",
      "/admin/content?concept=recursion&chunk=recursion%23pitfalls",
    );
    const table = await screen.findByRole("table");
    expect(within(table).getByText("Recursion")).toBeInTheDocument();
  });

  it("resolves a report with the typed note", async () => {
    const user = userEvent.setup();
    wrap(<ModerationQueue />);
    await user.type(await screen.findByLabelText("Resolution note"), "Fixed the pitfalls note.");
    await user.click(screen.getByRole("button", { name: /Resolve/ }));
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(`/admin/reports/${report.id}`, {
        method: "POST",
        body: { status: "resolved", note: "Fixed the pitfalls note." },
      }),
    );
  });
});

const question: AdminQuestion = {
  id: "stack-q01",
  concept_id: "stack",
  type: "mcq",
  difficulty: 1,
  prompt: "Which operation removes the top element of a stack?",
  code: null,
  language: "python",
  options: [
    { id: "a", text: "pop", why_wrong: null },
    { id: "b", text: "push", why_wrong: "push adds an element instead" },
    { id: "c", text: "peek", why_wrong: "peek only reads the top element" },
    { id: "d", text: "enqueue", why_wrong: "enqueue belongs to queues, not stacks" },
  ],
  answer: "a",
  explanation: "pop removes and returns the most recently pushed element (LIFO order).",
  rubric: null,
  misconception_tag: null,
  diagnoses_prereq: null,
  status: "active",
  source: "notes",
  reviewed: false,
  stats: { attempts: 12, pct_correct: 1, discrimination: null, flags: ["too_easy"] },
};
const stack = {
  id: "stack",
  subject_id: "dsa",
  name: "Stack",
  cluster: "linear",
  difficulty: 1,
  order_index: 1,
  description: "LIFO",
  aliases: [],
  keywords: [],
  status: "active",
};
const content: ConceptContent = {
  concept: stack,
  chunks: [
    {
      id: "stack#overview",
      concept_id: "stack",
      kind: "overview",
      heading: "Overview",
      text: "A stack is a last-in, first-out collection.",
      order: 0,
      reviewed: false,
      source: "notes",
      embedded: true,
    },
  ],
  chunk_kinds: ["overview", "pitfalls"],
  questions: [question],
};

describe("ContentEditor", () => {
  beforeEach(() => {
    search = new URLSearchParams("concept=stack");
    apiMock.mockReset();
    apiMock.mockImplementation((path: string) => {
      if (path === "/admin/graph")
        return Promise.resolve({ subject_id: "dsa", concepts: [stack], edges: [] });
      if (path === "/admin/content/concepts/stack") return Promise.resolve(content);
      if (path === "/admin/content/questions/stack-q01") return Promise.resolve(question);
      return Promise.reject(new Error(`unexpected ${path}`));
    });
  });

  it("asks for a concept when none is selected", async () => {
    search = new URLSearchParams();
    wrap(<ContentEditor />);
    expect(await screen.findByText("Pick a concept")).toBeInTheDocument();
  });

  it("lists questions with statistics flags", async () => {
    const user = userEvent.setup();
    wrap(<ContentEditor />);
    await user.click(await screen.findByRole("tab", { name: /Questions/ }));
    expect(screen.getByText("Everyone gets it right")).toBeInTheDocument();
    expect(screen.getByText(/12 attempts · 100% correct/)).toBeInTheDocument();
  });

  it("validates a question before saving and sends the edited body", async () => {
    const user = userEvent.setup();
    wrap(<ContentEditor />);
    await user.click(await screen.findByRole("tab", { name: /Questions/ }));
    await user.click(screen.getByRole("button", { name: /Edit/ }));
    const prompt = await screen.findByLabelText(/Prompt/);
    await user.clear(prompt);
    await user.type(prompt, "Short");
    await user.click(screen.getByRole("button", { name: "Save question" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The prompt needs 10 to 1200 characters.",
    );
    expect(apiMock).not.toHaveBeenCalledWith(
      "/admin/content/questions/stack-q01",
      expect.anything(),
    );

    await user.clear(prompt);
    await user.click(prompt);
    await user.paste("Which stack operation removes the top element?"); // fast under load
    await user.click(screen.getByRole("button", { name: "Save question" }));
    await waitFor(() =>
      expect(apiMock).toHaveBeenCalledWith(
        "/admin/content/questions/stack-q01",
        expect.objectContaining({
          method: "PUT",
          body: expect.objectContaining({
            type: "mcq",
            prompt: "Which stack operation removes the top element?",
            answer: "a",
            reviewed: false,
          }),
        }),
      ),
    );
  });
});

describe("admin navigation", () => {
  it("shows reviewers the content tools but not user or AI settings", () => {
    const reviewer = adminNavFor("reviewer").map((i) => i.href);
    expect(reviewer).toEqual(
      expect.arrayContaining([
        "/admin/graph",
        "/admin/proposals",
        "/admin/content",
        "/admin/moderation",
      ]),
    );
    expect(reviewer).not.toContain("/admin/users");
    expect(reviewer).not.toContain("/admin/settings");
    expect(adminNavFor("admin").map((i) => i.href)).toContain("/admin/users");
    expect(adminNavFor("student")).toEqual([]);
  });
});
