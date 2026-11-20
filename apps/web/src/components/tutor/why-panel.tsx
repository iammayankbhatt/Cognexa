"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Info, X } from "lucide-react";
import { useState } from "react";

import { ConceptChip } from "@/components/shared/concept-chip";
import { Markdown } from "@/components/tutor/markdown";
import { TraceGraph } from "@/components/tutor/trace-graph";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { ChatMessage, RetrievalTrace } from "@/lib/tutor/types";
import { cn } from "@/lib/utils";

const PATH_LABEL: Record<RetrievalTrace["classification_path"], string> = {
  llm: "LLM classifier",
  hybrid: "Hybrid fallback (fulltext + embeddings)",
  continued: "Continued after a quick check",
  cache: "Cache",
  none: "No concept matched",
};

const ACTION_LABEL: Record<string, string> = {
  answer_now: "Answer now",
  ask_diagnostic: "Ask a quick check",
  expand_traversal: "Expand the graph walk (depth 3)",
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{title}</h3>
      {children}
    </section>
  );
}

interface ChunkText {
  id: string;
  concept_id: string;
  kind: string;
  heading: string;
  text: string;
}

function ChunkItem({
  chunk,
  names,
}: {
  chunk: RetrievalTrace["chunks"][number];
  names: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);
  const { data, isPending } = useQuery({
    queryKey: ["tutor", "chunk", chunk.id],
    queryFn: () => api<ChunkText[]>(`/tutor/chunks?ids=${encodeURIComponent(chunk.id)}`),
    enabled: open,
    staleTime: Infinity,
  });
  return (
    <li className="rounded-lg border border-border bg-surface">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="font-medium text-text">{names[chunk.concept_id] ?? chunk.concept_id}</span>
        <span className="font-mono text-muted">/{chunk.kind}</span>
        <span className="ml-auto text-muted">
          {chunk.score !== null ? `${chunk.score.toFixed(2)} · ` : ""}
          {chunk.tokens} tok
        </span>
        <ChevronDown
          aria-hidden
          className={cn(
            "size-3.5 text-muted transition-transform duration-150",
            open && "rotate-180",
          )}
        />
      </button>
      {open && (
        <div className="border-t border-border px-3 py-2">
          {isPending ? (
            <Skeleton className="h-16 w-full" />
          ) : data?.[0] ? (
            <Markdown text={data[0].text} className="text-xs" />
          ) : (
            <p className="text-xs text-muted">This chunk is no longer available.</p>
          )}
        </div>
      )}
    </li>
  );
}

export function WhyPanel({
  message,
  onClose,
}: {
  message: ChatMessage | null;
  onClose?: () => void;
}) {
  const trace = message?.trace;
  return (
    <aside aria-label="Why this answer" className="flex h-full flex-col">
      <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-4">
        <Info aria-hidden className="size-4 text-accent" />
        <h2 className="text-sm font-semibold">Why this answer?</h2>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="ml-auto rounded p-1 text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="size-4" />
          </button>
        )}
      </div>
      {!trace ? (
        <p className="p-4 text-sm text-muted">
          Ask a question to see which concepts were matched, which prerequisites were walked and
          which notes the answer used.
        </p>
      ) : (
        <WhyBody message={message} trace={trace} />
      )}
    </aside>
  );
}

function WhyBody({ message, trace }: { message: ChatMessage; trace: RetrievalTrace }) {
  const names: Record<string, string> = Object.fromEntries(
    trace.concepts.map((c) => [c.id, c.name]),
  );
  for (const m of trace.matched) names[m.id] = m.name;
  const prereqs = trace.concepts.filter((c) => c.role === "prerequisite");
  const related = trace.concepts.filter((c) => c.role === "related");
  return (
    <div className="flex-1 space-y-5 overflow-y-auto p-4">
      {trace.mode === "graphrag" ? (
        <>
          <Section title="Matched concepts">
            <p className="text-xs text-muted">Path: {PATH_LABEL[trace.classification_path]}</p>
            {trace.matched.length ? (
              <ul className="space-y-1.5">
                {trace.matched.map((m) => (
                  <li key={m.id} className="flex items-center gap-2 text-sm">
                    <ConceptChip name={m.name} href={`/app/learn/${m.id}`} />
                    <span className="text-xs text-muted">{m.confidence.toFixed(2)}</span>
                    {m.reason && (
                      <span className="truncate text-xs text-muted" title={m.reason}>
                        {m.reason}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted">None.</p>
            )}
            {trace.fallback && (
              <p className="text-xs text-muted">
                Fallback lists: fulltext [{trace.fallback.fulltext.join(", ") || "none"}],
                embeddings [{trace.fallback.embedding.join(", ") || "none"}]
              </p>
            )}
          </Section>
          {trace.concepts.length > 0 && (
            <Section title="Graph walk">
              <TraceGraph trace={trace} />
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted">
                <span className="inline-flex items-center gap-1">
                  <span aria-hidden className="size-2.5 rounded-full bg-primary" /> matched
                </span>
                <span className="inline-flex items-center gap-1">
                  <span aria-hidden className="size-2.5 rounded-full border-2 border-danger" /> weak
                  prerequisite
                </span>
                <span>→ prerequisite of</span>
                <span>- - related</span>
              </div>
              <ul className="space-y-1 text-xs">
                {prereqs.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-1">
                    <span className={cn("font-medium", c.weak ? "text-danger" : "text-text")}>
                      {c.name}
                    </span>
                    <span className="text-muted">
                      {c.weak
                        ? c.mastery === null
                          ? "weak (never practised)"
                          : `weak (mastery ${c.mastery.toFixed(2)})`
                        : `known (${(c.mastery ?? 0).toFixed(2)})`}
                      {" · "}
                      {c.path.map((e) => names[e.source] ?? e.source).join(" → ")}
                      {c.path.length ? ` → ${names[c.path[c.path.length - 1].target] ?? ""}` : ""}
                    </span>
                  </li>
                ))}
                {related.length > 0 && (
                  <li className="text-muted">Related: {related.map((c) => c.name).join(", ")}</li>
                )}
              </ul>
            </Section>
          )}
          {trace.controller.length > 0 && (
            <Section title="Agentic step">
              <ol className="space-y-1 text-xs">
                {trace.controller.map((s, i) => (
                  <li key={i}>
                    <span className="font-medium text-text">
                      {ACTION_LABEL[s.action] ?? s.action}
                    </span>
                    {s.reason && <span className="text-muted"> · {s.reason}</span>}
                  </li>
                ))}
              </ol>
            </Section>
          )}
        </>
      ) : (
        <Section title="Plain RAG baseline">
          <p className="text-xs text-muted">
            The question was embedded and the {trace.chunks.length} most similar chunks were used,
            with no graph walk.
          </p>
        </Section>
      )}
      <Section title={`Notes used (${trace.used_tokens}/${trace.budget_tokens} tokens)`}>
        {trace.chunks.length ? (
          <ul className="space-y-1.5">
            {trace.chunks.map((c) => (
              <ChunkItem key={c.id} chunk={c} names={names} />
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">No notes were used.</p>
        )}
      </Section>
      <Section title="Model">
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
          <dt className="text-muted">Provider</dt>
          <dd>{message.cached ? "cache" : (message.provider ?? "—")}</dd>
          <dt className="text-muted">Model</dt>
          <dd className="truncate">{message.model ?? "—"}</dd>
          <dt className="text-muted">Latency</dt>
          <dd>{message.latencyMs != null ? `${(message.latencyMs / 1000).toFixed(1)} s` : "—"}</dd>
          <dt className="text-muted">Tokens in / out</dt>
          <dd>
            {message.tokensIn ?? 0} / {message.tokensOut ?? 0}
          </dd>
          <dt className="text-muted">Flags</dt>
          <dd>
            {[
              message.cached && "cached",
              message.truncated && "stopped early",
              message.moderated && "moderated",
            ]
              .filter(Boolean)
              .join(", ") || "none"}
          </dd>
        </dl>
      </Section>
    </div>
  );
}
