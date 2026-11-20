"use client";

import type { Core, ElementDefinition, EventObject, StylesheetJson } from "cytoscape";
import { Download, ListChecks, MessageSquare, Route, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { tutorLink } from "@/components/quiz/feedback-panel";
import { clusterLabel } from "@/components/quiz/quiz-home";
import { ErrorState } from "@/components/shared/error-state";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { PageHeader } from "@/components/shared/page-header";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useMasteryGraph, type MapNode, type MasteryGraph } from "@/lib/dashboard";
import { useCreateQuiz } from "@/lib/quiz/use-quiz";
import { pathConcepts, useRecommendations } from "@/lib/recommend";
import { cn } from "@/lib/utils";

const BAND_VAR: Record<MapNode["band"], string> = {
  weak: "--danger",
  developing: "--warning",
  strong: "--success",
  not_started: "--surface-2",
};
const BAND_LABEL: Record<MapNode["band"], string> = {
  weak: "Weak",
  developing: "Developing",
  strong: "Strong",
  not_started: "Not started",
};

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888888";
}

/** Cytoscape stylesheet from the current theme's CSS variables (canvas cannot read var()). */
export function mapStyle(read: (name: string) => string): StylesheetJson {
  const band = (b: MapNode["band"]) => read(BAND_VAR[b]);
  return [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "font-size": 10,
        color: read("--text"),
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-wrap": "ellipsis",
        "text-max-width": "110px",
        width: "data(size)",
        height: "data(size)",
        "background-color": read("--surface-2"),
        "border-width": 2,
        "border-color": read("--muted"), // visible outline for not-started concepts on --bg
        "transition-property": "opacity, border-width",
        "transition-duration": 150,
      },
    },
    ...(["weak", "developing", "strong"] as const).map((b) => ({
      selector: `node[band = "${b}"]`,
      style: { "background-color": band(b), "border-color": band(b) },
    })),
    { selector: "node.dim", style: { opacity: 0.18 } },
    { selector: "node:selected", style: { "border-width": 4, "border-color": read("--accent") } },
    { selector: "node.path", style: { "border-width": 4, "border-color": read("--accent") } },
    {
      selector: "edge",
      style: {
        width: 1.2,
        "line-color": read("--border"),
        "target-arrow-color": read("--border"),
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.8,
        "curve-style": "bezier",
      },
    },
    {
      selector: 'edge[type = "RELATED_TO"]',
      style: { "line-style": "dashed", "target-arrow-shape": "none" },
    },
    { selector: "edge.dim", style: { opacity: 0.1 } },
    {
      selector: "edge.path",
      style: { width: 3, "line-color": read("--accent"), "target-arrow-color": read("--accent") },
    },
  ] as StylesheetJson;
}

export function elementsFor(graph: MasteryGraph, showRelated: boolean): ElementDefinition[] {
  return [
    ...graph.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.name,
        band: n.band,
        cluster: n.cluster,
        size: 18 + n.difficulty * 6,
      },
    })),
    ...graph.edges
      .filter((e) => showRelated || e.type === "PREREQUISITE_OF")
      .map((e) => ({
        data: {
          id: `${e.source}>${e.target}>${e.type}`,
          source: e.source,
          target: e.target,
          type: e.type,
        },
      })),
  ];
}

function Drawer({ node, onClose }: { node: MapNode; onClose: () => void }) {
  const router = useRouter();
  const create = useCreateQuiz();
  const practise = async () => {
    try {
      const s = await create.mutateAsync({ mode: "concept", concept_id: node.id, count: 8 });
      router.push(`/app/quizzes/${s.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start the quiz.");
    }
  };
  return (
    <aside
      aria-label={`${node.name} details`}
      className="absolute inset-y-0 right-0 z-10 w-[min(22rem,100%)] space-y-4 overflow-y-auto border-l border-border bg-surface p-5 shadow-xl motion-safe:animate-in motion-safe:slide-in-from-right-4"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-xs text-muted">
            {clusterLabel(node.cluster)} · difficulty {node.difficulty}
          </p>
          <h2 className="text-lg font-semibold">{node.name}</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="rounded p-1 text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring"
        >
          <X className="size-4" />
        </button>
      </div>
      {node.mastery !== null ? (
        <MasteryBadge value={node.mastery} />
      ) : (
        <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted">
          Not started
        </span>
      )}
      <p className="text-sm text-muted">{node.description}</p>
      <dl className="grid grid-cols-2 gap-1 text-xs">
        <dt className="text-muted">Answers</dt>
        <dd>{node.attempts}</dd>
        <dt className="text-muted">Last practised</dt>
        <dd>
          {node.last_practiced_at ? new Date(node.last_practiced_at).toLocaleDateString() : "—"}
        </dd>
        <dt className="text-muted">Next review</dt>
        <dd>{node.next_review_at ? new Date(node.next_review_at).toLocaleDateString() : "—"}</dd>
      </dl>
      <div className="flex flex-col gap-2">
        <Link href={`/app/learn/${node.id}`} className={buttonVariants({ variant: "default" })}>
          Learn {node.name}
        </Link>
        <Button variant="outline" onClick={() => void practise()} disabled={create.isPending}>
          <ListChecks aria-hidden className="size-4" /> Practise
        </Button>
        <Link
          href={tutorLink(`Explain ${node.name}.`)}
          className={buttonVariants({ variant: "outline" })}
        >
          <MessageSquare aria-hidden className="size-4" /> Ask the tutor
        </Link>
      </div>
    </aside>
  );
}

/** Full-screen prerequisite DAG coloured by the learner's mastery. */
export function KnowledgeMap() {
  const { data, error, isPending, refetch } = useMasteryGraph();
  const recs = useRecommendations("learn", 1);
  const box = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [hover, setHover] = useState<{ id: string; x: number; y: number } | null>(null);
  const [cluster, setCluster] = useState("all");
  const [showRelated, setShowRelated] = useState(false);
  const [showPath, setShowPath] = useState(false);
  const byId = useMemo(() => new Map((data?.nodes ?? []).map((n) => [n.id, n])), [data]);
  const clusters = useMemo(() => [...new Set((data?.nodes ?? []).map((n) => n.cluster))], [data]);
  const rec = recs.data?.items[0];
  const pathIds = useMemo(() => {
    if (!rec) return [];
    const ids = pathConcepts(rec.path);
    return ids.length ? ids : [rec.concept_id];
  }, [rec]);

  // Build the graph once per data / related toggle.
  useEffect(() => {
    if (!data || !box.current) return;
    let cancelled = false;
    let cy: Core | null = null;
    void (async () => {
      const [{ default: cytoscape }, { default: dagre }] = await Promise.all([
        import("cytoscape"),
        import("cytoscape-dagre"),
      ]);
      if (cancelled || !box.current) return;
      cytoscape.use(dagre);
      cy = cytoscape({
        container: box.current,
        elements: elementsFor(data, showRelated),
        style: mapStyle(cssVar),
        layout: { name: "dagre", rankDir: "TB", nodeSep: 24, rankSep: 70, edgeSep: 8 } as never,
        wheelSensitivity: 0.3,
        minZoom: 0.15,
        maxZoom: 3,
      });
      cy.on("tap", "node", (e: EventObject) => setSelected(e.target.id()));
      cy.on("tap", (e: EventObject) => {
        if (e.target === cy) setSelected(null);
      });
      cy.on("mouseover", "node", (e: EventObject) => {
        const p = e.target.renderedPosition();
        setHover({ id: e.target.id(), x: p.x, y: p.y });
      });
      cy.on("mouseout", "node", () => setHover(null));
      cy.on("pan zoom", () => setHover(null));
      cyRef.current = cy;
    })();
    // Theme changes: recompute colours from the new CSS variables.
    const observer = new MutationObserver(() => cyRef.current?.style(mapStyle(cssVar)));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme", "class"],
    });
    return () => {
      cancelled = true;
      observer.disconnect();
      cy?.destroy();
      cyRef.current = null;
    };
  }, [data, showRelated]);

  // Cluster filter and "show my path" highlighting.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass("dim path");
      if (cluster !== "all") {
        cy.nodes()
          .filter((n) => n.data("cluster") !== cluster)
          .addClass("dim");
        cy.edges()
          .filter((e) => e.source().hasClass("dim") || e.target().hasClass("dim"))
          .addClass("dim");
      }
      if (showPath && pathIds.length) {
        const set = new Set(pathIds);
        cy.nodes()
          .filter((n) => set.has(n.id()))
          .addClass("path");
        cy.edges()
          .filter(
            (e) =>
              set.has(e.source().id()) &&
              set.has(e.target().id()) &&
              e.data("type") === "PREREQUISITE_OF",
          )
          .addClass("path");
      }
    });
    if (showPath && pathIds.length) {
      const set = new Set(pathIds);
      cy.animate(
        { fit: { eles: cy.nodes().filter((n) => set.has(n.id())), padding: 120 } },
        { duration: 200 },
      );
    }
  }, [cluster, showPath, pathIds, data, showRelated]);

  const exportPng = () => {
    const cy = cyRef.current;
    if (!cy) return;
    const uri = cy.png({ full: true, scale: 2, bg: cssVar("--bg") });
    const a = document.createElement("a");
    a.href = uri;
    a.download = "cognexa-knowledge-map.png";
    a.click();
  };

  const counts = useMemo(() => {
    const c = { weak: 0, developing: 0, strong: 0, not_started: 0 };
    for (const n of data?.nodes ?? []) c[n.band] += 1;
    return c;
  }, [data]);

  if (isPending) return <Skeleton className="h-[70vh] w-full" aria-label="Loading knowledge map" />;
  if (error || !data) {
    return (
      <ErrorState
        title="Couldn't load the knowledge map"
        message={error?.message}
        onRetry={() => void refetch()}
      />
    );
  }
  const hovered = hover ? byId.get(hover.id) : undefined;
  const node = selected ? byId.get(selected) : undefined;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Knowledge map"
        description="Every concept, arranged so prerequisites sit above what builds on them, coloured by your mastery."
      />
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2">
          Cluster
          <select
            value={cluster}
            onChange={(e) => setCluster(e.target.value)}
            className="h-8 rounded-lg border border-border bg-surface px-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <option value="all">All clusters</option>
            {clusters.map((c) => (
              <option key={c} value={c}>
                {clusterLabel(c)}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={showRelated}
            onChange={(e) => setShowRelated(e.target.checked)}
            className="size-4 accent-[var(--primary)]"
          />
          Related links
        </label>
        <Button
          variant={showPath ? "default" : "outline"}
          size="sm"
          aria-pressed={showPath}
          disabled={!rec}
          onClick={() => setShowPath((v) => !v)}
        >
          <Route aria-hidden className="size-4" /> Show my path
        </Button>
        <Button variant="outline" size="sm" onClick={exportPng}>
          <Download aria-hidden className="size-4" /> Export PNG
        </Button>
        <ul className="ml-auto flex flex-wrap gap-3 text-xs text-muted" aria-label="Legend">
          {(Object.keys(BAND_VAR) as MapNode["band"][]).map((b) => (
            <li key={b} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className={cn(
                  "size-3 rounded-full border-2",
                  {
                    weak: "border-danger bg-danger",
                    developing: "border-warning bg-warning",
                    strong: "border-success bg-success",
                    not_started: "border-border bg-surface-2",
                  }[b],
                )}
              />
              {BAND_LABEL[b]} ({counts[b]})
            </li>
          ))}
          <li>→ prerequisite of</li>
        </ul>
      </div>
      {showPath && rec && (
        <p className="text-sm text-muted" role="status">
          <span className="font-medium text-text">Your path:</span> {rec.reason}
        </p>
      )}
      <div className="relative h-[70vh] overflow-hidden rounded-2xl border border-border bg-bg">
        <div
          ref={box}
          // Explicit size: Cytoscape sets its own `position` on the container, so absolute
          // insets would collapse it to zero height (BUG-032).
          className="h-full w-full"
          role="img"
          aria-label={`Knowledge map with ${data.nodes.length} concepts: ${counts.strong} strong, ${counts.developing} developing, ${counts.weak} weak, ${counts.not_started} not started`}
        />
        {hovered && hover && (
          <div
            className="pointer-events-none absolute z-20 max-w-60 rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-lg"
            style={{ left: hover.x + 14, top: hover.y + 14 }}
          >
            <p className="font-medium text-text">{hovered.name}</p>
            <p className="text-muted">
              {hovered.mastery !== null
                ? `Mastery ${Math.round(hovered.mastery * 100)}%`
                : "Not started"}{" "}
              · {hovered.attempts} answers
            </p>
            {hovered.last_practiced_at && (
              <p className="text-muted">
                Last practised {new Date(hovered.last_practiced_at).toLocaleDateString()}
              </p>
            )}
          </div>
        )}
        {node && <Drawer node={node} onClose={() => setSelected(null)} />}
      </div>
      <details className="text-sm">
        <summary className="cursor-pointer text-muted">List view</summary>
        <ul className="mt-2 grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
          {[...data.nodes]
            .sort((a, b) => a.order_index - b.order_index)
            .map((n) => (
              <li key={n.id}>
                <button
                  type="button"
                  onClick={() => setSelected(n.id)}
                  className="text-left hover:underline"
                >
                  {n.name}
                </button>{" "}
                <span className="text-xs text-muted">{BAND_LABEL[n.band]}</span>
              </li>
            ))}
        </ul>
      </details>
    </div>
  );
}
