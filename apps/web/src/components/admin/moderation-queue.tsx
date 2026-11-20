"use client";

import { Flag, ShieldCheck, ThumbsDown, ThumbsUp, Wrench } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { fieldClass } from "@/components/admin/form-bits";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Markdown } from "@/components/tutor/markdown";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useFeedbackByConcept, useModerationActions, useReports, type Report } from "@/lib/admin";
import { ApiError } from "@/lib/api";
import type { RetrievalTrace } from "@/lib/tutor/types";
import { cn } from "@/lib/utils";

const STATUSES: Report["status"][] = ["open", "reviewing", "resolved", "dismissed"];

const REASON_LABEL: Record<string, string> = {
  incorrect: "Incorrect",
  off_topic: "Off topic",
  harmful: "Harmful",
  incomplete: "Incomplete",
  other: "Other",
};

function contentLink(conceptId: string, chunkId?: string): string {
  const q = new URLSearchParams({ concept: conceptId });
  if (chunkId) q.set("chunk", chunkId);
  return `/admin/content?${q}`;
}

function TraceSummary({ trace }: { trace: Partial<RetrievalTrace> }) {
  const chunks = trace.chunks ?? [];
  return (
    <details className="rounded-lg border border-border bg-bg p-3 text-sm">
      <summary className="cursor-pointer font-medium">
        Retrieval trace{trace.mode ? ` · ${trace.mode}` : ""}
        {trace.classification_path ? ` · classified by ${trace.classification_path}` : ""}
        {trace.cached ? " · served from cache" : ""}
      </summary>
      <div className="mt-3 space-y-3">
        {(trace.concepts ?? []).length > 0 && (
          <div>
            <p className="text-xs font-semibold text-muted uppercase">Concepts walked</p>
            <ul className="mt-1 flex flex-wrap gap-1.5">
              {(trace.concepts ?? []).map((c) => (
                <li key={c.id}>
                  <Badge
                    variant="outline"
                    className={cn(c.role === "matched" && "border-accent text-accent")}
                  >
                    {c.name} · {c.role}
                    {c.weak ? " · weak" : ""}
                  </Badge>
                </li>
              ))}
            </ul>
          </div>
        )}
        {chunks.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-muted uppercase">
              Context chunks ({trace.used_tokens ?? "?"} / {trace.budget_tokens ?? "?"} tokens)
            </p>
            <ul className="mt-1 space-y-1">
              {chunks.map((k) => (
                <li key={k.id} className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs">[{k.id}]</span>
                  <Link
                    href={contentLink(k.concept_id, k.id)}
                    className="text-xs text-accent underline-offset-4 hover:underline"
                  >
                    Open chunk
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
        {(trace.controller ?? []).length > 0 && (
          <div>
            <p className="text-xs font-semibold text-muted uppercase">Agentic steps</p>
            <ol className="mt-1 list-decimal space-y-0.5 pl-5 text-xs">
              {(trace.controller ?? []).map((s, i) => (
                <li key={i}>
                  {s.action}: {s.reason}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </details>
  );
}

function ReportCard({ report }: { report: Report }) {
  const { act, invalidate } = useModerationActions();
  const [note, setNote] = useState(report.resolution_note ?? "");
  const m = report.message;
  const trace = (m.trace ?? {}) as Partial<RetrievalTrace>;
  const firstChunk = trace.chunks?.[0];
  const matched = m.concepts.find((c) => c.role === "matched") ?? m.concepts[0];
  const busy = act.isPending || invalidate.isPending;
  const closed = report.status === "resolved" || report.status === "dismissed";

  const run = (status: "reviewing" | "resolved" | "dismissed", ok: string) =>
    act.mutate(
      { id: report.id, status, note },
      {
        onSuccess: () => toast.success(ok),
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Update failed."),
      },
    );

  return (
    <article className="space-y-4 rounded-2xl border border-border bg-surface p-5">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-danger text-danger">
              <Flag aria-hidden /> {REASON_LABEL[report.reason] ?? report.reason}
            </Badge>
            <Badge variant="outline">{report.status}</Badge>
            {m.mode && <Badge variant="outline">{m.mode}</Badge>}
          </div>
          <p className="text-xs text-muted">
            Reported {new Date(report.reported_at).toLocaleString()}
            {report.reporter ? ` by ${report.reporter}` : ""}
          </p>
        </div>
      </header>

      {report.comment && (
        <blockquote className="border-l-2 border-warning pl-3 text-sm">
          <span className="text-xs text-muted">Student&apos;s comment: </span>
          {report.comment}
        </blockquote>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-muted uppercase">Question</p>
          <p className="rounded-lg border border-border bg-bg p-3 text-sm whitespace-pre-wrap">
            {m.question ?? "(question not available)"}
          </p>
        </div>
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-muted uppercase">Answer</p>
          <div className="max-h-80 overflow-y-auto rounded-lg border border-border bg-bg p-3 text-sm">
            <Markdown
              text={m.content}
              conceptNames={Object.fromEntries(m.concepts.map((c) => [c.id, c.name]))}
            />
          </div>
        </div>
      </div>

      {m.trace && <TraceSummary trace={trace} />}

      <div className="space-y-3 border-t border-border pt-4">
        <label htmlFor={`note-${report.id}`} className="block text-sm font-medium">
          Resolution note
        </label>
        <textarea
          id={`note-${report.id}`}
          className={cn(fieldClass, "min-h-16")}
          maxLength={2000}
          value={note}
          placeholder="What was wrong and what you did about it"
          onChange={(e) => setNote(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {!closed && report.status !== "reviewing" && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => run("reviewing", "Marked as in review.")}
            >
              Start review
            </Button>
          )}
          <Button size="sm" disabled={busy} onClick={() => run("resolved", "Report resolved.")}>
            <ShieldCheck aria-hidden className="size-4" /> Resolve
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => run("dismissed", "Report dismissed.")}
          >
            Dismiss
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() =>
              invalidate.mutate(report.id, {
                onSuccess: (r) =>
                  toast.success(
                    r.had_cache_key
                      ? `Cache cleared (${r.removed} entr${r.removed === 1 ? "y" : "ies"}).`
                      : "This answer was not cached; nothing to clear.",
                  ),
                onError: (e) =>
                  toast.error(e instanceof ApiError ? e.message : "Could not clear the cache."),
              })
            }
          >
            Invalidate cache
          </Button>
          {matched && (
            <Link
              href={contentLink(
                matched.id,
                firstChunk?.concept_id === matched.id ? firstChunk.id : undefined,
              )}
              className={buttonVariants({ size: "sm", variant: "outline" })}
            >
              <Wrench aria-hidden className="size-4" /> Fix content: {matched.name}
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}

function FeedbackTable() {
  const { data, isPending, error, refetch } = useFeedbackByConcept();
  if (isPending) return <Skeleton className="h-40 w-full" aria-label="Loading feedback" />;
  if (error) return <ErrorState message={error.message} onRetry={() => void refetch()} />;
  if (data.items.length === 0)
    return (
      <p className="rounded-xl border border-dashed border-border p-4 text-sm text-muted">
        No ratings in the last 30 days.
      </p>
    );
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full min-w-[28rem] text-left text-sm">
        <caption className="sr-only">Ratings by matched concept, last 30 days</caption>
        <thead className="text-xs text-muted uppercase">
          <tr>
            <th className="px-3 py-2 font-medium">Concept</th>
            <th className="px-3 py-2 font-medium">
              <ThumbsDown aria-label="Thumbs down" className="size-4" />
            </th>
            <th className="px-3 py-2 font-medium">
              <ThumbsUp aria-label="Thumbs up" className="size-4" />
            </th>
            <th className="px-3 py-2 font-medium">Reports</th>
            <th className="px-3 py-2" />
          </tr>
        </thead>
        <tbody>
          {data.items.slice(0, 15).map((r) => (
            <tr key={r.concept_id} className="border-t border-border">
              <td className="px-3 py-2">{r.name}</td>
              <td className={cn("px-3 py-2", r.thumbs_down > 0 && "font-semibold text-danger")}>
                {r.thumbs_down}
              </td>
              <td className="px-3 py-2">{r.thumbs_up}</td>
              <td className="px-3 py-2">{r.reports}</td>
              <td className="px-3 py-2 text-right">
                <Link
                  href={contentLink(r.concept_id)}
                  className="text-xs text-accent underline-offset-4 hover:underline"
                >
                  Content
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ModerationQueue() {
  const [status, setStatus] = useState<Report["status"]>("open");
  const { data, isPending, error, refetch } = useReports(status);
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reviewer"
        title="Moderation"
        description="Answers students reported. Reported answers are the only chat content reviewers can read (privacy policy)."
      />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="min-w-0 space-y-4" aria-label="Reports">
          <Tabs value={status} onValueChange={(v) => setStatus(v as Report["status"])}>
            <TabsList>
              {STATUSES.map((s) => (
                <TabsTrigger key={s} value={s} className="capitalize">
                  {s}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          {isPending ? (
            <Skeleton className="h-64 w-full" aria-label="Loading reports" />
          ) : error ? (
            <ErrorState
              message={error.message}
              requestId={error instanceof ApiError ? error.requestId : undefined}
              onRetry={() => void refetch()}
            />
          ) : data.items.length === 0 ? (
            <EmptyState
              icon={<ShieldCheck />}
              title={status === "open" ? "No open reports" : `No ${status} reports`}
              description={
                status === "open"
                  ? "When a student reports an answer it appears here with the trace behind it."
                  : "Nothing here yet."
              }
            />
          ) : (
            <>
              <p className="text-sm text-muted">
                {data.total} report{data.total === 1 ? "" : "s"}
              </p>
              {data.items.map((r) => (
                <ReportCard key={`${r.id}-${r.status}`} report={r} />
              ))}
            </>
          )}
        </section>
        <aside className="space-y-3" aria-label="Ratings by concept">
          <h2 className="font-semibold">Ratings by concept (30 days)</h2>
          <p className="text-sm text-muted">
            Concepts whose answers students rate down most. Many thumbs-down usually means the notes
            for that concept need work.
          </p>
          <FeedbackTable />
        </aside>
      </div>
    </div>
  );
}
