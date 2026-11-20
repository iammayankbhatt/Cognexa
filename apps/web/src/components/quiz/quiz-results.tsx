"use client";

import { BookOpen, Clock, MessageSquare, RefreshCw, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { describeAnswer } from "@/components/quiz/question-view";
import { FeedbackPanel, tutorLink } from "@/components/quiz/feedback-panel";
import { NextStepCard } from "@/components/recommend/next-step-card";
import { masteryLevel } from "@/components/shared/mastery";
import { Button, buttonVariants } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { MODE_LABEL, useCreateQuiz, useRegrade } from "@/lib/quiz/use-quiz";
import type { QuizSession } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

const LEVEL_STROKE = { low: "var(--danger)", mid: "var(--warning)", high: "var(--success)" };
const LEVEL_BG = { low: "bg-danger", mid: "bg-warning", high: "bg-success" };

export function ScoreRing({ ratio, label }: { ratio: number; label: string }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const level = masteryLevel(ratio);
  return (
    <svg viewBox="0 0 100 100" className="size-32" role="img" aria-label={label}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="10" />
      <circle
        cx="50"
        cy="50"
        r={r}
        fill="none"
        stroke={LEVEL_STROKE[level]}
        strokeWidth="10"
        strokeLinecap="round"
        strokeDasharray={`${c * ratio} ${c}`}
        transform="rotate(-90 50 50)"
        className="motion-safe:transition-[stroke-dasharray] motion-safe:duration-200"
      />
      <text x="50" y="55" textAnchor="middle" fontSize="20" fontWeight="600" fill="var(--text)">
        {Math.round(ratio * 100)}%
      </text>
    </svg>
  );
}

export function QuizResults({ session }: { session: QuizSession }) {
  const router = useRouter();
  const regrade = useRegrade(session.id);
  const create = useCreateQuiz();
  const max = session.max_score ?? session.questions.length;
  const score = session.score ?? 0;
  const ratio = max ? score / max : 0;
  const wrong = session.questions.filter((q) => (q.answer?.score ?? 0) < 1 && !q.answer?.pending);
  const prereqNames = Object.fromEntries(
    session.weak_prerequisites.map((p) => [p.concept_id, p.name]),
  );

  const retry = async () => {
    try {
      const s = await create.mutateAsync({ mode: "concept", question_ids: wrong.map((q) => q.id) });
      router.push(`/app/quizzes/${s.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start the retry.");
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <section className="flex flex-col items-center gap-4 rounded-2xl border border-border bg-surface p-6 sm:flex-row">
        <ScoreRing ratio={ratio} label={`Score ${Math.round(ratio * 100)} percent`} />
        <div className="flex-1 space-y-2 text-center sm:text-left">
          <h1 className="text-xl font-semibold">{MODE_LABEL[session.mode]} results</h1>
          <p className="text-sm text-muted">
            {score.toFixed(score % 1 ? 1 : 0)} of {max} points. Your mastery has been updated.
          </p>
          {session.pending > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-sm text-warning">
              <Clock aria-hidden className="size-4" />
              {session.pending} short answer(s) are waiting for the AI grader.
              <Button
                variant="outline"
                size="sm"
                onClick={() => regrade.mutate()}
                disabled={regrade.isPending}
              >
                <RefreshCw aria-hidden className="size-3.5" />
                {regrade.isPending ? "Grading…" : "Grade now"}
              </Button>
            </div>
          )}
          <div className="flex flex-wrap justify-center gap-2 pt-1 sm:justify-start">
            {wrong.length > 0 && (
              <Button onClick={() => void retry()} disabled={create.isPending}>
                <RotateCcw aria-hidden className="size-4" />
                Retry the {wrong.length} I missed
              </Button>
            )}
            <Link href="/app/quizzes" className={buttonVariants({ variant: "outline" })}>
              Back to quizzes
            </Link>
          </div>
        </div>
      </section>

      {session.per_concept.length > 0 && (
        <section className="space-y-3 rounded-2xl border border-border bg-surface p-5">
          <h2 className="text-sm font-semibold">By concept</h2>
          <ul className="space-y-2">
            {session.per_concept.map((c) => {
              const r = c.max ? c.score / c.max : 0;
              return (
                <li
                  key={c.concept_id}
                  className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1"
                >
                  <Link
                    href={`/app/learn/${c.concept_id}`}
                    className="truncate text-sm text-text hover:underline"
                  >
                    {c.name}
                  </Link>
                  <span className="text-xs text-muted tabular-nums">
                    {c.score.toFixed(c.score % 1 ? 1 : 0)}/{c.max}
                  </span>
                  <div className="col-span-2 h-1.5 overflow-hidden rounded-full bg-surface-2">
                    <div
                      className={cn("h-full rounded-full", LEVEL_BG[masteryLevel(r)])}
                      style={{ width: `${r * 100}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {session.weak_prerequisites.length > 0 && (
        <section className="space-y-3 rounded-2xl border border-warning/40 bg-warning/5 p-5">
          <h2 className="text-sm font-semibold">Weak prerequisite detected</h2>
          <p className="text-sm text-muted">
            Some mistakes point to a concept that comes earlier in the syllabus. Reviewing it first
            usually helps more than repeating the quiz.
          </p>
          <ul className="space-y-2">
            {session.weak_prerequisites.map((p) => (
              <li key={p.concept_id} className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium">{p.name}</span>
                <Link
                  href={`/app/learn/${p.concept_id}`}
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  <BookOpen aria-hidden className="size-3.5" /> Learn it
                </Link>
                <Link
                  href={tutorLink(`Explain ${p.name} and how it is used in what I just practised.`)}
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  <MessageSquare aria-hidden className="size-3.5" /> Ask the tutor about it
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {session.mode !== "pretest" && session.mode !== "posttest" && <NextStepCard surface="quiz" />}

      <section className="space-y-3">
        <h2 className="text-sm font-semibold">Questions</h2>
        <ol className="space-y-4">
          {session.questions.map((q, i) => (
            <li key={q.id} className="space-y-2 rounded-2xl border border-border bg-surface p-4">
              <p className="text-xs text-muted">
                Question {i + 1} · {q.concept_name}
              </p>
              <p className="text-sm font-medium text-text">{q.prompt}</p>
              <p className="text-sm text-muted">
                Your answer:{" "}
                <span className="text-text">{describeAnswer(q, q.answer?.response)}</span>
              </p>
              {q.answer && (q.answer.score !== undefined || q.answer.pending) ? (
                <FeedbackPanel
                  question={q}
                  answer={q.answer}
                  prereqName={
                    q.answer.diagnoses_prereq ? prereqNames[q.answer.diagnoses_prereq] : undefined
                  }
                />
              ) : (
                q.explanation && <p className="text-sm text-muted">{q.explanation}</p>
              )}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
