import type { UsageDay } from "@/lib/api";

const DAY_MS = 86_400_000;

/** ISO date (YYYY-MM-DD) in UTC, matching the backend's usage days. */
export function utcDay(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** The last `days` UTC days ending today, oldest first, with zero rows for days without usage. */
export function fillDays(history: UsageDay[], days: number, today: Date = new Date()): UsageDay[] {
  const byDate = new Map(history.map((h) => [h.date, h]));
  const end = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const out: UsageDay[] = [];
  for (let i = days - 1; i >= 0; i--) {
    const date = utcDay(new Date(end - i * DAY_MS));
    out.push(
      byDate.get(date) ?? { date, ai_requests: 0, tokens_in: 0, tokens_out: 0, est_cost_usd: 0 },
    );
  }
  return out;
}

/** "Nov 20" from "2026-11-20" (UTC, so the label matches the usage day). */
export function shortDate(iso: string, locale?: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString(locale, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function formatUsd(v: number): string {
  if (v === 0) return "$0";
  return v < 0.01 ? `$${v.toFixed(4)}` : `$${v.toFixed(2)}`;
}
