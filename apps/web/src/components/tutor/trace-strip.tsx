"use client";

import { ArrowRight, Database, GitBranch, Sparkles, TriangleAlert } from "lucide-react";

import type { RetrievalTrace } from "@/lib/tutor/types";
import { cn } from "@/lib/utils";

function Step({
  children,
  delay,
  className,
}: {
  children: React.ReactNode;
  delay: number;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-left-1",
        className,
      )}
      style={{
        animationDelay: `${delay}ms`,
        animationDuration: "200ms",
        animationFillMode: "both",
      }}
    >
      {children}
    </span>
  );
}

const Arrow = ({ delay }: { delay: number }) => (
  <Step delay={delay}>
    <ArrowRight aria-hidden className="size-3 text-muted" />
  </Step>
);

/**
 * "Matched: Recursion (0.95) → walking prerequisites → Call Stack ⚠ weak", shown as soon as the
 * trace event arrives (before any answer token).
 */
export function TraceStrip({ trace, onOpen }: { trace: RetrievalTrace; onOpen?: () => void }) {
  const prereqs = trace.concepts.filter((c) => c.role === "prerequisite").slice(0, 3);
  let body: React.ReactNode;
  if (trace.mode === "plain_rag") {
    body = (
      <Step delay={0}>
        <Database aria-hidden className="size-3.5 text-accent" />
        Plain RAG: {trace.chunks.length} chunks by similarity
      </Step>
    );
  } else if (!trace.is_on_topic) {
    body = <Step delay={0}>Not a DSA question</Step>;
  } else if (!trace.matched.length) {
    body = <Step delay={0}>No matching concept found</Step>;
  } else {
    body = (
      <>
        <Step delay={0}>
          <Sparkles aria-hidden className="size-3.5 text-accent" />
          {trace.classification_path === "continued" ? "Continuing:" : "Matched:"}
        </Step>
        {trace.matched.map((m, i) => (
          <Step key={m.id} delay={60 + i * 60} className="font-medium text-text">
            {m.name}
            {trace.classification_path !== "continued" && (
              <span className="font-normal text-muted">({m.confidence.toFixed(2)})</span>
            )}
          </Step>
        ))}
        {prereqs.length > 0 && (
          <>
            <Arrow delay={200} />
            <Step delay={240}>
              <GitBranch aria-hidden className="size-3.5 text-muted" />
              walking prerequisites
            </Step>
            <Arrow delay={300} />
            {prereqs.map((c, i) => (
              <Step key={c.id} delay={340 + i * 60} className="text-text">
                {c.name}
                {c.weak && (
                  <span className="inline-flex items-center gap-0.5 text-warning">
                    <TriangleAlert aria-hidden className="size-3" />
                    weak
                  </span>
                )}
              </Step>
            ))}
          </>
        )}
      </>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs text-muted">
      <span className="sr-only">Retrieval: </span>
      {body}
      {trace.cached && (
        <span className="rounded-full border border-border px-1.5 py-px text-[10px] tracking-wide uppercase">
          cached
        </span>
      )}
      {onOpen && (
        <button
          type="button"
          onClick={onOpen}
          className="ml-1 rounded px-1 text-accent underline-offset-2 outline-none hover:underline focus-visible:ring-2 focus-visible:ring-ring"
        >
          Why this answer?
        </button>
      )}
    </div>
  );
}
