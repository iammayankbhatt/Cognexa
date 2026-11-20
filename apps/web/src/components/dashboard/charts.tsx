"use client";

import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { clusterLabel } from "@/components/quiz/quiz-home";
import { masteryLevel } from "@/components/shared/mastery";
import type { DashboardData } from "@/lib/dashboard";
import { shortDate } from "@/lib/usage";

const LEVEL_FILL = { low: "var(--danger)", mid: "var(--warning)", high: "var(--success)" };

function TableToggle({ table, onToggle }: { table: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={table}
      className="rounded text-xs text-accent underline-offset-2 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
    >
      {table ? "Show chart" : "Show table"}
    </button>
  );
}

/** Daily quiz accuracy over 30 days: one series, gaps on days without answers. */
export function AccuracyTrend({ data }: { data: DashboardData["accuracy_trend"] }) {
  const [table, setTable] = useState(false);
  const points = data.map((d) => ({
    ...d,
    pct: d.accuracy === null ? null : Math.round(d.accuracy * 100),
  }));
  const answered = points.filter((p) => p.pct !== null);
  return (
    <figure className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <figcaption className="text-sm font-semibold">Quiz accuracy, last 30 days</figcaption>
        <TableToggle table={table} onToggle={() => setTable((t) => !t)} />
      </div>
      {answered.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted">No graded answers yet.</p>
      ) : table ? (
        <div className="max-h-56 overflow-auto rounded-lg border border-border">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-surface-2 text-muted">
              <tr>
                <th className="px-3 py-1.5 font-medium">Day</th>
                <th className="px-3 py-1.5 text-right font-medium">Accuracy</th>
                <th className="px-3 py-1.5 text-right font-medium">Answers</th>
              </tr>
            </thead>
            <tbody>
              {answered.map((d) => (
                <tr key={d.date} className="border-t border-border">
                  <td className="px-3 py-1.5">{shortDate(d.date)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{d.pct}%</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{d.answers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          className="h-52"
          role="img"
          aria-label={`Accuracy on ${answered.length} days with quizzes`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(d: string) => shortDate(d)}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                minTickGap={24}
              />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(v: number) => `${v}%`}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ stroke: "var(--border)" }}
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "var(--text)",
                }}
                labelFormatter={(d) => shortDate(String(d))}
                formatter={(v) => [`${v}%`, "Accuracy"]}
              />
              <Line
                type="monotone"
                dataKey="pct"
                stroke="var(--primary)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--primary)" }}
                connectNulls
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  );
}

/** Mastery per cluster (unpractised concepts count as 0), coloured by mastery band. */
export function ClusterBars({ data }: { data: DashboardData["per_cluster"] }) {
  const [table, setTable] = useState(false);
  const rows = data.map((c) => ({
    ...c,
    label: clusterLabel(c.cluster),
    pct: Math.round(c.mastery * 100),
  }));
  return (
    <figure className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <figcaption className="text-sm font-semibold">Mastery by cluster</figcaption>
        <TableToggle table={table} onToggle={() => setTable((t) => !t)} />
      </div>
      {table ? (
        <table className="w-full text-left text-xs">
          <thead className="text-muted">
            <tr>
              <th className="py-1 font-medium">Cluster</th>
              <th className="py-1 text-right font-medium">Mastery</th>
              <th className="py-1 text-right font-medium">Practised</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.cluster} className="border-t border-border">
                <td className="py-1">{r.label}</td>
                <td className="py-1 text-right tabular-nums">{r.pct}%</td>
                <td className="py-1 text-right tabular-nums">
                  {r.practised}/{r.concepts}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="h-64" role="img" aria-label="Mastery by cluster">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={rows}
              layout="vertical"
              margin={{ top: 0, right: 16, bottom: 0, left: 8 }}
            >
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                domain={[0, 100]}
                tickFormatter={(v: number) => `${v}%`}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={120}
                interval={0}
                tick={{ fill: "var(--text)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: "var(--surface-2)" }}
                contentStyle={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderRadius: 8,
                  fontSize: 12,
                  color: "var(--text)",
                }}
                formatter={(v, _n, item) => [
                  `${v}% · ${item.payload.practised}/${item.payload.concepts} practised`,
                  "Mastery",
                ]}
              />
              <Bar dataKey="pct" radius={[0, 4, 4, 0]} isAnimationActive={false}>
                {rows.map((r) => (
                  <Cell key={r.cluster} fill={LEVEL_FILL[masteryLevel(r.mastery)]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </figure>
  );
}
