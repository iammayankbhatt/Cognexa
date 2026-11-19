import { cn } from "@/lib/utils";

import { masteryLevel, type MasteryLevel } from "./mastery";

const STYLES: Record<MasteryLevel, { label: string; classes: string; dot: string }> = {
  low: {
    label: "Needs work",
    classes: "border-danger/40 bg-danger/10 text-danger",
    dot: "bg-danger",
  },
  mid: {
    label: "Getting there",
    classes: "border-warning/40 bg-warning/10 text-warning",
    dot: "bg-warning",
  },
  high: {
    label: "Strong",
    classes: "border-success/40 bg-success/10 text-success",
    dot: "bg-success",
  },
};

interface MasteryBadgeProps {
  /** Mastery score from 0 to 1. Values outside the range are clamped. */
  value: number;
  /** Show the percentage next to the label. */
  showValue?: boolean;
  className?: string;
}

export function MasteryBadge({ value, showValue = true, className }: MasteryBadgeProps) {
  const clamped = Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
  const level = masteryLevel(clamped);
  const style = STYLES[level];
  const percent = Math.round(clamped * 100);

  return (
    <span
      data-level={level}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
        style.classes,
        className,
      )}
    >
      <span aria-hidden className={cn("size-1.5 rounded-full", style.dot)} />
      {style.label}
      {showValue && <span className="tabular-nums opacity-90">{percent}%</span>}
    </span>
  );
}
