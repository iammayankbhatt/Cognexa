"use client";

import {
  Activity,
  Coins,
  Database,
  Flag,
  FlaskConical,
  Gauge,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";

import { useMe } from "@/components/app/me-provider";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useOverview, useProposalStats } from "@/lib/admin";
import { cn } from "@/lib/utils";

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${Math.round(v * 100)}%`;
}

/** Admin landing page: health of the product at a glance, with links to each queue. */
export function AdminOverview() {
  const { data, isPending, error, refetch } = useOverview();
  const stats = useProposalStats();
  const { data: me } = useMe();
  if (isPending) {
    return (
      <div className="space-y-6" aria-label="Loading overview">
        <Skeleton className="h-16 w-1/2" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }, (_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }
  if (error || !data) return <ErrorState message={error?.message} onRetry={() => void refetch()} />;
  const capShare = data.global_cap ? Math.min(1, data.ai_requests_today / data.global_cap) : 0;
  const accept = stats.data?.total;
  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Admin"
        title="Overview"
        description="Usage, queues and system health. Reviewers curate the graph and content; admins also manage people and AI settings."
      />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Users" value={data.users} icon={<Users />} />
        <StatCard
          label="Active today / this week"
          value={`${data.dau} / ${data.wau}`}
          hint="Asked the tutor or started a quiz"
          icon={<Activity />}
        />
        <div className="flex flex-col gap-2 rounded-xl border border-border bg-surface p-5">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-muted">AI requests today</p>
            <Gauge aria-hidden className="size-4 text-accent" />
          </div>
          <p className="text-3xl font-semibold tracking-tight tabular-nums">
            {data.ai_requests_today}
            <span className="text-base font-normal text-muted"> / {data.global_cap}</span>
          </p>
          <div
            className="h-2 overflow-hidden rounded-full bg-surface-2"
            role="meter"
            aria-label="Share of the global daily cap used"
            aria-valuemin={0}
            aria-valuemax={data.global_cap}
            aria-valuenow={data.ai_requests_today}
          >
            <div
              className={cn(
                "h-full rounded-full transition-[width] duration-200",
                capShare > 0.9 ? "bg-danger" : capShare > 0.7 ? "bg-warning" : "bg-accent",
              )}
              style={{ width: `${capShare * 100}%` }}
            />
          </div>
        </div>
        <StatCard
          label="Cache hit rate today"
          value={pct(data.cache_hit_rate_today)}
          hint={`Est. cost today $${data.est_cost_today_usd.toFixed(4)}`}
          icon={<Database />}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <QueueCard
          href="/admin/moderation"
          icon={<Flag />}
          title="Reported answers"
          count={data.open_reports}
          empty="No open reports."
          action="Open moderation"
        />
        <QueueCard
          href="/admin/proposals"
          icon={<Sparkles />}
          title="Pending proposals"
          count={data.pending_proposals}
          empty="Nothing waiting for review."
          action="Review proposals"
          footer={
            accept && accept.approved + accept.rejected > 0
              ? `LLM proposals accepted after review: ${pct(accept.acceptance_rate)} (${accept.approved} of ${accept.approved + accept.rejected})`
              : undefined
          }
        />
        <QueueCard
          href="/admin/evaluation"
          icon={<FlaskConical />}
          title="Last evaluation run"
          count={null}
          empty={
            data.last_eval_run
              ? `${data.last_eval_run.name}${data.last_eval_run.finished_at ? `, ${new Date(data.last_eval_run.finished_at).toLocaleDateString()}` : " (running)"}`
              : "No evaluation run yet."
          }
          action="Open evaluation"
        />
      </div>
      {me?.role === "admin" && (
        <p className="flex items-center gap-2 text-sm text-muted">
          <Coins aria-hidden className="size-4" /> Costs are notional (free tiers); see{" "}
          <Link href="/admin/usage" className="text-accent underline-offset-4 hover:underline">
            AI usage
          </Link>{" "}
          for the breakdown and CSV export.
        </p>
      )}
    </div>
  );
}

function QueueCard({
  href,
  icon,
  title,
  count,
  empty,
  action,
  footer,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  count: number | null;
  empty: string;
  action: string;
  footer?: string;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-5">
      <div className="flex items-center gap-2">
        <span aria-hidden className="text-accent [&_svg]:size-4">
          {icon}
        </span>
        <h2 className="text-sm font-semibold">{title}</h2>
      </div>
      {count === null ? (
        <p className="text-sm text-muted">{empty}</p>
      ) : count > 0 ? (
        <p className="text-3xl font-semibold tabular-nums">{count}</p>
      ) : (
        <p className="text-sm text-muted">{empty}</p>
      )}
      {footer && <p className="text-xs text-muted">{footer}</p>}
      <Link
        href={href}
        className={cn(buttonVariants({ variant: "outline", size: "sm" }), "mt-auto self-start")}
      >
        {action}
      </Link>
    </section>
  );
}
