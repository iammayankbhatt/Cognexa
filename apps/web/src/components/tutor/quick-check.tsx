"use client";

import { HelpCircle, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

interface QuickCheckProps {
  question: string;
  /** Only the latest unanswered quick check takes an answer. */
  active: boolean;
  disabled?: boolean;
  onAnswer: (text: string) => void;
}

/** The agentic step's diagnostic question: answering it continues the same turn. */
export function QuickCheck({ question, active, disabled, onAnswer }: QuickCheckProps) {
  const [text, setText] = useState("");
  const submit = () => {
    const t = text.trim();
    if (!t) return;
    onAnswer(t);
    setText("");
  };
  return (
    <div
      className="rounded-xl border border-accent/50 bg-surface-2 p-4"
      role="group"
      aria-label="Quick check"
    >
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold tracking-wide text-accent uppercase">
        <HelpCircle aria-hidden className="size-4" />
        Quick check before I answer
      </div>
      <p className="text-sm text-text">{question.replace(/^Quick check:\s*/i, "")}</p>
      {active ? (
        <form
          className="mt-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <label htmlFor="quick-check-answer" className="sr-only">
            Your answer
          </label>
          <input
            id="quick-check-answer"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={disabled}
            placeholder="Answer in your own words…"
            className="h-9 min-w-0 flex-1 rounded-lg border border-border bg-surface px-3 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="submit" disabled={disabled || !text.trim()} size="lg">
            <Send aria-hidden className="size-4" />
            Answer
          </Button>
        </form>
      ) : (
        <p className="mt-2 text-xs text-muted">Answered below.</p>
      )}
    </div>
  );
}
