"use client";

import { ArrowLeft, ArrowRight, Flag, Timer } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { FeedbackPanel } from "@/components/quiz/feedback-panel";
import { QuestionView } from "@/components/quiz/question-view";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { isAnswered, MODE_LABEL, useAnswer, useSubmit } from "@/lib/quiz/use-quiz";
import type { AnswerView, QuizSession, ResponseValue } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

function useCountdown(deadline: string | null): number | null {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!deadline) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [deadline]);
  return deadline ? Math.max(0, Math.round((new Date(deadline).getTime() - now) / 1000)) : null;
}

function clock(s: number): string {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

interface QuizPlayerProps {
  session: QuizSession;
  /** Called with the submitted session (results). */
  onFinished: (s: QuizSession) => void;
}

/**
 * One question per screen. Immediate mode: "Check" grades the answer and shows feedback, then
 * "Next". Exam mode: answers are kept until "Submit quiz". Keys: 1-6 choose an option, Enter
 * checks / moves on (Ctrl+Enter inside a text answer), F flags the question.
 */
export function QuizPlayer({ session, onFinished }: QuizPlayerProps) {
  const immediate = session.feedback_mode === "immediate";
  const total = session.questions.length;
  const firstOpen = session.questions.findIndex((q) => !q.answer);
  const [index, setIndex] = useState(firstOpen < 0 ? total - 1 : firstOpen);
  const [responses, setResponses] = useState<Record<string, ResponseValue>>(() =>
    Object.fromEntries(
      session.questions.filter((q) => q.answer).map((q) => [q.id, q.answer!.response]),
    ),
  );
  const [graded, setGraded] = useState<Record<string, AnswerView>>(() =>
    Object.fromEntries(
      session.questions
        .filter((q) => q.answer && (q.answer.score !== undefined || q.answer.pending))
        .map((q) => [q.id, q.answer!]),
    ),
  );
  const [flags, setFlags] = useState<Set<string>>(new Set());
  const shownAt = useRef(0);
  const answer = useAnswer(session.id);
  const submit = useSubmit(session.id);
  const remaining = useCountdown(session.deadline);
  const autoSubmitted = useRef(false);

  const q = session.questions[index];
  const value = responses[q.id];
  const result = graded[q.id];
  const answeredCount = session.questions.filter((x) => isAnswered(responses[x.id])).length;

  useEffect(() => {
    shownAt.current = Date.now();
  }, [index]);

  const finish = useCallback(async () => {
    try {
      const done = await submit.mutateAsync(immediate ? {} : responses);
      onFinished(done);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not submit the quiz.");
    }
  }, [submit, immediate, responses, onFinished]);

  useEffect(() => {
    if (remaining === 0 && !autoSubmitted.current) {
      autoSubmitted.current = true;
      toast("Time is up: submitting your quiz.");
      void finish();
    }
  }, [remaining, finish]);

  const check = async () => {
    if (!isAnswered(value)) return;
    try {
      const a = await answer.mutateAsync({
        question_id: q.id,
        response: value ?? null,
        time_ms: Date.now() - shownAt.current,
      });
      setGraded((g) => ({ ...g, [q.id]: a }));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not check the answer.");
    }
  };

  const next = () => setIndex((i) => Math.min(total - 1, i + 1));
  const prev = () => setIndex((i) => Math.max(0, i - 1));
  const isLast = index === total - 1;

  const primary = () => {
    if (immediate) {
      if (!result) return void check();
      if (isLast) return void finish();
      return next();
    }
    if (isLast) {
      const missing = total - answeredCount;
      if (missing > 0 && !window.confirm(`${missing} question(s) are unanswered. Submit anyway?`))
        return;
      return void finish();
    }
    next();
  };
  const primaryLabel = immediate
    ? !result
      ? "Check answer"
      : isLast
        ? "See results"
        : "Next question"
    : isLast
      ? "Submit quiz"
      : "Next";

  const onKey = (e: React.KeyboardEvent) => {
    const inText = (e.target as HTMLElement).tagName === "TEXTAREA";
    if (e.key === "Enter" && (!inText || e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      primary();
      return;
    }
    if (inText) return;
    if ((e.key === "f" || e.key === "F") && !e.ctrlKey && !e.metaKey) {
      setFlags((f) => {
        const n = new Set(f);
        if (n.has(q.id)) n.delete(q.id);
        else n.add(q.id);
        return n;
      });
      return;
    }
    const n = Number(e.key);
    if (Number.isInteger(n) && n >= 1 && !result) {
      if (q.type === "true_false" && n <= 2) setResponses((r) => ({ ...r, [q.id]: n === 1 }));
      const opt = q.options?.[n - 1];
      if (opt && q.type === "mcq") setResponses((r) => ({ ...r, [q.id]: opt.id }));
      if (opt && q.type === "multi_select") {
        const list = Array.isArray(value) ? value : [];
        setResponses((r) => ({
          ...r,
          [q.id]: list.includes(opt.id) ? list.filter((x) => x !== opt.id) : [...list, opt.id],
        }));
      }
    }
  };

  const busy = answer.isPending || submit.isPending;
  return (
    <div className="mx-auto max-w-3xl space-y-5 outline-none" onKeyDown={onKey} tabIndex={-1}>
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="font-medium">
            {MODE_LABEL[session.mode]} · Question {index + 1} of {total}
          </span>
          <span className="flex items-center gap-3 text-muted">
            {remaining !== null && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 tabular-nums",
                  remaining < 30 && "text-danger",
                )}
                aria-label={`Time left ${clock(remaining)}`}
              >
                <Timer aria-hidden className="size-4" />
                {clock(remaining)}
              </span>
            )}
            <span>{immediate ? "Instant feedback" : "Exam mode"}</span>
          </span>
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-surface-2"
          role="progressbar"
          aria-label="Quiz progress"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={immediate ? Object.keys(graded).length : answeredCount}
        >
          <div
            className="h-full rounded-full bg-primary transition-[width] duration-200"
            style={{
              width: `${((immediate ? Object.keys(graded).length : answeredCount) / total) * 100}%`,
            }}
          />
        </div>
        <nav aria-label="Questions" className="flex flex-wrap gap-1.5">
          {session.questions.map((x, i) => {
            const g = graded[x.id];
            return (
              <button
                key={x.id}
                type="button"
                onClick={() => setIndex(i)}
                aria-current={i === index ? "step" : undefined}
                aria-label={`Question ${i + 1}${flags.has(x.id) ? ", flagged" : ""}${isAnswered(responses[x.id]) ? ", answered" : ""}`}
                className={cn(
                  "relative size-7 rounded-md border text-xs tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  i === index ? "border-accent text-text" : "border-border text-muted",
                  g?.is_correct && "bg-success/15",
                  g && !g.is_correct && !g.pending && "bg-danger/15",
                  !g && isAnswered(responses[x.id]) && "bg-surface-2",
                )}
              >
                {i + 1}
                {flags.has(x.id) && (
                  <span
                    aria-hidden
                    className="absolute -top-1 -right-1 size-2 rounded-full bg-warning"
                  />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-5">
        <QuestionView
          key={q.id}
          question={q}
          value={value}
          onChange={(v) => setResponses((r) => ({ ...r, [q.id]: v }))}
          graded={result}
          disabled={busy}
        />
      </div>

      {result && <FeedbackPanel question={q} answer={result} prereqName={undefined} />}

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={prev} disabled={index === 0}>
          <ArrowLeft aria-hidden className="size-4" />
          Back
        </Button>
        <Button
          variant="ghost"
          aria-pressed={flags.has(q.id)}
          onClick={() =>
            setFlags((f) => {
              const n = new Set(f);
              if (n.has(q.id)) n.delete(q.id);
              else n.add(q.id);
              return n;
            })
          }
        >
          <Flag
            aria-hidden
            className={cn("size-4", flags.has(q.id) && "fill-warning text-warning")}
          />
          {flags.has(q.id) ? "Flagged" : "Flag for later"}
        </Button>
        <span className="ml-auto text-xs text-muted">
          {answeredCount}/{total} answered
        </span>
        <Button
          size="lg"
          onClick={primary}
          disabled={busy || (immediate && !result && !isAnswered(value))}
        >
          {busy ? "Working…" : primaryLabel}
          {!busy && <ArrowRight aria-hidden className="size-4" />}
        </Button>
      </div>
      <p className="text-xs text-muted">
        Keys: 1–6 choose · Enter {immediate ? "check / next" : "next"} · F flag
      </p>
    </div>
  );
}
