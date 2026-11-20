"use client";

import { useQuery } from "@tanstack/react-query";
import { BookOpenCheck, CalendarClock, ListChecks, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { masteryLevel } from "@/components/shared/mastery";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { MODE_LABEL, useCreateQuiz, useMastery, useQuizHistory } from "@/lib/quiz/use-quiz";
import type { CreateQuizBody, FeedbackMode } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

interface ConceptLite {
  id: string;
  name: string;
  cluster: string;
  difficulty: number;
  order_index: number;
}

const CLUSTER_LABEL: Record<string, string> = {
  foundations: "Foundations",
  complexity: "Complexity",
  linear: "Linear structures",
  searching_hashing: "Searching & hashing",
  sorting: "Sorting",
  trees: "Trees",
  graphs: "Graphs",
  paradigms: "Paradigms",
};

export function clusterLabel(c: string): string {
  return CLUSTER_LABEL[c] ?? c.replace(/_/g, " ");
}

function Card({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-5">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-accent [&_svg]:size-5"
        >
          {icon}
        </span>
        <h2 className="text-base font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

export function QuizHome() {
  const router = useRouter();
  const create = useCreateQuiz();
  const mastery = useMastery();
  const history = useQuizHistory();
  const concepts = useQuery({
    queryKey: ["concepts"],
    queryFn: () => api<ConceptLite[]>("/concepts"),
    staleTime: 5 * 60_000,
  });
  const [q, setQ] = useState("");
  const [cluster, setCluster] = useState("all");
  const [conceptId, setConceptId] = useState<string | null>(null);
  const [count, setCount] = useState(8);
  const [feedback, setFeedback] = useState<FeedbackMode>("immediate");
  const [timed, setTimed] = useState(false);

  const masteryBy = useMemo(
    () =>
      new Map(
        (mastery.data?.items ?? []).filter((m) => m.attempts > 0).map((m) => [m.concept_id, m]),
      ),
    [mastery.data],
  );
  const due = (mastery.data?.items ?? []).filter(
    (m) => m.next_review_at && new Date(m.next_review_at) <= new Date(),
  ).length;
  const clusters = [...new Set((concepts.data ?? []).map((c) => c.cluster))];
  const filtered = (concepts.data ?? []).filter(
    (c) =>
      (cluster === "all" || c.cluster === cluster) &&
      (!q.trim() || c.name.toLowerCase().includes(q.trim().toLowerCase())),
  );

  const start = async (body: CreateQuizBody) => {
    try {
      const s = await create.mutateAsync(body);
      router.push(`/app/quizzes/${s.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start the quiz.");
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quizzes"
        description="Practise a concept, let Cognexa pick, or review what is due."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card icon={<ListChecks />} title="Concept quiz">
            <div className="flex flex-wrap gap-2">
              <label htmlFor="concept-filter" className="sr-only">
                Search concepts
              </label>
              <input
                id="concept-filter"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search concepts"
                className="h-8 min-w-0 flex-1 rounded-lg border border-border bg-bg px-3 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
              />
              <label htmlFor="cluster-filter" className="sr-only">
                Cluster
              </label>
              <select
                id="cluster-filter"
                value={cluster}
                onChange={(e) => setCluster(e.target.value)}
                className="h-8 rounded-lg border border-border bg-bg px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <option value="all">All clusters</option>
                {clusters.map((c) => (
                  <option key={c} value={c}>
                    {clusterLabel(c)}
                  </option>
                ))}
              </select>
            </div>
            {concepts.isPending ? (
              <Skeleton className="h-48 w-full" />
            ) : concepts.error ? (
              <ErrorState
                message={concepts.error.message}
                onRetry={() => void concepts.refetch()}
              />
            ) : (
              <ul
                aria-label="Concepts"
                className="grid max-h-64 gap-1 overflow-y-auto pr-1 sm:grid-cols-2"
              >
                {filtered.map((c) => {
                  const m = masteryBy.get(c.id);
                  return (
                    <li key={c.id}>
                      <button
                        type="button"
                        aria-pressed={conceptId === c.id}
                        onClick={() => setConceptId(c.id)}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring",
                          conceptId === c.id
                            ? "border-accent bg-surface-2"
                            : "border-transparent hover:bg-surface-2",
                        )}
                      >
                        <span className="min-w-0 flex-1 truncate">{c.name}</span>
                        {m && <MasteryBadge value={m.effective} showValue={false} />}
                      </button>
                    </li>
                  );
                })}
                {filtered.length === 0 && (
                  <li className="p-2 text-sm text-muted">No matching concepts.</li>
                )}
              </ul>
            )}
            <div className="flex flex-wrap items-center gap-3 border-t border-border pt-3 text-sm">
              <label className="flex items-center gap-2">
                Questions
                <select
                  value={count}
                  onChange={(e) => setCount(Number(e.target.value))}
                  className="h-8 rounded-lg border border-border bg-bg px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {[5, 8, 10].map((n) => (
                    <option key={n} value={n}>
                      {n}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={feedback === "exam"}
                  onChange={(e) => setFeedback(e.target.checked ? "exam" : "immediate")}
                  className="size-4 accent-[var(--primary)]"
                />
                Exam mode (feedback at the end)
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={timed}
                  onChange={(e) => setTimed(e.target.checked)}
                  className="size-4 accent-[var(--primary)]"
                />
                Timed (1 min per question)
              </label>
              <Button
                className="ml-auto"
                disabled={!conceptId || create.isPending}
                onClick={() =>
                  conceptId &&
                  void start({
                    mode: "concept",
                    concept_id: conceptId,
                    count,
                    feedback_mode: feedback,
                    timed,
                  })
                }
              >
                Start quiz
              </Button>
            </div>
          </Card>
        </div>
        <div className="space-y-4">
          <Card icon={<Sparkles />} title="Smart quiz">
            <p className="text-sm text-muted">
              Questions on your weakest concepts and the next one in the syllabus, at the right
              difficulty for your mastery.
            </p>
            <Button
              onClick={() => void start({ mode: "adaptive", count: 8 })}
              disabled={create.isPending}
            >
              Start smart quiz
            </Button>
          </Card>
          <Card icon={<CalendarClock />} title="Review">
            <p className="text-sm text-muted">
              {due > 0
                ? `${due} concept(s) are due for review.`
                : "Nothing is due right now. Reviews are scheduled as you practise."}
            </p>
            <Button
              variant="outline"
              disabled={due === 0 || create.isPending}
              onClick={() => void start({ mode: "review", count: 8 })}
            >
              Start review
            </Button>
          </Card>
        </div>
      </div>

      <section className="space-y-3">
        <h2 className="text-base font-semibold">History</h2>
        {history.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : history.error ? (
          <ErrorState message={history.error.message} onRetry={() => void history.refetch()} />
        ) : !history.data?.items.length ? (
          <EmptyState
            icon={<BookOpenCheck />}
            title="No quizzes yet"
            description="Your finished quizzes and scores appear here."
          />
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted">
                <tr className="border-b border-border">
                  <th className="px-4 py-2 font-medium">Quiz</th>
                  <th className="px-4 py-2 font-medium">Date</th>
                  <th className="px-4 py-2 font-medium">Score</th>
                  <th className="px-4 py-2 font-medium">
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.data.items.map((h) => {
                  const ratio = h.max_score ? (h.score ?? 0) / h.max_score : 0;
                  return (
                    <tr key={h.id} className="border-b border-border last:border-0">
                      <td className="px-4 py-2">
                        {MODE_LABEL[h.mode]}
                        {h.concept_name ? `: ${h.concept_name}` : ""}
                      </td>
                      <td className="px-4 py-2 text-muted">
                        {new Date(h.submitted_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-2">
                        <span
                          className={cn(
                            "tabular-nums",
                            { low: "text-danger", mid: "text-warning", high: "text-success" }[
                              masteryLevel(ratio)
                            ],
                          )}
                        >
                          {Math.round(ratio * 100)}%
                        </span>{" "}
                        <span className="text-xs text-muted">
                          ({h.score}/{h.max_score})
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <Link href={`/app/quizzes/${h.id}`} className="text-accent hover:underline">
                          Review
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
