"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CircleCheck, CircleX, Download, Loader2, Zap } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { ME_KEY } from "@/components/app/me-provider";
import { USAGE_KEY } from "@/components/app/usage-card";
import { UsageChart } from "@/components/app/usage-chart";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { saveBlob } from "@/lib/admin";
import { api, apiBlob, ApiError, type UsageDay } from "@/lib/api";
import { friendlyError } from "@/lib/errors";
import { fillDays, formatUsd } from "@/lib/usage";
import { cn } from "@/lib/utils";

interface ProviderStatus {
  provider: string;
  model: string;
  circuit_open: boolean;
  consecutive_failures: number;
}
interface AdminUsage {
  days: number;
  totals: {
    ai_requests: number;
    tokens: number;
    est_cost_usd: number;
    calls: number;
    cache_hit_rate: number;
    fallback_rate: number;
  };
  by_day: UsageDay[];
  by_user: {
    user_id: string;
    email: string | null;
    ai_requests: number;
    tokens: number;
    est_cost_usd: number;
  }[];
  by_model: {
    provider: string;
    model: string;
    calls: number;
    tokens_in: number;
    tokens_out: number;
    est_cost_usd: number;
    avg_latency_ms: number;
    cached: number;
    fallback: number;
  }[];
  cache: Record<string, { entries: number; hits: number }>;
  providers: ProviderStatus[];
}
interface CheckResult {
  provider: string;
  model: string;
  latency_ms: number;
  fallback_used: boolean;
  text: string;
  providers: ProviderStatus[];
}

const RANGES = [7, 30, 90] as const;
const pct = (v: number) => `${Math.round(v * 100)}%`;

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-2xl font-semibold text-text tabular-nums">{value}</p>
      {hint && <p className="text-xs text-muted">{hint}</p>}
    </div>
  );
}

function Providers({ providers }: { providers: ProviderStatus[] }) {
  const qc = useQueryClient();
  const check = useMutation({
    mutationFn: () => api<CheckResult>("/admin/llm/check", { method: "POST", body: {} }),
    onSuccess: (r) => {
      toast.success(`${r.provider} / ${r.model} answered in ${r.latency_ms} ms`, {
        description: r.fallback_used ? "The primary failed; the fallback answered." : r.text,
      });
      // The call used one of the admin's own requests: refresh the top-bar meter too (BUG-021).
      void qc.invalidateQueries({ queryKey: ["admin", "usage"] });
      void qc.invalidateQueries({ queryKey: ME_KEY });
      void qc.invalidateQueries({ queryKey: USAGE_KEY });
    },
    onError: (e) => {
      const f = friendlyError(e);
      toast.error(f.title, { description: f.description });
    },
  });
  return (
    <section className="space-y-3 rounded-2xl border border-border bg-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-text">Providers</h2>
        <Button size="sm" onClick={() => check.mutate()} disabled={check.isPending}>
          {check.isPending ? <Loader2 className="animate-spin" aria-hidden /> : <Zap aria-hidden />}
          Run live check
        </Button>
      </div>
      <p className="text-sm text-muted">
        Primary first, then fallback. A provider is skipped for 60 s after repeated failures. The
        check sends one tiny prompt and counts against your quota.
      </p>
      <ul className="divide-y divide-border">
        {providers.map((p, i) => (
          <li key={`${p.provider}:${p.model}`} className="flex items-center gap-3 py-2 text-sm">
            {p.circuit_open ? (
              <CircleX aria-hidden className="size-4 text-danger" />
            ) : (
              <CircleCheck aria-hidden className="size-4 text-success" />
            )}
            <span className="text-text">
              {i === 0 ? "Primary" : "Fallback"}: <span className="font-mono">{p.provider}</span>{" "}
              <span className="font-mono text-muted">{p.model}</span>
            </span>
            <span className={cn("ml-auto text-xs", p.circuit_open ? "text-danger" : "text-muted")}>
              {p.circuit_open
                ? "Skipped (circuit open)"
                : p.consecutive_failures
                  ? `${p.consecutive_failures} recent failure(s)`
                  : "Healthy"}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Table({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface-2 text-xs text-muted">
          <tr>
            {head.map((h, i) => (
              <th key={h} className={cn("px-3 py-2 font-medium", i > 0 && "text-right")}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={String(r[0])} className="border-t border-border text-text">
              {r.map((c, i) => (
                <td key={i} className={cn("px-3 py-2", i > 0 && "text-right tabular-nums")}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function UsageDashboard() {
  const [days, setDays] = useState<(typeof RANGES)[number]>(30);
  const q = useQuery({
    queryKey: ["admin", "usage", days],
    queryFn: () => api<AdminUsage>(`/admin/usage?days=${days}`),
  });
  return (
    <div className="space-y-6">
      <PageHeader
        title="AI usage"
        description="Requests, tokens and notional cost (free tiers cost nothing; this shows what it would cost at scale)."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              onClick={() =>
                void apiBlob(`/admin/usage/export.csv?days=${days}`)
                  .then((b) => saveBlob(b, `cognexa-usage-${days}d.csv`))
                  .catch((e: unknown) =>
                    toast.error(e instanceof ApiError ? e.message : "Export failed."),
                  )
              }
            >
              <Download aria-hidden className="size-4" /> Export CSV
            </Button>
            <div
              role="radiogroup"
              aria-label="Time range"
              className="flex rounded-lg border border-border p-0.5"
            >
              {RANGES.map((r) => (
                <button
                  key={r}
                  type="button"
                  role="radio"
                  aria-checked={days === r}
                  onClick={() => setDays(r)}
                  className={cn(
                    "rounded-md px-3 py-1 text-sm transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                    days === r ? "bg-primary text-primary-fg" : "text-muted hover:text-text",
                  )}
                >
                  {r} days
                </button>
              ))}
            </div>
          </div>
        }
      />
      {q.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
          <Skeleton className="h-56 sm:col-span-2 lg:col-span-5" />
        </div>
      ) : q.isError ? (
        <ErrorState
          message="We couldn't load usage."
          requestId={q.error instanceof ApiError ? q.error.requestId : undefined}
          onRetry={() => void q.refetch()}
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="AI requests" value={q.data.totals.ai_requests.toLocaleString()} />
            <Stat label="Tokens" value={q.data.totals.tokens.toLocaleString()} />
            <Stat label="Notional cost" value={formatUsd(q.data.totals.est_cost_usd)} />
            <Stat
              label="Cache hit rate"
              value={pct(q.data.totals.cache_hit_rate)}
              hint={`${q.data.totals.calls} logged calls`}
            />
            <Stat label="Fallback rate" value={pct(q.data.totals.fallback_rate)} />
          </div>
          <section className="rounded-2xl border border-border bg-surface p-5">
            <h2 className="mb-3 text-lg font-semibold text-text">Requests per day</h2>
            <UsageChart days={fillDays(q.data.by_day, days)} label={`Last ${days} days`} />
          </section>
          <Providers providers={q.data.providers} />
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-text">By provider and model</h2>
            {q.data.by_model.length === 0 ? (
              <EmptyState
                icon={<Activity aria-hidden />}
                title="No AI calls yet"
                description="Calls appear here once students use the tutor (or you run a live check)."
              />
            ) : (
              <Table
                head={[
                  "Provider / model",
                  "Calls",
                  "Cached",
                  "Fallback",
                  "Tokens",
                  "Avg latency",
                  "Cost",
                ]}
                rows={q.data.by_model.map((m) => [
                  `${m.provider} / ${m.model}`,
                  m.calls,
                  m.cached,
                  m.fallback,
                  (m.tokens_in + m.tokens_out).toLocaleString(),
                  `${m.avg_latency_ms} ms`,
                  formatUsd(m.est_cost_usd),
                ])}
              />
            )}
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-text">Top users</h2>
            {q.data.by_user.length === 0 ? (
              <EmptyState icon={<Activity aria-hidden />} title="No usage in this period" />
            ) : (
              <Table
                head={["User", "Requests", "Tokens", "Cost"]}
                rows={q.data.by_user.map((u) => [
                  u.email ?? u.user_id,
                  u.ai_requests,
                  u.tokens.toLocaleString(),
                  formatUsd(u.est_cost_usd),
                ])}
              />
            )}
          </section>
        </>
      )}
    </div>
  );
}
