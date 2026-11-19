"use client";

import { Sparkles } from "lucide-react";

import { useMe } from "@/components/app/me-provider";
import { cn } from "@/lib/utils";

/** Today's AI requests against the daily quota. Colour follows the mastery thresholds. */
export function UsageMeter({ className }: { className?: string }) {
  const { data: me } = useMe();
  if (!me) {
    return <div className={cn("h-9 w-32 animate-pulse rounded-lg bg-surface-2", className)} />;
  }
  const { ai_requests: used, daily_quota: quota } = me.usage;
  const pct = quota > 0 ? Math.min(100, Math.round((used / quota) * 100)) : 100;
  const tone = pct >= 90 ? "bg-danger" : pct >= 70 ? "bg-warning" : "bg-accent";
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg border border-border bg-surface px-2.5 py-1",
        className,
      )}
      title={`${used} of ${quota} AI requests used today`}
    >
      <Sparkles aria-hidden className="size-4 text-accent" />
      <div className="flex flex-col gap-1">
        <span className="text-xs leading-none text-text">
          {used}/{quota} <span className="text-muted">AI today</span>
        </span>
        <span
          role="progressbar"
          aria-label="AI requests used today"
          aria-valuemin={0}
          aria-valuemax={quota}
          aria-valuenow={used}
          className="h-1 w-24 overflow-hidden rounded-full bg-surface-2"
        >
          <span
            className={cn("block h-full rounded-full transition-[width] duration-200", tone)}
            style={{ width: `${pct}%` }}
          />
        </span>
      </div>
    </div>
  );
}
