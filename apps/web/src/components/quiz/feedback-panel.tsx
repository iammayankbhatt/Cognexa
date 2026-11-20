import { BookOpen, CheckCircle2, Clock, MessageSquare, XCircle } from "lucide-react";
import Link from "next/link";

import { describeAnswer } from "@/components/quiz/question-view";
import { Markdown } from "@/components/tutor/markdown";
import type { AnswerView, QuizQuestion } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

export function tutorLink(prompt: string): string {
  return `/app/tutor?ask=${encodeURIComponent(prompt)}`;
}

/** Result of one graded answer: verdict, correct answer, feedback and prerequisite actions. */
export function FeedbackPanel({
  question,
  answer,
  prereqName,
}: {
  question: QuizQuestion;
  answer: AnswerView;
  prereqName?: string;
}) {
  const pending = answer.pending;
  prereqName = prereqName ?? answer.diagnoses_prereq_name ?? undefined;
  const score = answer.score ?? 0;
  const verdict = pending
    ? { icon: Clock, label: "Grading pending", tone: "text-warning" }
    : answer.is_correct
      ? { icon: CheckCircle2, label: "Correct", tone: "text-success" }
      : score > 0
        ? {
            icon: CheckCircle2,
            label: `Partly correct (${Math.round(score * 100)}%)`,
            tone: "text-warning",
          }
        : { icon: XCircle, label: "Not quite", tone: "text-danger" };
  const Icon = verdict.icon;
  const showCorrect =
    !pending &&
    !answer.is_correct &&
    answer.correct_answer !== undefined &&
    answer.correct_answer !== null;
  return (
    <div
      role="status"
      className={cn(
        "space-y-3 rounded-xl border p-4",
        pending
          ? "border-warning/40 bg-warning/5"
          : answer.is_correct
            ? "border-success/40 bg-success/5"
            : "border-danger/40 bg-danger/5",
      )}
    >
      <p className={cn("flex items-center gap-2 text-sm font-semibold", verdict.tone)}>
        <Icon aria-hidden className="size-4" />
        {verdict.label}
      </p>
      {showCorrect && (
        <p className="text-sm text-text">
          <span className="text-muted">
            {question.type === "short_answer" ? "A model answer: " : "Correct answer: "}
          </span>
          {describeAnswer(question, answer.correct_answer)}
        </p>
      )}
      {answer.missing_points && answer.missing_points.length > 0 && (
        <p className="text-sm text-muted">Missing: {answer.missing_points.join("; ")}</p>
      )}
      {answer.feedback && <Markdown text={answer.feedback} />}
      {answer.diagnoses_prereq && (
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/app/learn/${answer.diagnoses_prereq}`}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs outline-none hover:border-accent focus-visible:ring-2 focus-visible:ring-ring"
          >
            <BookOpen aria-hidden className="size-3.5 text-accent" />
            Learn {prereqName ?? answer.diagnoses_prereq.replace(/_/g, " ")}
          </Link>
          <Link
            href={tutorLink(
              `Can you explain ${prereqName ?? answer.diagnoses_prereq.replace(/_/g, " ")}? I got a quiz question wrong: ${question.prompt.slice(0, 200)}`,
            )}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs outline-none hover:border-accent focus-visible:ring-2 focus-visible:ring-ring"
          >
            <MessageSquare aria-hidden className="size-3.5 text-accent" />
            Ask the tutor about it
          </Link>
        </div>
      )}
    </div>
  );
}
