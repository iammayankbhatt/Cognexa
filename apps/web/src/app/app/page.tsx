"use client";

import { CalendarClock, ClipboardCheck, MessageSquareText, Sparkles } from "lucide-react";
import Link from "next/link";

import { useMe } from "@/components/app/me-provider";
import { NextStepCard } from "@/components/recommend/next-step-card";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMastery, useQuizHistory } from "@/lib/quiz/use-quiz";
import { useReviewDue } from "@/lib/recommend";
import { cn } from "@/lib/utils";

/** Dashboard: next best step and the first progress numbers (Phase 10 builds the full page). */
export default function DashboardPage() {
  const { data: me, isPending } = useMe();
  const mastery = useMastery();
  const history = useQuizHistory();
  const review = useReviewDue();

  if (isPending) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      </div>
    );
  }
  if (!me) return null;
  const first = (me.display_name ?? "there").split(" ")[0];
  const practised = (mastery.data?.items ?? []).filter((m) => m.attempts > 0);
  const strong = practised.filter((m) => m.band === "strong").length;
  const quizzes = history.data?.total ?? 0;
  const due = review.data?.due.length ?? 0;
  const loading = mastery.isPending || history.isPending || review.isPending;
  const fresh = !loading && practised.length === 0 && quizzes === 0;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dashboard"
        title={`Welcome, ${first}`}
        description="Your next best step, based on your quizzes and the questions you ask."
        actions={
          <Link href="/app/tutor" className={cn(buttonVariants({ variant: "default" }))}>
            <MessageSquareText aria-hidden /> Ask the tutor
          </Link>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <NextStepCard surface="dashboard" />
        <section aria-label="Today" className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
          <StatCard
            label="AI requests today"
            value={`${me.usage.ai_requests}/${me.usage.daily_quota}`}
            hint="Resets at midnight UTC"
            icon={<Sparkles />}
          />
          <StatCard
            label="Concepts practised"
            value={loading ? "…" : practised.length}
            hint={loading ? undefined : `${strong} strong · ${quizzes} quizzes taken`}
            icon={<ClipboardCheck />}
          />
          <Link
            href="/app/review"
            className="rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <StatCard
              label="Due for review"
              value={loading ? "…" : due}
              hint={
                review.data?.streak_days
                  ? `${review.data.streak_days}-day streak`
                  : "Reviews are scheduled after quizzes"
              }
              icon={<CalendarClock />}
            />
          </Link>
        </section>
      </div>
      {fresh && (
        <EmptyState
          icon={<ClipboardCheck />}
          title="Start with a quiz or a question"
          description="Take the diagnostic or a concept quiz, or ask the tutor. Your recommendations get sharper with every answer."
          action={
            <Link href="/app/quizzes" className={buttonVariants({ variant: "outline" })}>
              Go to quizzes
            </Link>
          }
        />
      )}
    </div>
  );
}
