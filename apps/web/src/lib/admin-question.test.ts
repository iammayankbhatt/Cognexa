import { describe, expect, it } from "vitest";

import type { AdminQuestion } from "@/lib/admin";
import {
  changeType,
  draftFrom,
  draftToBody,
  emptyOptions,
  validateDraft,
} from "@/lib/admin-question";

const base: AdminQuestion = {
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
  stats: { attempts: 0, pct_correct: null, discrimination: null, flags: [] },
};

describe("question draft validation", () => {
  it("accepts a valid single-choice question and round-trips it", () => {
    const d = draftFrom(base);
    expect(validateDraft(d)).toEqual([]);
    const body = draftToBody(d, true);
    expect(body.options).toHaveLength(4);
    expect(body.options?.[0]).toEqual({ id: "a", text: "pop" }); // no empty why_wrong sent
    expect(body.answer).toBe("a");
    expect(body.rubric).toBeNull();
    expect(body.reviewed).toBe(true);
  });

  it("requires a why_wrong for every incorrect option", () => {
    const d = draftFrom(base);
    d.options[1] = { ...d.options[1], why_wrong: "short" };
    expect(validateDraft(d)).toContain("Option B is incorrect: explain why in 10+ characters.");
  });

  it("checks prompt and explanation lengths and difficulty", () => {
    const d = { ...draftFrom(base), prompt: "short", explanation: "too short", difficulty: 4 };
    const errs = validateDraft(d);
    expect(errs).toContain("Difficulty must be 1, 2 or 3.");
    expect(errs).toContain("The prompt needs 10 to 1200 characters.");
    expect(errs).toContain("The explanation needs 30 to 1500 characters.");
  });

  it("multi-select needs two or more correct options, not all", () => {
    let d = changeType(draftFrom(base), "multi_select");
    d = { ...d, options: d.options.map((o) => ({ ...o, why_wrong: "a long enough reason" })) };
    expect(validateDraft({ ...d, answer: ["a"] })).toContain(
      "Mark at least 2 correct options, but not all of them.",
    );
    expect(validateDraft({ ...d, answer: ["a", "b", "c", "d"] })).toContain(
      "Mark at least 2 correct options, but not all of them.",
    );
    expect(validateDraft({ ...d, answer: ["a", "b"] })).toEqual([]);
  });

  it("switching to true/false drops options and defaults the answer", () => {
    const d = changeType(draftFrom(base), "true_false");
    expect(d.options).toEqual([]);
    expect(d.answer).toBe(true);
    expect(validateDraft(d)).toEqual([]);
    expect(draftToBody(d).options).toBeNull();
  });

  it("code output needs code and an expected output, kept verbatim", () => {
    const d = changeType(draftFrom(base), "code_output");
    expect(validateDraft(d)).toEqual([
      "A code-output question needs code.",
      "Enter the exact expected output.",
    ]);
    const ok = { ...d, code: "print(1)", answer: "1\n" };
    expect(validateDraft(ok)).toEqual([]);
    expect(draftToBody(ok).answer).toBe("1\n");
  });

  it("short answer needs a reference answer and rubric key points", () => {
    const d = changeType(draftFrom(base), "short_answer");
    expect(validateDraft(d)).toEqual([
      "The reference answer needs at least 10 characters.",
      "Add at least one rubric key point (one per line).",
    ]);
    const ok = {
      ...d,
      answer: "  LIFO: last in, first out.  ",
      keyPoints: "LIFO\n\n removes top \n",
    };
    expect(validateDraft(ok)).toEqual([]);
    const body = draftToBody(ok);
    expect(body.rubric).toEqual({ key_points: ["LIFO", "removes top"] });
    expect(body.answer).toBe("LIFO: last in, first out.");
  });

  it("emptyOptions gives lettered ids", () => {
    expect(emptyOptions(5).map((o) => o.id)).toEqual(["a", "b", "c", "d", "e"]);
  });
});
