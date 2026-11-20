"use client";

import { GitCompareArrows, Loader2 } from "lucide-react";

import { Markdown } from "@/components/tutor/markdown";
import { TraceStrip } from "@/components/tutor/trace-strip";
import type { CompareResult, CompareSide } from "@/lib/tutor/types";

function conceptsInContext(side: CompareSide): string[] {
  return [...new Set(side.trace.chunks.map((c) => c.concept_id))];
}

function Column({
  title,
  side,
  highlight,
}: {
  title: string;
  side: CompareSide;
  highlight: Set<string>;
}) {
  const names = Object.fromEntries(side.trace.concepts.map((c) => [c.id, c.name]));
  const concepts = conceptsInContext(side);
  return (
    <section
      className="flex min-w-0 flex-col gap-2 rounded-xl border border-border bg-surface p-4"
      aria-label={title}
    >
      <h3 className="text-sm font-semibold">{title}</h3>
      <TraceStrip trace={side.trace} />
      <p className="text-xs text-muted">
        Context concepts:{" "}
        {concepts.map((c, i) => (
          <span key={c} className={highlight.has(c) ? "font-semibold text-accent" : undefined}>
            {i > 0 && ", "}
            {c}
          </span>
        ))}
      </p>
      <Markdown text={side.content} conceptNames={names} />
      <p className="mt-auto pt-2 text-xs text-muted">
        {(side.latency_ms / 1000).toFixed(1)} s · {side.tokens_in} in / {side.tokens_out} out ·{" "}
        {side.trace.used_tokens} context tokens
      </p>
    </section>
  );
}

/** The project's central claim, live: the same question through GraphRAG and plain RAG. */
export function CompareView({
  result,
  pending,
  question,
}: {
  result?: CompareResult;
  pending: boolean;
  question: string;
}) {
  const graphOnly = result
    ? new Set(
        conceptsInContext(result.graphrag).filter(
          (c) => !conceptsInContext(result.plain_rag).includes(c),
        ),
      )
    : new Set<string>();
  return (
    <div className="space-y-3">
      <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-fg">
        {question}
      </div>
      <p className="flex items-center gap-2 text-xs text-muted">
        <GitCompareArrows aria-hidden className="size-3.5 text-accent" />
        Comparison (not saved to the chat). Concepts only GraphRAG brought in are highlighted.
      </p>
      {pending || !result ? (
        <p className="flex items-center gap-2 text-sm text-muted">
          <Loader2 aria-hidden className="size-4 animate-spin text-accent" />
          Running both pipelines…
        </p>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          <Column title="GraphRAG (Cognexa)" side={result.graphrag} highlight={graphOnly} />
          <Column title="Plain RAG (baseline)" side={result.plain_rag} highlight={new Set()} />
        </div>
      )}
    </div>
  );
}
