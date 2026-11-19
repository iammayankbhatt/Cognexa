import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type Variant = "card" | "stat" | "list" | "text";

interface LoadingSkeletonProps {
  variant?: Variant;
  /** Number of repeated items (list rows, text lines, cards). */
  count?: number;
  /** Accessible description announced to screen readers. */
  label?: string;
  className?: string;
}

export function LoadingSkeleton({
  variant = "card",
  count = variant === "text" ? 3 : variant === "list" ? 4 : 1,
  label = "Loading",
  className,
}: LoadingSkeletonProps) {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <div role="status" aria-busy="true" aria-label={label} className={cn("w-full", className)}>
      {variant === "text" && (
        <div className="space-y-2.5">
          {items.map((i) => (
            <Skeleton key={i} className={cn("h-4", i === count - 1 ? "w-2/3" : "w-full")} />
          ))}
        </div>
      )}
      {variant === "list" && (
        <div className="space-y-3">
          {items.map((i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="size-10 shrink-0 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-1/3" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            </div>
          ))}
        </div>
      )}
      {variant === "stat" && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {items.map((i) => (
            <div key={i} className="space-y-3 rounded-xl border border-border bg-surface p-5">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-8 w-1/3" />
            </div>
          ))}
        </div>
      )}
      {variant === "card" && (
        <div className="space-y-4">
          {items.map((i) => (
            <div key={i} className="space-y-3 rounded-xl border border-border bg-surface p-5">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ))}
        </div>
      )}
      <span className="sr-only">{label}…</span>
    </div>
  );
}
