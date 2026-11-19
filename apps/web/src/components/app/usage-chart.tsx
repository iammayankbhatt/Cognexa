"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { UsageDay } from "@/lib/api";
import { formatUsd, shortDate } from "@/lib/usage";

interface TooltipProps {
  active?: boolean;
  payload?: { payload: UsageDay }[];
}

function DayTooltip({ active, payload }: TooltipProps) {
  const day = active ? payload?.[0]?.payload : undefined;
  if (!day) return null;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg">
      <p className="font-medium text-text">{shortDate(day.date)}</p>
      <p className="text-muted">
        <span className="text-text tabular-nums">{day.ai_requests}</span> AI requests
      </p>
      <p className="text-muted">
        <span className="text-text tabular-nums">
          {(day.tokens_in + day.tokens_out).toLocaleString()}
        </span>{" "}
        tokens · {formatUsd(day.est_cost_usd)}
      </p>
    </div>
  );
}

/**
 * AI requests per day: a single series, so no legend (the heading names it). Bars use the theme's
 * primary colour (validated against each theme's surface), 4 px rounded tops, a recessive grid,
 * a hover tooltip per bar, and a table view for screen readers and exact values.
 */
export function UsageChart({ days, label }: { days: UsageDay[]; label: string }) {
  const [table, setTable] = useState(false);
  const total = days.reduce((n, d) => n + d.ai_requests, 0);
  return (
    <figure className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <figcaption className="text-sm text-muted">
          {label}: <span className="text-text tabular-nums">{total}</span> requests
        </figcaption>
        <button
          type="button"
          onClick={() => setTable((t) => !t)}
          className="rounded text-xs text-accent underline-offset-2 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          aria-pressed={table}
        >
          {table ? "Show chart" : "Show table"}
        </button>
      </div>
      {table ? (
        <div className="max-h-56 overflow-auto rounded-lg border border-border">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-surface-2 text-muted">
              <tr>
                <th className="px-3 py-1.5 font-medium">Day</th>
                <th className="px-3 py-1.5 text-right font-medium">Requests</th>
                <th className="px-3 py-1.5 text-right font-medium">Tokens</th>
                <th className="px-3 py-1.5 text-right font-medium">Est. cost</th>
              </tr>
            </thead>
            <tbody>
              {[...days].reverse().map((d) => (
                <tr key={d.date} className="border-t border-border text-text">
                  <td className="px-3 py-1.5">{shortDate(d.date)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{d.ai_requests}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {(d.tokens_in + d.tokens_out).toLocaleString()}
                  </td>
                  <td className="px-3 py-1.5 text-right tabular-nums">
                    {formatUsd(d.est_cost_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="h-44 w-full" role="img" aria-label={`${label}: ${total} requests`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={days} margin={{ top: 4, right: 4, bottom: 0, left: -24 }} barGap={2}>
              <CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="0" />
              <XAxis
                dataKey="date"
                tickFormatter={(v: string) => shortDate(v)}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: "var(--border)" }}
                minTickGap={24}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={48}
              />
              <Tooltip
                content={<DayTooltip />}
                cursor={{ fill: "var(--surface-2)" }}
                isAnimationActive={false}
              />
              <Bar
                dataKey="ai_requests"
                name="AI requests"
                fill="var(--primary)"
                radius={[4, 4, 0, 0]}
                maxBarSize={28}
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  );
}
