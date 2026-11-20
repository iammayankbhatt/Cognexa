"use client";

import { CalendarCheck, CalendarClock, Flame } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { NextStepCard } from "@/components/recommend/next-step-card";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useCreateQuiz } from "@/lib/quiz/use-quiz";
import { useReviewDue } from "@/lib/recommend";

function relativeDay(iso: string, now = new Date()): string {
  const days = Math.round((new Date(iso).getTime() - now.getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days} days`;
}

/** Spaced review: due concepts, a review quiz, the streak. Works without AI. */
export function ReviewPage() {
  const router = useRouter();
  const { data, isPending, error, refetch } = useReviewDue();
  const create = useCreateQuiz();

  const start = async () => {
    try {
      const s = await create.mutateAsync({ mode: "review", count: 8 });
      router.push(`/app/quizzes/${s.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start the review.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Review"
        description="Short quizzes on what you are about to forget. Spacing grows 1 → 3 → 7 → 14 → 30 days as you get them right. No AI needed."
      />
      {isPending ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : error || !data ? (
        <ErrorState message={error?.message} onRetry={() => void refetch()} />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard label="Due now" value={data.due.length} icon={<CalendarClock />} />
            <StatCard
              label="Streak"
              value={`${data.streak_days} day${data.streak_days === 1 ? "" : "s"}`}
              hint="Days in a row with practice"
              icon={<Flame />}
            />
            <StatCard
              label="Next review"
              value={data.next_due_at ? relativeDay(data.next_due_at) : "—"}
              hint={`${data.scheduled} concept(s) scheduled`}
              icon={<CalendarCheck />}
            />
          </div>
          {data.due.length === 0 ? (
            <EmptyState
              icon={<CalendarCheck />}
              title="Nothing is due"
              description={
                data.scheduled
                  ? "You are up to date. Come back when the next review is due."
                  : "Reviews are scheduled automatically after you take quizzes."
              }
              action={
                <Link href="/app/quizzes" className="text-sm text-accent underline">
                  Take a quiz
                </Link>
              }
            />
          ) : (
            <section className="space-y-3 rounded-2xl border border-border bg-surface p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-semibold">Due for review</h2>
                <Button onClick={() => void start()} disabled={create.isPending}>
                  Start review quiz
                </Button>
              </div>
              <ul className="divide-y divide-border">
                {data.due.map((d) => (
                  <li key={d.concept_id} className="flex flex-wrap items-center gap-3 py-2">
                    <Link
                      href={`/app/learn/${d.concept_id}`}
                      className="font-medium text-text hover:underline"
                    >
                      {d.name}
                    </Link>
                    <MasteryBadge value={d.effective} />
                    <span className="ml-auto text-xs text-muted">
                      {d.question_ids.length} questions ready
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <NextStepCard surface="review" />
        </>
      )}
    </div>
  );
}
