"use client";

import { ArrowRight, BookOpen, Sparkles } from "lucide-react";
import Link from "next/link";

import { Skeleton } from "@/components/ui/skeleton";
import { useSuggestions } from "@/lib/tutor/use-tutor";

const FALLBACK = [
  {
    title: "Debug a crash",
    prompt:
      "Why does my recursive function crash for big inputs with maximum recursion depth exceeded?",
  },
  { title: "Complexity", prompt: "Why is binary search O(log n)?" },
];

/** New chat: starter prompts and the next concept to learn. */
export function ChatEmpty({ onPick }: { onPick: (prompt: string) => void }) {
  const { data, isPending } = useSuggestions();
  const starters = data?.starters ?? (isPending ? [] : FALLBACK);
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-6 py-10 text-center">
      <span className="flex size-12 items-center justify-center rounded-full bg-surface-2 text-accent">
        <Sparkles aria-hidden className="size-6" />
      </span>
      <div className="space-y-1">
        <h2 className="text-xl font-semibold">What are you stuck on?</h2>
        <p className="text-sm text-muted">
          Describe the problem in your own words. Cognexa finds the concept behind it, walks its
          prerequisites, and answers from the course notes.
        </p>
      </div>
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {isPending
          ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-20" />)
          : starters.map((s) => (
              <button
                key={s.prompt}
                type="button"
                onClick={() => onPick(s.prompt)}
                className="flex flex-col gap-1 rounded-xl border border-border bg-surface p-3 text-left transition-colors duration-150 outline-none hover:border-accent focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="text-xs font-semibold tracking-wide text-accent uppercase">
                  {s.title}
                </span>
                <span className="text-sm text-text">{s.prompt}</span>
              </button>
            ))}
      </div>
      {data?.continue && (
        <Link
          href={`/app/learn/${encodeURIComponent(data.continue.concept_id)}`}
          className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface-2 p-3 text-left transition-colors duration-150 outline-none hover:border-accent focus-visible:ring-2 focus-visible:ring-ring"
        >
          <BookOpen aria-hidden className="size-5 shrink-0 text-accent" />
          <span className="min-w-0 flex-1">
            <span className="block text-sm font-medium text-text">
              Continue learning: {data.continue.name}
            </span>
            <span className="block text-xs text-muted">{data.continue.reason}</span>
          </span>
          <ArrowRight aria-hidden className="size-4 text-muted" />
        </Link>
      )}
    </div>
  );
}
