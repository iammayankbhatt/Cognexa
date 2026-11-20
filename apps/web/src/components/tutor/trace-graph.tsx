"use client";

import { useMemo } from "react";

import { layerLayout, type GEdge, type GNode } from "@/lib/graph-layout";
import type { RetrievalTrace } from "@/lib/tutor/types";

const W = 320;
const ROW = 62; // vertical space per prerequisite layer
const PAD_X = 52; // room for centred labels at the edges
const PAD_Y = 20;
const R = 8;
const LABEL_CHARS = 18;

/** Nodes and edges of the traversal recorded in a trace (exact prerequisite paths + related). */
export function traceSubgraph(trace: RetrievalTrace): { nodes: GNode[]; edges: GEdge[] } {
  const nodes = new Map<string, GNode>();
  for (const c of trace.concepts) {
    nodes.set(c.id, { id: c.id, name: c.name, cluster: c.role, difficulty: 1 });
  }
  const edges = new Map<string, GEdge>();
  for (const c of trace.concepts) {
    for (const e of c.path) {
      if (nodes.has(e.source) && nodes.has(e.target)) {
        edges.set(`${e.source}>${e.target}>${e.type}`, e);
      }
    }
  }
  return { nodes: [...nodes.values()], edges: [...edges.values()] };
}

/**
 * Mini graph of the traversed subgraph: matched concepts filled with --primary, weak
 * prerequisites outlined in --danger, related concepts dashed. Arrows point from a prerequisite to
 * the concept that builds on it. A text list next to it carries the same information for screen
 * readers.
 */
export function TraceGraph({ trace }: { trace: RetrievalTrace }) {
  const { placed, edges, byId, height } = useMemo(() => {
    const { nodes, edges } = traceSubgraph(trace);
    const role = new Map(trace.concepts.map((c) => [c.id, c.role]));
    // Top-to-bottom suits the narrow panel: prerequisite layers become rows (prerequisites above
    // the concepts that build on them); related concepts get their own row at the bottom.
    const core = nodes.filter((n) => role.get(n.id) !== "related");
    const related = nodes.filter((n) => role.get(n.id) === "related");
    const layers = Math.max(0, ...layerLayout(core, edges, 1, 1).map((p) => p.layer)) + 1;
    const rows = layers + (related.length ? 1 : 0);
    const height = Math.max(110, rows * ROW + 2 * PAD_Y);
    const coreHeight = (layers - 1) * ROW;
    const placed = layerLayout(core, edges, coreHeight || 1, W - 2 * PAD_X, 0).map((p) => ({
      ...p,
      x: p.y + PAD_X,
      y: (layers === 1 ? 0 : p.x) + PAD_Y + 4,
    }));
    related.forEach((n, i) => {
      const span = W - 2 * PAD_X;
      placed.push({
        ...n,
        layer: layers,
        x: PAD_X + (related.length === 1 ? span / 2 : (i / (related.length - 1)) * span),
        y: PAD_Y + 4 + layers * ROW,
      });
    });
    return { placed, edges, byId: new Map(placed.map((p) => [p.id, p])), height };
  }, [trace]);
  // Busy rows alternate labels below/above their nodes so neighbours do not overlap.
  const rowIndex = new Map<string, number>();
  const rowCount = new Map<number, number>();
  for (const p of [...placed].sort((a, b) => a.x - b.x)) {
    const n = rowCount.get(p.y) ?? 0;
    rowIndex.set(p.id, n);
    rowCount.set(p.y, n + 1);
  }
  const info = new Map(trace.concepts.map((c) => [c.id, c]));
  if (!placed.length) return null;
  return (
    <svg
      viewBox={`0 0 ${W} ${height}`}
      className="h-auto w-full rounded-lg border border-border bg-bg"
      role="img"
      aria-label={`Traversed graph: ${placed.length} concepts, ${edges.length} edges`}
    >
      <defs>
        <marker
          id="trace-arrow"
          viewBox="0 0 10 10"
          refX="10"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M0,0 L10,5 L0,10 z" fill="var(--muted)" />
        </marker>
      </defs>
      {edges.map((e) => {
        const a = byId.get(e.source);
        const b = byId.get(e.target);
        if (!a || !b) return null;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        const related = e.type !== "PREREQUISITE_OF";
        return (
          <line
            key={`${e.source}-${e.target}-${e.type}`}
            x1={a.x + (dx / len) * R}
            y1={a.y + (dy / len) * R}
            x2={b.x - (dx / len) * (R + 2)}
            y2={b.y - (dy / len) * (R + 2)}
            stroke="var(--muted)"
            strokeWidth={1.2}
            strokeDasharray={related ? "3 3" : undefined}
            markerEnd={related ? undefined : "url(#trace-arrow)"}
          >
            <title>
              {related
                ? `${a.name} is related to ${b.name}`
                : `${a.name} is a prerequisite of ${b.name}`}
            </title>
          </line>
        );
      })}
      {placed.map((p) => {
        const c = info.get(p.id);
        const matched = c?.role === "matched";
        const weak = c?.role === "prerequisite" && c.weak;
        return (
          <g key={p.id}>
            <circle
              cx={p.x}
              cy={p.y}
              r={R}
              fill={matched ? "var(--primary)" : "var(--surface-2)"}
              stroke={weak ? "var(--danger)" : matched ? "var(--primary)" : "var(--border)"}
              strokeWidth={weak ? 2.5 : 1.5}
              strokeDasharray={c?.role === "related" ? "2 2" : undefined}
            />
            <text
              x={p.x}
              y={
                (rowCount.get(p.y) ?? 0) > 3 && (rowIndex.get(p.id) ?? 0) % 2 === 1
                  ? p.y - R - 5
                  : p.y + R + 12
              }
              textAnchor="middle"
              fontSize={9}
              fill="var(--text)"
            >
              <title>{p.name}</title>
              {p.name.length > LABEL_CHARS ? `${p.name.slice(0, LABEL_CHARS - 1)}…` : p.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
