"use client";

import { useQuery } from "@tanstack/react-query";
import { Network } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { layerLayout, type GEdge, type GNode } from "@/lib/graph-layout";

interface GraphData {
  subject_id: string;
  nodes: GNode[];
  edges: GEdge[];
}

const W = 1100;
const H = 520;
// Theme variables only (CLAUDE.md section 6): no hard-coded colours.
const CLUSTER_COLORS = [
  "var(--primary)",
  "var(--accent)",
  "var(--success)",
  "var(--warning)",
  "var(--danger)",
  "var(--muted)",
  "var(--text)",
  "var(--border)",
];

/** Read-only prerequisite graph from GET /graph (public). Hover or focus a node to see its links. */
export function LiveGraph() {
  const { data, error, isPending, refetch } = useQuery({
    queryKey: ["public-graph"],
    queryFn: () => api<GraphData>("/graph", { anonymous: true }),
    staleTime: 5 * 60_000,
  });
  const [active, setActive] = useState<string | null>(null);

  const layout = useMemo(() => {
    if (!data) return null;
    const placed = layerLayout(data.nodes, data.edges, W, H);
    const byId = new Map(placed.map((p) => [p.id, p]));
    const clusters = [...new Set(data.nodes.map((n) => n.cluster))].sort();
    return { placed, byId, clusters };
  }, [data]);

  if (isPending) return <Skeleton className="h-[26rem] w-full" aria-label="Loading graph" />;
  if (error || !data || !layout) {
    return (
      <ErrorState
        title="The graph isn't available right now"
        message={error?.message ?? "Please try again in a moment."}
        requestId={error instanceof ApiError ? error.requestId : undefined}
        onRetry={() => void refetch()}
      />
    );
  }
  if (data.nodes.length === 0) {
    return (
      <EmptyState
        icon={<Network />}
        title="No concepts yet"
        description="The concept graph has not been loaded."
      />
    );
  }

  const color = (cluster: string) =>
    CLUSTER_COLORS[layout.clusters.indexOf(cluster) % CLUSTER_COLORS.length];
  const prereq = data.edges.filter((e) => e.type === "PREREQUISITE_OF");
  const neighbours = new Set<string>();
  if (active) {
    for (const e of prereq) {
      if (e.source === active) neighbours.add(e.target);
      if (e.target === active) neighbours.add(e.source);
    }
  }
  const activeNode = active ? layout.byId.get(active) : null;

  return (
    <figure className="space-y-3">
      <div className="overflow-x-auto rounded-2xl border border-border bg-surface p-2">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="group"
          aria-label={`Prerequisite graph with ${data.nodes.length} concepts and ${prereq.length} prerequisite links. Arrows point from a prerequisite to the concept that needs it.`}
          className="h-auto w-full min-w-[48rem]"
        >
          <g>
            {prereq.map((e) => {
              const a = layout.byId.get(e.source);
              const b = layout.byId.get(e.target);
              if (!a || !b) return null;
              const hot = active === e.source || active === e.target;
              return (
                <line
                  key={`${e.source}-${e.target}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={hot ? "var(--accent)" : "var(--border)"}
                  strokeWidth={hot ? 2 : 1}
                  opacity={active && !hot ? 0.25 : 1}
                />
              );
            })}
          </g>
          <g>
            {layout.placed.map((n) => {
              const dim = active && n.id !== active && !neighbours.has(n.id);
              return (
                <g
                  key={n.id}
                  tabIndex={0}
                  role="img"
                  aria-label={`${n.name}, ${n.cluster.replace(/_/g, " ")}`}
                  onMouseEnter={() => setActive(n.id)}
                  onMouseLeave={() => setActive(null)}
                  onFocus={() => setActive(n.id)}
                  onBlur={() => setActive(null)}
                  opacity={dim ? 0.3 : 1}
                  className="cursor-pointer outline-none"
                >
                  <circle
                    cx={n.x}
                    cy={n.y}
                    r={n.id === active ? 9 : 6}
                    fill={color(n.cluster)}
                    stroke="var(--bg)"
                    strokeWidth="2"
                  />
                </g>
              );
            })}
          </g>
          {activeNode && (
            <g pointerEvents="none">
              <rect
                x={Math.min(Math.max(activeNode.x - 80, 4), W - 164)}
                y={Math.max(activeNode.y - 40, 4)}
                width="160"
                height="26"
                rx="6"
                fill="var(--surface-2)"
                stroke="var(--border)"
              />
              <text
                x={Math.min(Math.max(activeNode.x - 80, 4), W - 164) + 80}
                y={Math.max(activeNode.y - 40, 4) + 17}
                textAnchor="middle"
                fontSize="12"
                fill="var(--text)"
              >
                {activeNode.name}
              </text>
            </g>
          )}
        </svg>
      </div>
      <figcaption className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        {layout.clusters.map((c) => (
          <span key={c} className="inline-flex items-center gap-1.5">
            <span aria-hidden className="size-2.5 rounded-full" style={{ background: color(c) }} />
            {c.replace(/_/g, " ")}
          </span>
        ))}
        <span className="ml-auto">
          {data.nodes.length} concepts · {prereq.length} prerequisite links. Left to right:
          foundations first.
        </span>
      </figcaption>
    </figure>
  );
}
