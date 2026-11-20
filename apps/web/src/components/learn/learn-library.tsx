"use client";

import { useQuery } from "@tanstack/react-query";
import { Lock, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { clusterLabel } from "@/components/quiz/quiz-home";
import { ErrorState } from "@/components/shared/error-state";
import { MASTERY_LOW_MAX } from "@/components/shared/mastery";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { GEdge, GNode } from "@/lib/graph-layout";
import { useMastery } from "@/lib/quiz/use-quiz";

interface GraphData {
  subject_id: string;
  nodes: (GNode & { order_index?: number })[];
  edges: GEdge[];
}

/** Prerequisites of a concept that the student has not yet reached "developing" on. */
export function lockHints(
  conceptId: string,
  edges: GEdge[],
  mastery: Map<string, number>,
  names: Map<string, string>,
): string[] {
  return edges
    .filter((e) => e.type === "PREREQUISITE_OF" && e.target === conceptId)
    .filter((e) => (mastery.get(e.source) ?? -1) < MASTERY_LOW_MAX)
    .map((e) => names.get(e.source) ?? e.source);
}

/** Concept library grouped by cluster, in syllabus order, with mastery and lock hints. */
export function LearnLibrary() {
  const router = useRouter();
  const params = useSearchParams();
  const legacy = params.get("concept");
  useEffect(() => {
    // Old links used /app/learn?concept=<id>.
    if (legacy && /^[a-z][a-z0-9_]*$/.test(legacy)) router.replace(`/app/learn/${legacy}`);
  }, [legacy, router]);
  const [q, setQ] = useState("");
  const graph = useQuery({
    queryKey: ["public-graph"],
    queryFn: () => api<GraphData>("/graph", { anonymous: true }),
    staleTime: 5 * 60_000,
  });
  const mastery = useMastery();
  const masteryBy = useMemo(
    () =>
      new Map(
        (mastery.data?.items ?? [])
          .filter((m) => m.attempts > 0)
          .map((m) => [m.concept_id, m.effective]),
      ),
    [mastery.data],
  );

  if (graph.isPending) {
    return (
      <div className="space-y-4" aria-label="Loading concepts">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (graph.error || !graph.data) {
    return <ErrorState message={graph.error?.message} onRetry={() => void graph.refetch()} />;
  }
  const names = new Map(graph.data.nodes.map((n) => [n.id, n.name]));
  const term = q.trim().toLowerCase();
  const nodes = graph.data.nodes.filter((n) => !term || n.name.toLowerCase().includes(term));
  const clusters = [...new Set(graph.data.nodes.map((n) => n.cluster))];
  const practised = masteryBy.size;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Learn"
        description={`${graph.data.nodes.length} concepts in syllabus order. You have practised ${practised}.`}
      />
      <div className="relative max-w-sm">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted"
        />
        <label htmlFor="learn-search" className="sr-only">
          Search concepts
        </label>
        <input
          id="learn-search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search concepts"
          className="h-9 w-full rounded-lg border border-border bg-surface pr-3 pl-9 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      {clusters.map((cluster) => {
        const items = nodes.filter((n) => n.cluster === cluster);
        if (!items.length) return null;
        return (
          <section key={cluster} className="space-y-3" aria-labelledby={`cluster-${cluster}`}>
            <h2
              id={`cluster-${cluster}`}
              className="text-sm font-semibold tracking-wide text-muted uppercase"
            >
              {clusterLabel(cluster)}
            </h2>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((n) => {
                const m = masteryBy.get(n.id);
                const hints = lockHints(n.id, graph.data.edges, masteryBy, names);
                return (
                  <li key={n.id}>
                    <Link
                      href={`/app/learn/${n.id}`}
                      className="flex h-full flex-col gap-2 rounded-xl border border-border bg-surface p-4 transition-colors duration-150 outline-none hover:border-accent focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-medium text-text">{n.name}</span>
                        <span
                          className="flex shrink-0 gap-0.5"
                          aria-label={`Difficulty ${n.difficulty} of 5`}
                        >
                          {[1, 2, 3, 4, 5].map((d) => (
                            <span
                              key={d}
                              aria-hidden
                              className={
                                d <= n.difficulty
                                  ? "size-1.5 rounded-full bg-accent"
                                  : "size-1.5 rounded-full bg-surface-2"
                              }
                            />
                          ))}
                        </span>
                      </div>
                      {m !== undefined ? (
                        <MasteryBadge value={m} className="self-start" />
                      ) : (
                        <span className="self-start rounded-full border border-border px-2 py-0.5 text-xs text-muted">
                          Not started
                        </span>
                      )}
                      {hints.length > 0 && (
                        <span className="mt-auto flex items-start gap-1 text-xs text-muted">
                          <Lock aria-hidden className="mt-0.5 size-3 shrink-0" />
                          Recommended after: {hints.slice(0, 2).join(", ")}
                          {hints.length > 2 ? ` +${hints.length - 2}` : ""}
                        </span>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
      {nodes.length === 0 && <p className="text-sm text-muted">No concepts match “{q}”.</p>}
    </div>
  );
}
