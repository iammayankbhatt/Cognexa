"use client";

import { Check, X } from "lucide-react";

import { Markdown } from "@/components/tutor/markdown";
import type { AnswerView, QuizQuestion, ResponseValue } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

export const TYPE_LABEL: Record<string, string> = {
  mcq: "Choose one",
  multi_select: "Choose all that apply",
  true_false: "True or false",
  code_output: "What does this code print?",
  short_answer: "Answer in your own words",
};

/** Human-readable form of an answer value for a question. */
export function describeAnswer(q: QuizQuestion, value: ResponseValue | undefined): string {
  if (value === null || value === undefined || value === "") return "No answer";
  if (q.type === "true_false") return value ? "True" : "False";
  const text = (id: string) => q.options?.find((o) => o.id === id)?.text ?? id;
  if (Array.isArray(value)) return value.length ? value.map(text).join("; ") : "No answer";
  if (q.type === "mcq") return text(String(value));
  return String(value);
}

interface QuestionViewProps {
  question: QuizQuestion;
  value: ResponseValue | undefined;
  onChange: (value: ResponseValue) => void;
  /** Graded answer to show (immediate feedback or results); inputs are locked when set. */
  graded?: AnswerView | null;
  disabled?: boolean;
}

function OptionButton({
  index,
  label,
  selected,
  multi,
  state,
  disabled,
  onClick,
}: {
  index: number;
  label: string;
  selected: boolean;
  multi: boolean;
  state?: "correct" | "wrong" | "missed";
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role={multi ? "checkbox" : "radio"}
      aria-checked={selected}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring",
        selected ? "border-accent bg-surface-2" : "border-border bg-surface hover:border-accent/60",
        state === "correct" && "border-success bg-success/10",
        state === "wrong" && "border-danger bg-danger/10",
        state === "missed" && "border-dashed border-success",
        disabled && "cursor-default",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "flex size-6 shrink-0 items-center justify-center border text-xs font-semibold",
          multi ? "rounded-md" : "rounded-full",
          selected ? "border-accent bg-accent text-bg" : "border-border text-muted",
        )}
      >
        {index + 1}
      </span>
      <span className="min-w-0 flex-1">
        <Markdown text={label} className="[&_p]:my-0" />
      </span>
      {state === "correct" && <Check aria-label="correct" className="size-4 text-success" />}
      {state === "wrong" && <X aria-label="incorrect" className="size-4 text-danger" />}
    </button>
  );
}

export function QuestionView({
  question: q,
  value,
  onChange,
  graded,
  disabled,
}: QuestionViewProps) {
  const locked = disabled || Boolean(graded && (graded.score !== undefined || graded.pending));
  const correct = graded?.correct_answer;
  const optionState = (id: string): "correct" | "wrong" | "missed" | undefined => {
    if (correct === undefined || correct === null) return undefined;
    const isRight = Array.isArray(correct) ? correct.includes(id) : correct === id;
    const chosen = Array.isArray(value) ? value.includes(id) : value === id;
    if (isRight && chosen) return "correct";
    if (!isRight && chosen) return "wrong";
    if (isRight) return "missed";
    return undefined;
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <p className="text-xs font-semibold tracking-wide text-muted uppercase">
          {TYPE_LABEL[q.type]} · difficulty {q.difficulty}
          {q.concept_name ? ` · ${q.concept_name}` : ""}
        </p>
        <Markdown text={q.prompt} className="text-base" />
        {q.code && <Markdown text={`\`\`\`${q.language}\n${q.code}\n\`\`\``} />}
      </div>

      {(q.type === "mcq" || q.type === "multi_select") && (
        <div
          role={q.type === "mcq" ? "radiogroup" : "group"}
          aria-label="Options"
          className="space-y-2"
        >
          {(q.options ?? []).map((o, i) => {
            const multi = q.type === "multi_select";
            const list = Array.isArray(value) ? value : [];
            const selected = multi ? list.includes(o.id) : value === o.id;
            return (
              <OptionButton
                key={o.id}
                index={i}
                label={o.text}
                selected={selected}
                multi={multi}
                state={optionState(o.id)}
                disabled={locked}
                onClick={() =>
                  onChange(
                    multi ? (selected ? list.filter((x) => x !== o.id) : [...list, o.id]) : o.id,
                  )
                }
              />
            );
          })}
        </div>
      )}

      {q.type === "true_false" && (
        <div role="radiogroup" aria-label="True or false" className="grid grid-cols-2 gap-2">
          {[true, false].map((v, i) => {
            const right = correct === undefined || correct === null ? undefined : correct === v;
            const chosen = value === v;
            return (
              <OptionButton
                key={String(v)}
                index={i}
                label={v ? "True" : "False"}
                selected={chosen}
                multi={false}
                state={
                  right === undefined
                    ? undefined
                    : right && chosen
                      ? "correct"
                      : chosen
                        ? "wrong"
                        : right
                          ? "missed"
                          : undefined
                }
                disabled={locked}
                onClick={() => onChange(v)}
              />
            );
          })}
        </div>
      )}

      {(q.type === "code_output" || q.type === "short_answer") && (
        <div className="space-y-1.5">
          <label htmlFor={`answer-${q.id}`} className="text-sm font-medium">
            {q.type === "code_output" ? "Exact output" : "Your answer"}
          </label>
          <textarea
            id={`answer-${q.id}`}
            value={typeof value === "string" ? value : ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={locked}
            maxLength={4000}
            rows={q.type === "code_output" ? 3 : 5}
            spellCheck={q.type === "short_answer"}
            placeholder={
              q.type === "code_output"
                ? "Type what the program prints…"
                : "Explain in a few sentences…"
            }
            className={cn(
              "w-full resize-y rounded-xl border border-border bg-surface px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring",
              q.type === "code_output" && "font-mono",
            )}
          />
          <p className="text-xs text-muted">Ctrl+Enter to confirm.</p>
        </div>
      )}
    </div>
  );
}
