/**
 * Question editor model. The rules mirror apps/api/app/content/models.py (Question) so the
 * form can explain a problem before saving; the server validates again and stays authoritative.
 */
import type { AdminOption, AdminQuestion } from "@/lib/admin";

export type QType = AdminQuestion["type"];
export const OPTION_IDS = ["a", "b", "c", "d", "e", "f"] as const;

export interface QuestionDraft {
  type: QType;
  difficulty: number;
  prompt: string;
  code: string;
  language: "python" | "cpp";
  options: AdminOption[];
  /** mcq: option id; multi_select: ids; true_false: boolean; code_output / short_answer: text. */
  answer: string | string[] | boolean;
  explanation: string;
  keyPoints: string;
  misconception_tag: string;
  diagnoses_prereq: string;
}

export function emptyOptions(n = 4): AdminOption[] {
  return OPTION_IDS.slice(0, n).map((id) => ({ id, text: "", why_wrong: "" }));
}

function defaultAnswer(type: QType): QuestionDraft["answer"] {
  if (type === "mcq") return "a";
  if (type === "multi_select") return [];
  if (type === "true_false") return true;
  return "";
}

export function draftFrom(q: AdminQuestion): QuestionDraft {
  const options = q.options?.map((o) => ({ ...o, why_wrong: o.why_wrong ?? "" })) ?? [];
  let answer: QuestionDraft["answer"];
  if (q.type === "multi_select") answer = Array.isArray(q.answer) ? q.answer.map(String) : [];
  else if (q.type === "true_false") answer = q.answer === true;
  else answer = typeof q.answer === "string" ? q.answer : String(q.answer ?? "");
  return {
    type: q.type,
    difficulty: q.difficulty,
    prompt: q.prompt,
    code: q.code ?? "",
    language: q.language,
    options: q.type === "mcq" || q.type === "multi_select" ? options : [],
    answer,
    explanation: q.explanation,
    keyPoints: (q.rubric?.key_points ?? []).join("\n"),
    misconception_tag: q.misconception_tag ?? "",
    diagnoses_prereq: q.diagnoses_prereq ?? "",
  };
}

/** Switching type keeps the shared fields and resets the parts whose shape differs. */
export function changeType(d: QuestionDraft, type: QType): QuestionDraft {
  if (type === d.type) return d;
  const needsOptions = type === "mcq" || type === "multi_select";
  let options: AdminOption[] = [];
  if (needsOptions) options = d.options.length >= 4 ? d.options : emptyOptions();
  if (type === "mcq") options = options.slice(0, 4);
  return { ...d, type, options, answer: defaultAnswer(type) };
}

export function keyPointList(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Every problem with the draft, in form order; empty means the server should accept it. */
export function validateDraft(d: QuestionDraft): string[] {
  const errors: string[] = [];
  if (![1, 2, 3].includes(d.difficulty)) errors.push("Difficulty must be 1, 2 or 3.");
  const prompt = d.prompt.trim().length;
  if (prompt < 10 || prompt > 1200) errors.push("The prompt needs 10 to 1200 characters.");
  const expl = d.explanation.trim().length;
  if (expl < 30 || expl > 1500) errors.push("The explanation needs 30 to 1500 characters.");

  if (d.type === "mcq" || d.type === "multi_select") {
    const ids = d.options.map((o) => o.id);
    if (new Set(ids).size !== ids.length) errors.push("Option ids must be unique.");
    if (d.options.some((o) => !o.text.trim())) errors.push("Every option needs text.");
    if (d.options.some((o) => o.text.length > 400))
      errors.push("Options are limited to 400 characters.");
    let correct = new Set<string>();
    if (d.type === "mcq") {
      if (d.options.length !== 4) errors.push("A single-choice question needs exactly 4 options.");
      if (typeof d.answer !== "string" || !ids.includes(d.answer))
        errors.push("Pick the correct option.");
      else correct = new Set([d.answer]);
    } else {
      if (d.options.length < 4) errors.push("A multi-select question needs at least 4 options.");
      const ans = Array.isArray(d.answer) ? d.answer : [];
      if (ans.length < 2 || ans.length >= ids.length || !ans.every((a) => ids.includes(a)))
        errors.push("Mark at least 2 correct options, but not all of them.");
      else correct = new Set(ans);
    }
    for (const o of d.options) {
      if (!correct.has(o.id) && (o.why_wrong ?? "").trim().length < 10)
        errors.push(`Option ${o.id.toUpperCase()} is incorrect: explain why in 10+ characters.`);
    }
  }
  if (d.type === "code_output") {
    if (!d.code.trim()) errors.push("A code-output question needs code.");
    if (typeof d.answer !== "string" || !d.answer.trim())
      errors.push("Enter the exact expected output.");
  }
  if (d.type === "short_answer") {
    if (typeof d.answer !== "string" || d.answer.trim().length < 10)
      errors.push("The reference answer needs at least 10 characters.");
    if (keyPointList(d.keyPoints).length === 0)
      errors.push("Add at least one rubric key point (one per line).");
  }
  if (d.misconception_tag.length > 100)
    errors.push("The misconception tag is limited to 100 characters.");
  return errors;
}

/** Request body for PUT /admin/content/questions/{id}. */
export function draftToBody(d: QuestionDraft, reviewed?: boolean) {
  const choice = d.type === "mcq" || d.type === "multi_select";
  return {
    type: d.type,
    difficulty: d.difficulty,
    prompt: d.prompt.trim(),
    code: d.code.trim() ? d.code : null,
    language: d.language,
    options: choice
      ? d.options.map((o) => ({
          id: o.id,
          text: o.text.trim(),
          ...(o.why_wrong?.trim() ? { why_wrong: o.why_wrong.trim() } : {}),
        }))
      : null,
    // code output is kept verbatim (the grader normalises it); a short reference answer is trimmed
    answer: d.type === "short_answer" && typeof d.answer === "string" ? d.answer.trim() : d.answer,
    explanation: d.explanation.trim(),
    rubric: d.type === "short_answer" ? { key_points: keyPointList(d.keyPoints) } : null,
    misconception_tag: d.misconception_tag.trim() || null,
    diagnoses_prereq: d.diagnoses_prereq || null,
    ...(reviewed === undefined ? {} : { reviewed }),
  };
}
