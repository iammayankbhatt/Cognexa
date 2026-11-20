"use client";

import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  ChevronRight,
  ListChecks,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useCreateQuiz } from "@/lib/quiz/use-quiz";
import {
  pathConcepts,
  RULE_LABEL,
  useRecommendationClick,
  useRecommendations,
  type RecommendationItem,
  type Surface,
} from "@/lib/recommend";
import { cn } from "@/lib/utils";

/** The prerequisite chain behind a root-cause recommendation, gap first. */
export function PathChain({
  item,
  names,
}: {
  item: RecommendationItem;
  names?: Record<string, string>;
}) {
  const ids = pathConcepts(item.path);
  if (ids.length < 2) return null;
  const known = { ...item.names, ...names };
  const label = (id: string) =>
    id === item.concept_id ? item.name : (known[id] ?? id.replace(/_/g, " "));
  return (
    <ol className="flex flex-wrap items-center gap-1.5 text-xs" aria-label="Prerequisite path">
      {ids.map((id, i) => (
        <li key={id} className="flex items-center gap-1.5">
          <span
            className={cn(
              "rounded-full border px-2 py-0.5",
              i === 0 ? "border-danger text-text" : "border-border text-muted",
            )}
          >
            {label(id)}
          </span>
          {i < ids.length - 1 && <ChevronRight aria-hidden className="size-3 text-muted" />}
        </li>
      ))}
    </ol>
  );
}

function ActionButton({ item, compact }: { item: RecommendationItem; compact?: boolean }) {
  const router = useRouter();
  const click = useRecommendationClick();
  const create = useCreateQuiz();
  const logClick = () => {
    if (item.id) click.mutate(item.id);
  };
  if (item.action === "practice") {
    return (
      <Button
        size={compact ? "sm" : "default"}
        disabled={create.isPending}
        onClick={async () => {
          logClick();
          try {
            const s = await create.mutateAsync({
              mode: "concept",
              concept_id: item.concept_id,
              count: 8,
            });
            router.push(`/app/quizzes/${s.id}`);
          } catch (err) {
            toast.error(err instanceof ApiError ? err.message : "Could not start the quiz.");
          }
        }}
      >
        <ListChecks aria-hidden className="size-4" /> Practise {item.name}
      </Button>
    );
  }
  const href = item.action === "review" ? "/app/review" : `/app/learn/${item.concept_id}`;
  const Icon = item.action === "review" ? CalendarClock : BookOpen;
  return (
    <Link
      href={href}
      onClick={logClick}
      className={buttonVariants({ variant: "default", size: compact ? "sm" : "default" })}
    >
      <Icon aria-hidden className="size-4" />
      {item.action === "review" ? "Start review" : `Learn ${item.name}`}
      <ArrowRight aria-hidden className="size-4" />
    </Link>
  );
}

/** One recommendation: rule label, concept, reason, path and the action. */
export function NextStep({ item, compact }: { item: RecommendationItem; compact?: boolean }) {
  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold tracking-wide text-accent uppercase">
        {RULE_LABEL[item.rule]}
      </p>
      <p className={cn("font-semibold text-text", compact ? "text-sm" : "text-lg")}>{item.name}</p>
      <p className="text-sm text-muted">{item.reason}</p>
      <PathChain item={item} />
      <div className="pt-1">
        <ActionButton item={item} compact={compact} />
      </div>
    </div>
  );
}

/** "Next best step" card: the top recommendation, plus the others as small links. */
export function NextStepCard({ surface, className }: { surface: Surface; className?: string }) {
  const { data, isPending, error } = useRecommendations(surface);
  const click = useRecommendationClick();
  if (isPending)
    return <Skeleton className={cn("h-40 w-full", className)} aria-label="Loading next step" />;
  if (error || !data || !data.items.length) return null;
  const [top, ...rest] = data.items;
  return (
    <section
      aria-label="Next best step"
      className={cn("space-y-4 rounded-2xl border border-border bg-surface p-5", className)}
    >
      <div className="flex items-center gap-2 text-sm font-semibold">
        <Sparkles aria-hidden className="size-4 text-accent" />
        Next best step
      </div>
      <NextStep item={top} />
      {rest.length > 0 && (
        <div className="space-y-1.5 border-t border-border pt-3">
          <p className="text-xs text-muted">Also worth doing</p>
          <ul className="space-y-1">
            {rest.map((r) => (
              <li key={r.concept_id}>
                <Link
                  href={r.action === "review" ? "/app/review" : `/app/learn/${r.concept_id}`}
                  onClick={() => r.id && click.mutate(r.id)}
                  className="flex items-center gap-2 rounded-md px-1 py-1 text-sm outline-none hover:bg-surface-2 focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="text-xs text-muted">{RULE_LABEL[r.rule]}</span>
                  <span className="text-text">{r.name}</span>
                  <ChevronRight aria-hidden className="ml-auto size-3.5 text-muted" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
