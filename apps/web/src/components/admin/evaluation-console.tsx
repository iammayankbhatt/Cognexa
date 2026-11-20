"use client";

import { useQuery } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Markdown } from "@/components/tutor/markdown";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Summary = Record<string, number | null>;
interface Pair {
  metric: string;
  pairs: number;
  mean_a: number;
  mean_b: number;
  mean_diff: number;
  ci_low: number;
  ci_high: number;
  p_value: number;
  rank_biserial: number;
}
interface Run {
  id: string;
  name: string;
  started_at: string;
  finished_at: string | null;
  config: Record<string, unknown>;
  results: number;
  headline?: Record<string, Record<string, Summary>>;
  headline_pairs: Pair[];
  overall_pairs: Pair[];
}
interface Item {
  item_id: string;
  question: string;
  category: string;
  gold_concepts: string[];
  gold_prerequisites: string[];
  modes: Record<
    string,
    {
      answer: string | null;
      context_concepts: string[];
      metrics: Record<string, unknown>;
      latency_ms: number | null;
      tokens: number;
    }
  >;
}

const COLUMNS: [string, string][] = [
  ["n", "n"],
  ["prerequisite_hit_rate", "Prereq hit"],
  ["concept_accuracy@1", "Concept@1"],
  ["concept_accuracy@3", "Concept@3"],
  ["off_topic_decline_accuracy", "Off-topic"],
  ["faithfulness", "Faithful."],
  ["answer_relevancy", "Ans. rel."],
  ["context_precision", "Ctx prec."],
  ["context_recall", "Ctx recall"],
  ["avg_latency_ms", "Latency ms"],
  ["avg_tokens", "Tokens"],
];

function fmt(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v >= 10 ? v.toFixed(0) : v.toFixed(2);
}

function MetricTable({
  table,
  categories,
}: {
  table: Record<string, Record<string, Summary>>;
  categories: string[];
}) {
  const modes = Object.keys(table).sort();
  const cols = COLUMNS.filter(([k]) =>
    modes.some((m) => categories.some((c) => table[m]?.[c]?.[k] != null)),
  );
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead className="bg-surface-2 text-left text-xs text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Category</th>
            <th className="px-3 py-2 font-medium">Mode</th>
            {cols.map(([k, label]) => (
              <th key={k} className="px-3 py-2 text-right font-medium">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {categories.flatMap((c) =>
            modes
              .filter((m) => table[m]?.[c]?.n)
              .map((m) => (
                <tr
                  key={`${c}-${m}`}
                  className={cn(
                    "border-t border-border",
                    c === "unnamed_prerequisite" && "bg-surface-2/50",
                  )}
                >
                  <td className="px-3 py-1.5">{c.replace(/_/g, " ")}</td>
                  <td className="px-3 py-1.5 font-medium">{m}</td>
                  {cols.map(([k]) => (
                    <td key={k} className="px-3 py-1.5 text-right tabular-nums">
                      {fmt(table[m][c][k])}
                    </td>
                  ))}
                </tr>
              )),
          )}
        </tbody>
      </table>
    </div>
  );
}

function PairTable({ rows }: { rows: Pair[] }) {
  if (!rows.length) return null;
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead className="bg-surface-2 text-left text-xs text-muted">
          <tr>
            {[
              "Metric",
              "Pairs",
              "Plain RAG",
              "GraphRAG",
              "Δ mean",
              "95 % CI",
              "Wilcoxon p",
              "r",
            ].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.metric} className="border-t border-border tabular-nums">
              <td className="px-3 py-1.5">{r.metric.replace(/_/g, " ")}</td>
              <td className="px-3 py-1.5">{r.pairs}</td>
              <td className="px-3 py-1.5">{r.mean_a.toFixed(2)}</td>
              <td className="px-3 py-1.5">{r.mean_b.toFixed(2)}</td>
              <td
                className={cn(
                  "px-3 py-1.5",
                  r.mean_diff > 0 ? "text-success" : r.mean_diff < 0 ? "text-danger" : "",
                )}
              >
                {r.mean_diff >= 0 ? "+" : ""}
                {r.mean_diff.toFixed(2)}
              </td>
              <td className="px-3 py-1.5">
                [{r.ci_low.toFixed(2)}, {r.ci_high.toFixed(2)}]
              </td>
              <td className="px-3 py-1.5">{r.p_value < 0.001 ? "<0.001" : r.p_value.toFixed(3)}</td>
              <td className="px-3 py-1.5">{r.rank_biserial.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ItemRow({ item }: { item: Item }) {
  const [open, setOpen] = useState(false);
  const g = item.modes.graphrag;
  const p = item.modes.plain_rag;
  const hit = (m?: Item["modes"][string]) => m?.metrics.prerequisite_hit;
  return (
    <li className="rounded-xl border border-border bg-surface">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="font-mono text-xs text-muted">{item.item_id}</span>
        <span className="min-w-0 flex-1 truncate">{item.question}</span>
        {item.gold_prerequisites.length > 0 && (
          <span className="shrink-0 text-xs text-muted">
            prereq hit: GraphRAG {hit(g) === 1 ? "✓" : "✗"} · plain {hit(p) === 1 ? "✓" : "✗"}
          </span>
        )}
      </button>
      {open && (
        <div className="space-y-3 border-t border-border p-4">
          <p className="text-xs text-muted">
            {item.category.replace(/_/g, " ")} · gold: {item.gold_concepts.join(", ") || "—"} · gold
            prerequisites: {item.gold_prerequisites.join(", ") || "—"}
          </p>
          <div className="grid gap-3 lg:grid-cols-2">
            {(["graphrag", "plain_rag"] as const).map((m) => (
              <section
                key={m}
                className="space-y-2 rounded-lg border border-border p-3"
                aria-label={m}
              >
                <h3 className="text-sm font-semibold">
                  {m === "graphrag" ? "GraphRAG" : "Plain RAG"}
                </h3>
                <p className="text-xs text-muted">
                  Context: {item.modes[m]?.context_concepts.join(", ") || "none"}
                </p>
                {item.modes[m]?.answer ? (
                  <Markdown text={item.modes[m].answer!} className="text-xs" />
                ) : (
                  <p className="text-xs text-muted">No answer.</p>
                )}
              </section>
            ))}
          </div>
        </div>
      )}
    </li>
  );
}

/** Evaluation runs pushed by `evaluation/ragas_eval.py --push`. */
export function EvaluationConsole() {
  const runs = useQuery({
    queryKey: ["admin", "eval", "runs"],
    queryFn: () => api<{ items: Run[] }>("/admin/evaluation/runs"),
  });
  const [picked, setPicked] = useState<string | null>(null);
  const [category, setCategory] = useState("unnamed_prerequisite");
  const runId = picked ?? runs.data?.items[0]?.id ?? null;
  const run = useQuery({
    queryKey: ["admin", "eval", "run", runId],
    queryFn: () => api<Run>(`/admin/evaluation/runs/${runId}`),
    enabled: Boolean(runId),
  });
  const items = useQuery({
    queryKey: ["admin", "eval", "items", runId, category],
    queryFn: () =>
      api<{ items: Item[] }>(
        `/admin/evaluation/runs/${runId}/items?category=${encodeURIComponent(category)}`,
      ),
    enabled: Boolean(runId),
  });

  if (runs.isPending) return <Skeleton className="h-64 w-full" />;
  if (runs.error)
    return <ErrorState message={runs.error.message} onRetry={() => void runs.refetch()} />;
  if (!runs.data?.items.length) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Evaluation"
          description="GraphRAG vs plain RAG on the 85-item test set."
        />
        <EmptyState
          icon={<FlaskConical />}
          title="No evaluation runs yet"
          description="Run `uv run --project apps/api --group eval python evaluation/ragas_eval.py --push` to store a run here."
        />
      </div>
    );
  }
  const table = run.data?.headline ?? {};
  const cats = Object.keys(Object.values(table)[0] ?? {})
    .filter((c) => c !== "all")
    .sort();
  const fake = Boolean(run.data?.config?.fake);
  return (
    <div className="space-y-6">
      <PageHeader
        title="Evaluation"
        description="GraphRAG vs plain RAG on the 85-item test set. The headline row is unnamed-prerequisite questions."
      />
      <label className="flex items-center gap-2 text-sm">
        Run
        <select
          value={runId ?? ""}
          onChange={(e) => setPicked(e.target.value)}
          className="h-8 rounded-lg border border-border bg-surface px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {runs.data.items.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name} · {new Date(r.started_at).toLocaleString()} · {r.results} results
            </option>
          ))}
        </select>
      </label>
      {fake && (
        <p role="note" className="rounded-xl border border-warning/40 bg-warning/5 p-3 text-sm">
          This run used the offline fake model: retrieval metrics are meaningful, answer-quality
          metrics are not.
        </p>
      )}
      {run.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <>
          <section className="space-y-2">
            <h2 className="text-base font-semibold">Headline (paired, GraphRAG minus plain RAG)</h2>
            <PairTable rows={run.data?.headline_pairs ?? []} />
          </section>
          <section className="space-y-2">
            <h2 className="text-base font-semibold">By mode and category</h2>
            <MetricTable table={table} categories={["all", ...cats]} />
          </section>
        </>
      )}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold">Items</h2>
          <label htmlFor="eval-category" className="sr-only">
            Category
          </label>
          <select
            id="eval-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="h-8 rounded-lg border border-border bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {(cats.length ? cats : ["unnamed_prerequisite"]).map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        {items.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <ul className="space-y-2">
            {(items.data?.items ?? []).map((i) => (
              <ItemRow key={i.item_id} item={i} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
