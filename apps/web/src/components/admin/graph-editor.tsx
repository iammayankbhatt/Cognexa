"use client";

import type { Core, ElementDefinition, EventObject, StylesheetJson } from "cytoscape";
import { Download, GitBranchPlus, Plus, Sparkles, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Field, fieldClass, splitList } from "@/components/admin/form-bits";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  checkEdge,
  useAdminGraph,
  useGraphMutations,
  type AdminConcept,
  type AdminEdge,
  type AdminGraph,
  type ConceptInput,
  type CycleCheck,
  type EdgeType,
} from "@/lib/admin";
import { apiBlob, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888888";
}

function editorStyle(read: (n: string) => string): StylesheetJson {
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
        "text-max-width": "120px",
        width: 22,
        height: 22,
        "background-color": read("--surface-2"),
        "border-width": 2,
        "border-color": read("--muted"),
      },
    },
    { selector: "node:selected", style: { "border-width": 4, "border-color": read("--accent") } },
    { selector: "node.near", style: { "border-color": read("--primary") } },
    { selector: "node.dim, edge.dim", style: { opacity: 0.2 } },
    {
      selector: "edge",
      style: {
        width: 1.3,
        "line-color": read("--border"),
        "target-arrow-color": read("--border"),
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.8,
        "curve-style": "bezier",
      },
    },
    {
      selector: 'edge[kind = "llm"]',
      style: {
        "line-style": "dashed",
        "line-color": read("--accent"),
        "target-arrow-color": read("--accent"),
      },
    },
    {
      selector: 'edge[type = "RELATED_TO"]',
      style: { "line-style": "dotted", "target-arrow-shape": "none" },
    },
  ];
}

function elements(g: AdminGraph): ElementDefinition[] {
  return [
    ...g.concepts.map((c) => ({ data: { id: c.id, label: c.name, cluster: c.cluster } })),
    ...g.edges.map((e) => ({
      data: {
        id: `${e.type}:${e.source}->${e.target}`,
        source: e.source,
        target: e.target,
        type: e.type,
        kind: e.source_kind,
      },
    })),
  ];
}

const EMPTY: ConceptInput = {
  name: "",
  cluster: "",
  difficulty: 2,
  description: "",
  aliases: [],
  keywords: [],
};

function ConceptForm({
  initial,
  withId,
  clusters,
  busy,
  onSubmit,
  submitLabel,
}: {
  initial: ConceptInput & { id?: string };
  withId: boolean;
  clusters: string[];
  busy: boolean;
  onSubmit: (v: ConceptInput & { id: string }) => void;
  submitLabel: string;
}) {
  const [id, setId] = useState(initial.id ?? "");
  const [name, setName] = useState(initial.name);
  const [cluster, setCluster] = useState(initial.cluster);
  const [difficulty, setDifficulty] = useState(initial.difficulty);
  const [description, setDescription] = useState(initial.description);
  const [aliases, setAliases] = useState(initial.aliases.join(", "));
  const [keywords, setKeywords] = useState(initial.keywords.join(", "));
  const idError =
    withId && id && !/^[a-z][a-z0-9_]{1,63}$/.test(id) ? "Use snake_case: a-z, 0-9, _" : null;
  const descError =
    description && description.trim().length < 10 ? "At least 10 characters." : null;
  const valid =
    (!withId || (id && !idError)) &&
    name.trim() &&
    /^[a-z][a-z0-9_]*$/.test(cluster) &&
    description.trim().length >= 10;
  const prefix = withId ? "new" : "edit";
  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (!valid) return;
        onSubmit({
          id: initial.id ?? id,
          name: name.trim(),
          cluster,
          difficulty,
          description: description.trim(),
          aliases: splitList(aliases),
          keywords: splitList(keywords),
        });
      }}
    >
      {withId && (
        <Field
          label="Id"
          htmlFor={`${prefix}-id`}
          error={idError}
          hint="Permanent; used in URLs and the YAML file."
        >
          <input
            id={`${prefix}-id`}
            className={fieldClass}
            value={id}
            onChange={(e) => setId(e.target.value.trim())}
            placeholder="e.g. deque"
          />
        </Field>
      )}
      <Field label="Name" htmlFor={`${prefix}-name`}>
        <input
          id={`${prefix}-name`}
          className={fieldClass}
          value={name}
          maxLength={200}
          onChange={(e) => setName(e.target.value)}
        />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Cluster" htmlFor={`${prefix}-cluster`}>
          <input
            id={`${prefix}-cluster`}
            list="cluster-options"
            className={fieldClass}
            value={cluster}
            onChange={(e) => setCluster(e.target.value.trim())}
          />
          <datalist id="cluster-options">
            {clusters.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </Field>
        <Field label="Difficulty (1-5)" htmlFor={`${prefix}-difficulty`}>
          <input
            id={`${prefix}-difficulty`}
            type="number"
            min={1}
            max={5}
            className={fieldClass}
            value={difficulty}
            onChange={(e) => setDifficulty(Math.min(5, Math.max(1, Number(e.target.value) || 1)))}
          />
        </Field>
      </div>
      <Field label="Description" htmlFor={`${prefix}-description`} error={descError}>
        <textarea
          id={`${prefix}-description`}
          rows={3}
          maxLength={600}
          className={cn(fieldClass, "resize-y")}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </Field>
      <Field
        label="Aliases"
        htmlFor={`${prefix}-aliases`}
        hint="Comma-separated. Drive question classification."
      >
        <input
          id={`${prefix}-aliases`}
          className={fieldClass}
          value={aliases}
          onChange={(e) => setAliases(e.target.value)}
        />
      </Field>
      <Field
        label="Keywords"
        htmlFor={`${prefix}-keywords`}
        hint="Comma-separated, e.g. error messages students type."
      >
        <input
          id={`${prefix}-keywords`}
          className={fieldClass}
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
        />
      </Field>
      <Button type="submit" disabled={!valid || busy}>
        {busy ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}

type Direction = "prereq_of_this" | "this_prereq_of" | "related";

function AddEdgeForm({ concept, graph }: { concept: AdminConcept; graph: AdminGraph }) {
  const { addEdge } = useGraphMutations();
  const [direction, setDirection] = useState<Direction>("prereq_of_this");
  const [other, setOther] = useState("");
  const [rationale, setRationale] = useState("");
  // The cycle check is keyed by the edge it was made for, so a stale answer is never shown.
  const [checked, setChecked] = useState<{ key: string; result: CycleCheck } | null>(null);
  const linked = useMemo(() => {
    const s = new Set<string>();
    for (const e of graph.edges) {
      if (e.source === concept.id) s.add(e.target);
      if (e.target === concept.id) s.add(e.source);
    }
    return s;
  }, [graph, concept.id]);
  const options = graph.concepts.filter((c) => c.id !== concept.id && !linked.has(c.id));
  const source = direction === "this_prereq_of" ? concept.id : other;
  const target = direction === "this_prereq_of" ? other : concept.id;

  const edgeKey = `${source}->${target}`;
  const wantsCheck = Boolean(other) && direction !== "related";
  useEffect(() => {
    if (!wantsCheck) return;
    let live = true;
    checkEdge(source, target)
      .then((result) => {
        if (live) setChecked({ key: edgeKey, result });
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [wantsCheck, source, target, edgeKey]);
  const check = wantsCheck && checked?.key === edgeKey ? checked.result : null;

  const type: EdgeType = direction === "related" ? "RELATED_TO" : "PREREQUISITE_OF";
  const blocked = check !== null && !check.ok;
  return (
    <form
      className="space-y-3 rounded-xl border border-border bg-surface-2/40 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (!other || blocked) return;
        addEdge.mutate(
          { source, target, type, rationale: rationale.trim() || null },
          {
            onSuccess: () => {
              toast.success("Edge added.");
              setOther("");
              setRationale("");
            },
            onError: (err) =>
              toast.error(err instanceof ApiError ? err.message : "Could not add the edge."),
          },
        );
      }}
    >
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <GitBranchPlus aria-hidden className="size-4 text-accent" /> Add an edge
      </h3>
      <Field label="Relation" htmlFor="edge-direction">
        <select
          id="edge-direction"
          className={fieldClass}
          value={direction}
          onChange={(e) => setDirection(e.target.value as Direction)}
        >
          <option value="prereq_of_this">… must be learned before {concept.name}</option>
          <option value="this_prereq_of">{concept.name} must be learned before …</option>
          <option value="related">… is related to {concept.name}</option>
        </select>
      </Field>
      <Field label="Concept" htmlFor="edge-other">
        <select
          id="edge-other"
          className={fieldClass}
          value={other}
          onChange={(e) => setOther(e.target.value)}
        >
          <option value="">Choose a concept</option>
          {options.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </Field>
      {blocked && (
        <div
          role="alert"
          className="rounded-lg border border-danger/60 bg-danger/10 p-3 text-sm text-text"
        >
          <p className="font-medium">This edge would create a cycle.</p>
          <p className="mt-1 text-muted">{check.message}</p>
          {check.path.length > 0 && (
            <p className="mt-2 font-mono text-xs break-words">
              {check.path.join(" → ")} → {check.path[0]}
            </p>
          )}
        </div>
      )}
      <Field
        label="Rationale"
        htmlFor="edge-rationale"
        hint="Why? Shown to reviewers and kept in the audit log."
      >
        <input
          id="edge-rationale"
          className={fieldClass}
          maxLength={1000}
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
        />
      </Field>
      <Button type="submit" size="sm" disabled={!other || blocked || addEdge.isPending}>
        Add edge
      </Button>
    </form>
  );
}

function EdgeRow({ edge, graph, focus }: { edge: AdminEdge; graph: AdminGraph; focus: string }) {
  const { removeEdge } = useGraphMutations();
  const name = (id: string) => graph.concepts.find((c) => c.id === id)?.name ?? id;
  const other = edge.source === focus ? edge.target : edge.source;
  return (
    <li className="flex items-start gap-2 rounded-lg border border-border px-3 py-2 text-sm">
      <div className="min-w-0 flex-1">
        <p className="font-medium">{name(other)}</p>
        <p className="text-xs text-muted">
          {edge.source_kind === "llm" ? "LLM proposal, approved" : "Added by a person"}
          {edge.rationale ? ` · ${edge.rationale}` : ""}
        </p>
      </div>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={`Remove edge to ${name(other)}`}
        disabled={removeEdge.isPending}
        onClick={() => {
          const why = window.prompt(
            `Remove this edge (${name(edge.source)} → ${name(edge.target)})? Reason (optional):`,
          );
          if (why === null) return;
          removeEdge.mutate(
            {
              source: edge.source,
              target: edge.target,
              type: edge.type,
              rationale: why || undefined,
            },
            {
              onSuccess: () => toast.success("Edge removed."),
              onError: (e) =>
                toast.error(e instanceof ApiError ? e.message : "Could not remove it."),
            },
          );
        }}
      >
        <Trash2 aria-hidden className="size-4" />
      </Button>
    </li>
  );
}

function ConceptPanel({
  concept,
  graph,
  clusters,
  onClose,
}: {
  concept: AdminConcept;
  graph: AdminGraph;
  clusters: string[];
  onClose: () => void;
}) {
  const { updateConcept, suggest } = useGraphMutations();
  const prereqs = graph.edges.filter(
    (e) => e.type === "PREREQUISITE_OF" && e.target === concept.id,
  );
  const dependents = graph.edges.filter(
    (e) => e.type === "PREREQUISITE_OF" && e.source === concept.id,
  );
  const related = graph.edges.filter(
    (e) => e.type === "RELATED_TO" && (e.source === concept.id || e.target === concept.id),
  );
  const groups: [string, AdminEdge[]][] = [
    ["Prerequisites (learn before)", prereqs],
    ["Dependents (learn after)", dependents],
    ["Related", related],
  ];
  return (
    <aside
      aria-label={`Edit ${concept.name}`}
      className="space-y-6 rounded-2xl border border-border bg-surface p-5"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-mono text-xs text-muted">{concept.id}</p>
          <h2 className="text-lg font-semibold">{concept.name}</h2>
        </div>
        <Button variant="ghost" size="icon-sm" aria-label="Close panel" onClick={onClose}>
          <X aria-hidden className="size-4" />
        </Button>
      </div>
      <ConceptForm
        key={concept.id}
        initial={{ ...concept }}
        withId={false}
        clusters={clusters}
        busy={updateConcept.isPending}
        submitLabel="Save concept"
        onSubmit={(v) =>
          updateConcept.mutate(v, {
            onSuccess: () => toast.success("Concept saved."),
            onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save."),
          })
        }
      />
      {groups.map(([title, edges]) => (
        <section key={title} className="space-y-2">
          <h3 className="text-sm font-semibold">
            {title} <span className="font-normal text-muted">({edges.length})</span>
          </h3>
          {edges.length === 0 ? (
            <p className="text-sm text-muted">None.</p>
          ) : (
            <ul className="space-y-2">
              {edges.map((e) => (
                <EdgeRow
                  key={`${e.type}${e.source}${e.target}`}
                  edge={e}
                  graph={graph}
                  focus={concept.id}
                />
              ))}
            </ul>
          )}
        </section>
      ))}
      <AddEdgeForm key={`add-${concept.id}`} concept={concept} graph={graph} />
      <div className="space-y-2 border-t border-border pt-4">
        <Button
          variant="outline"
          disabled={suggest.isPending}
          onClick={() =>
            suggest.mutate(concept.id, {
              onSuccess: (r) =>
                toast.success(
                  r.created.length
                    ? `${r.created.length} edge proposal(s) added to the review queue.`
                    : "No new edges suggested.",
                ),
              onError: (e) => toast.error(e instanceof ApiError ? e.message : "Suggestion failed."),
            })
          }
        >
          <Sparkles aria-hidden className="size-4" />
          {suggest.isPending ? "Asking the model…" : "Suggest missing edges"}
        </Button>
        <p className="text-xs text-muted">
          The model proposes; nothing changes until a reviewer approves it in{" "}
          <Link href="/admin/proposals" className="text-accent underline-offset-4 hover:underline">
            Proposals
          </Link>
          . Uses one AI request.
        </p>
      </div>
    </aside>
  );
}

function GraphCanvas({
  graph,
  selected,
  onSelect,
}: {
  graph: AdminGraph;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  useEffect(() => {
    if (!box.current) return;
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
        elements: elements(graph),
        style: editorStyle(cssVar),
        layout: { name: "dagre", rankDir: "TB", nodeSep: 22, rankSep: 64 } as never,
        wheelSensitivity: 0.3,
        minZoom: 0.15,
        maxZoom: 3,
      });
      cy.on("tap", "node", (e: EventObject) => onSelect(e.target.id()));
      cy.on("tap", (e: EventObject) => {
        if (e.target === cy) onSelect(null);
      });
      cyRef.current = cy;
    })();
    const observer = new MutationObserver(() => cyRef.current?.style(editorStyle(cssVar)));
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
    // onSelect is a state setter wrapper; rebuilding on graph changes only
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass("dim near");
      cy.nodes().unselect();
      if (!selected) return;
      const node = cy.getElementById(selected);
      if (node.empty()) return;
      node.select();
      const hood = node.closedNeighborhood();
      hood.nodes().not(node).addClass("near");
      cy.elements().not(hood).addClass("dim");
    });
  }, [selected, graph]);

  return (
    <div className="relative h-[70vh] min-h-[420px] overflow-hidden rounded-2xl border border-border bg-bg">
      <div
        ref={box}
        className="h-full w-full"
        role="img"
        aria-label="Concept graph editor: click a concept to edit it"
      />
      <div className="pointer-events-none absolute bottom-3 left-3 flex flex-wrap gap-3 rounded-lg bg-surface/90 px-3 py-2 text-xs text-muted">
        <span>→ prerequisite</span>
        <span className="text-accent">⇢ approved LLM proposal</span>
        <span>⋯ related</span>
      </div>
    </div>
  );
}

function GraphTable({ graph, onSelect }: { graph: AdminGraph; onSelect: (id: string) => void }) {
  const [q, setQ] = useState("");
  const counts = useMemo(() => {
    const m = new Map<string, { pre: number; dep: number }>();
    for (const c of graph.concepts) m.set(c.id, { pre: 0, dep: 0 });
    for (const e of graph.edges) {
      if (e.type !== "PREREQUISITE_OF") continue;
      m.get(e.target)!.pre += 1;
      m.get(e.source)!.dep += 1;
    }
    return m;
  }, [graph]);
  const rows = graph.concepts.filter(
    (c) => !q || `${c.id} ${c.name} ${c.cluster}`.toLowerCase().includes(q.toLowerCase()),
  );
  return (
    <div className="space-y-3">
      <input
        aria-label="Filter concepts"
        placeholder="Filter by name, id or cluster"
        className={cn(fieldClass, "max-w-sm")}
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div className="overflow-x-auto rounded-2xl border border-border">
        <table className="w-full text-sm">
          <thead className="bg-surface-2 text-left text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">#</th>
              <th className="px-3 py-2 font-medium">Concept</th>
              <th className="px-3 py-2 font-medium">Cluster</th>
              <th className="px-3 py-2 text-right font-medium">Difficulty</th>
              <th className="px-3 py-2 text-right font-medium">Prereqs</th>
              <th className="px-3 py-2 text-right font-medium">Dependents</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className="border-t border-border hover:bg-surface-2/50">
                <td className="px-3 py-2 text-muted tabular-nums">{c.order_index}</td>
                <td className="px-3 py-2">
                  <button
                    type="button"
                    className="text-left font-medium text-text hover:text-accent"
                    onClick={() => onSelect(c.id)}
                  >
                    {c.name}
                  </button>
                  <div className="font-mono text-xs text-muted">{c.id}</div>
                </td>
                <td className="px-3 py-2">{c.cluster}</td>
                <td className="px-3 py-2 text-right tabular-nums">{c.difficulty}</td>
                <td className="px-3 py-2 text-right tabular-nums">{counts.get(c.id)?.pre ?? 0}</td>
                <td className="px-3 py-2 text-right tabular-nums">{counts.get(c.id)?.dep ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Reviewer graph editor: concepts, prerequisite / related edges, cycle-safe edits, YAML export. */
export function GraphEditor() {
  const { data, isPending, error, refetch } = useAdminGraph();
  const { createConcept } = useGraphMutations();
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const clusters = useMemo(
    () => [...new Set((data?.concepts ?? []).map((c) => c.cluster))],
    [data],
  );
  const concept = data?.concepts.find((c) => c.id === selected) ?? null;

  const exportYaml = async () => {
    try {
      const blob = await apiBlob("/admin/graph/export.yaml");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `concepts-${data?.subject_id ?? "dsa"}.yaml`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Exported. Replace concepts.yaml with it and run validate_graph.py.");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Export failed.");
    }
  };

  if (isPending) return <Skeleton className="h-[70vh] w-full" aria-label="Loading graph" />;
  if (error || !data) return <ErrorState message={error?.message} onRetry={() => void refetch()} />;
  const prereqCount = data.edges.filter((e) => e.type === "PREREQUISITE_OF").length;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reviewer"
        title="Graph editor"
        description={`${data.concepts.length} concepts, ${prereqCount} prerequisite edges. The prerequisite graph must stay acyclic; edits that would create a cycle are refused.`}
        actions={
          <>
            <Button variant="outline" onClick={() => void exportYaml()}>
              <Download aria-hidden className="size-4" /> Export concepts.yaml
            </Button>
            <Button onClick={() => setCreating(true)}>
              <Plus aria-hidden className="size-4" /> New concept
            </Button>
          </>
        }
      />
      <Tabs defaultValue="graph">
        <TabsList>
          <TabsTrigger value="graph">Graph</TabsTrigger>
          <TabsTrigger value="table">Table</TabsTrigger>
        </TabsList>
        <div className="mt-4 grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
          <div className="min-w-0">
            <TabsContent value="graph">
              <GraphCanvas graph={data} selected={selected} onSelect={setSelected} />
            </TabsContent>
            <TabsContent value="table">
              <GraphTable graph={data} onSelect={setSelected} />
            </TabsContent>
          </div>
          {concept ? (
            <ConceptPanel
              concept={concept}
              graph={data}
              clusters={clusters}
              onClose={() => setSelected(null)}
            />
          ) : (
            <div className="hidden rounded-2xl border border-dashed border-border p-6 text-sm text-muted xl:block">
              Select a concept to edit its fields and edges, or ask the model to suggest missing
              edges.
            </div>
          )}
        </div>
      </Tabs>
      <Dialog open={creating} onOpenChange={setCreating}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>New concept</DialogTitle>
            <DialogDescription>
              Add it, then connect it with prerequisite edges so the tutor can reach it.
            </DialogDescription>
          </DialogHeader>
          <ConceptForm
            initial={EMPTY}
            withId
            clusters={clusters}
            busy={createConcept.isPending}
            submitLabel="Create concept"
            onSubmit={(v) =>
              createConcept.mutate(v, {
                onSuccess: (c) => {
                  toast.success("Concept created.");
                  setCreating(false);
                  setSelected(c.id);
                },
                onError: (e) =>
                  toast.error(e instanceof ApiError ? e.message : "Could not create it."),
              })
            }
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreating(false)}>
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
