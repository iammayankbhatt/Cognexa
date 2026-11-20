"use client";

import {
  BookmarkCheck,
  CalendarClock,
  ClipboardCheck,
  Clock,
  Flame,
  MessageSquareText,
  Network,
  Sparkles,
  Target,
  Wrench,
} from "lucide-react";
import Link from "next/link";

import { useMe } from "@/components/app/me-provider";
import { AccuracyTrend, ClusterBars } from "@/components/dashboard/charts";
import { NextStepCard } from "@/components/recommend/next-step-card";
import { StudyBanner } from "@/components/study/study-page";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { timeAgo, useDashboard, type DashboardData } from "@/lib/dashboard";
import { MODE_LABEL } from "@/lib/quiz/use-quiz";
import { cn } from "@/lib/utils";

function Panel({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      aria-label={title}
      className={cn("space-y-3 rounded-2xl border border-border bg-surface p-5", className)}
    >
      <h2 className="text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Activity({ items }: { items: DashboardData["activity"] }) {
  if (!items.length) return <p className="text-sm text-muted">Nothing yet this week.</p>;
  return (
    <ol className="space-y-2.5">
      {items.map((a, i) => {
        const when = timeAgo(a.at);
        if (a.kind === "quiz") {
          const pct = a.max_score ? Math.round((a.score / a.max_score) * 100) : 0;
          return (
            <li key={i} className="flex items-start gap-2 text-sm">
              <ClipboardCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
              <Link href={`/app/quizzes/${a.id}`} className="min-w-0 flex-1 hover:underline">
                {MODE_LABEL[a.mode] ?? a.mode}
                {a.name ? `: ${a.name}` : ""} · {pct}%
              </Link>
              <span className="shrink-0 text-xs text-muted">{when}</span>
            </li>
          );
        }
        if (a.kind === "question") {
          return (
            <li key={i} className="flex items-start gap-2 text-sm">
              <MessageSquareText aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
              <Link
                href={`/app/tutor?thread=${a.thread_id}`}
                className="min-w-0 flex-1 truncate hover:underline"
              >
                {a.text}
              </Link>
              <span className="shrink-0 text-xs text-muted">{when}</span>
            </li>
          );
        }
        return (
          <li key={i} className="flex items-start gap-2 text-sm">
            <BookmarkCheck aria-hidden className="mt-0.5 size-4 shrink-0 text-accent" />
            <Link
              href={`/app/learn/${a.concept_id}`}
              className="min-w-0 flex-1 truncate hover:underline"
            >
              {a.bookmarked ? "Bookmarked" : "Note on"} {a.name}
            </Link>
            <span className="shrink-0 text-xs text-muted">{when}</span>
          </li>
        );
      })}
    </ol>
  );
}

/** Progress dashboard: next best step, numbers, trends, weak spots, activity. */
export default function DashboardPage() {
  const { data: me, isPending: mePending } = useMe();
  const dash = useDashboard();

  if (mePending || dash.isPending) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-4 sm:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (!me) return null;
  const first = (me.display_name ?? "there").split(" ")[0];
  if (dash.error || !dash.data) {
    return (
      <ErrorState
        title="Couldn't load your dashboard"
        message={dash.error?.message}
        onRetry={() => void dash.refetch()}
      />
    );
  }
  const d = dash.data;
  const fresh = d.concepts_practised === 0 && d.quizzes_this_week === 0 && d.activity.length === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Dashboard"
        title={`Welcome, ${first}`}
        description="Your next best step, based on your quizzes and the questions you ask."
        actions={
          <div className="flex gap-2">
            <Link href="/app/graph" className={buttonVariants({ variant: "outline" })}>
              <Network aria-hidden /> Knowledge map
            </Link>
            <Link href="/app/tutor" className={buttonVariants({ variant: "default" })}>
              <MessageSquareText aria-hidden /> Ask the tutor
            </Link>
          </div>
        }
      />

      <StudyBanner />

      {fresh && (
        <EmptyState
          icon={<Target />}
          title="Let's find your starting point"
          description="Take the 10-question diagnostic or a concept quiz. Your mastery map, weak spots and recommendations fill in as you go."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Link href="/app/onboarding" className={buttonVariants({ variant: "default" })}>
                Take the diagnostic
              </Link>
              <Link href="/app/quizzes" className={buttonVariants({ variant: "outline" })}>
                Browse quizzes
              </Link>
            </div>
          }
        />
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <NextStepCard surface="dashboard" />
        <section aria-label="Today" className="grid grid-cols-2 gap-3">
          <StatCard
            label="Overall mastery"
            value={`${Math.round(d.overall_mastery * 100)}%`}
            hint={`${d.concepts_practised}/${d.concepts_total} concepts practised`}
            icon={<Target />}
          />
          <StatCard
            label="Streak"
            value={`${d.streak_days} day${d.streak_days === 1 ? "" : "s"}`}
            hint="Days in a row with practice"
            icon={<Flame />}
          />
          <StatCard
            label="This week"
            value={`${d.quizzes_this_week} quiz${d.quizzes_this_week === 1 ? "" : "zes"}`}
            hint={`${d.tutor_questions_this_week} tutor questions · ~${d.time_on_task_minutes_7d} min`}
            icon={<Clock />}
          />
          <Link
            href="/app/review"
            className="rounded-2xl outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <StatCard
              label="Due for review"
              value={d.review_due}
              hint="Open the review queue"
              icon={<CalendarClock />}
            />
          </Link>
        </section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Accuracy">
          <AccuracyTrend data={d.accuracy_trend} />
        </Panel>
        <Panel title="Clusters">
          <ClusterBars data={d.per_cluster} />
          <p className="text-xs text-muted">
            {d.bands.strong} strong · {d.bands.developing} developing · {d.bands.weak} weak ·{" "}
            {d.bands.not_started} not started
          </p>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Weak spots" className="lg:col-span-2">
          {d.weak_concepts.length === 0 ? (
            <p className="text-sm text-muted">
              No weak spots yet. A concept counts as weak after two shaky quiz attempts or several
              questions about it.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {d.weak_concepts.map((w) => (
                <li key={w.concept_id} className="flex flex-wrap items-center gap-3 py-2.5">
                  <Link href={`/app/learn/${w.concept_id}`} className="font-medium hover:underline">
                    {w.name}
                  </Link>
                  {w.mastery !== null ? (
                    <MasteryBadge value={w.mastery} />
                  ) : (
                    <span className="text-xs text-muted">asked {w.asked} times</span>
                  )}
                  {w.fix && w.fix.concept_id !== w.concept_id ? (
                    <Link
                      href={`/app/learn/${w.fix.concept_id}`}
                      className={cn(buttonVariants({ variant: "outline", size: "sm" }), "ml-auto")}
                    >
                      <Wrench aria-hidden className="size-3.5" /> Fix the root cause: {w.fix.name}
                    </Link>
                  ) : (
                    <Link
                      href={`/app/learn/${w.concept_id}`}
                      className={cn(buttonVariants({ variant: "outline", size: "sm" }), "ml-auto")}
                    >
                      <Wrench aria-hidden className="size-3.5" /> Review {w.name}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Panel>
        <Panel title="Recent activity">
          <Activity items={d.activity} />
        </Panel>
      </div>

      <p className="flex items-center gap-2 text-xs text-muted">
        <Sparkles aria-hidden className="size-3.5" />
        {d.usage_today.ai_requests} of {d.usage_today.daily_quota} AI requests used today. Quizzes
        and review work without AI.
      </p>
    </div>
  );
}
