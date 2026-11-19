"use client";

import { useQuery } from "@tanstack/react-query";

import { UsageChart } from "@/components/app/usage-chart";
import { ErrorState } from "@/components/shared/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError, type UsageSummary } from "@/lib/api";
import { formatClock } from "@/lib/errors";
import { fillDays } from "@/lib/usage";

export const USAGE_KEY = ["me", "usage"] as const;

/** The student's own AI usage: today against the limits, plus the last 30 days. */
export function UsageCard() {
  const q = useQuery({
    queryKey: USAGE_KEY,
    queryFn: () => api<UsageSummary>("/me/usage"),
  });
  return (
    <section className="space-y-4 rounded-2xl border border-border bg-surface p-5 lg:col-span-2">
      <div>
        <h2 className="text-lg font-semibold text-text">AI usage</h2>
        <p className="text-sm text-muted">
          Each question to the tutor counts as one request, including answers served from the cache.
          Limits reset at midnight UTC.
        </p>
      </div>
      {q.isPending ? (
        <Skeleton className="h-56 w-full" />
      ) : q.isError ? (
        <ErrorState
          message="We couldn't load your usage."
          requestId={q.error instanceof ApiError ? q.error.requestId : undefined}
          onRetry={() => void q.refetch()}
        />
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Used today", `${q.data.today.ai_requests} / ${q.data.limits.daily_ai_requests}`],
              ["Remaining", String(q.data.today.remaining)],
              ["Resets at", formatClock(q.data.today.resets_at)],
              ["Per minute", `${q.data.limits.per_minute} max`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl border border-border bg-surface-2 px-3 py-2">
                <dt className="text-xs text-muted">{label}</dt>
                <dd className="text-lg font-semibold text-text tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
          <UsageChart days={fillDays(q.data.history, 30)} label="Last 30 days" />
        </>
      )}
    </section>
  );
}
