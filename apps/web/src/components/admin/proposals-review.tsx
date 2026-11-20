"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Check, FileUp, Inbox, Loader2, Sparkles, X } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { confidenceLabel, Field, fieldClass } from "@/components/admin/form-bits";
import { Markdown } from "@/components/tutor/markdown";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAdminGraph,
  useIngestDocuments,
  useProposal,
  useProposalDecisions,
  useProposals,
  useProposalStats,
  type AdminConcept,
  type Proposal,
  type ProposalDetail,
  type ProposalFilters,
  type ProposalType,
} from "@/lib/admin";
import { api, apiUpload, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const TYPE_LABEL: Record<ProposalType, string> = {
  add_edge: "Add edge",
  remove_edge: "Remove edge",
  tag_chunk: "Tag section",
  new_concept: "New concept",
};
const CHUNK_KINDS = [
  "overview",
  "intuition",
  "mechanism",
  "example",
  "code",
  "complexity",
  "pitfalls",
];

function str(v: unknown): string {
  return typeof v === "string" ? v : "";
}

function summary(p: Proposal): string {
  const n = (id: unknown) => p.names?.[str(id)] ?? str(id);
  const pl = p.payload;
  switch (p.type) {
    case "add_edge":
    case "remove_edge":
      return pl.edge_type === "RELATED_TO"
        ? `${n(pl.source)} ↔ ${n(pl.target)}`
        : `${n(pl.source)} → ${n(pl.target)}`;
    case "tag_chunk":
      return `${str(pl.heading) || "Section"} → ${n(pl.concept_id)}`;
    case "new_concept":
      return str((pl.concept as Record<string, unknown> | undefined)?.name) || "New concept";
  }
}

function UploadCard({ onShow }: { onShow: (documentId: string) => void }) {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const docs = useIngestDocuments();
  const upload = async (file: File) => {
    if (file.size > 10 * 1024 * 1024) {
      toast.error("Files must be 10 MB or smaller.");
      return;
    }
    setBusy(true);
    try {
      await apiUpload(`/admin/ingest?filename=${encodeURIComponent(file.name)}`, file);
      toast.success("Uploaded. The model is tagging its sections…");
      void qc.invalidateQueries({ queryKey: ["admin", "ingest"] });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };
  return (
    <section
      className="space-y-4 rounded-2xl border border-border bg-surface p-5"
      aria-labelledby="ingest-title"
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <h2 id="ingest-title" className="flex items-center gap-2 text-base font-semibold">
            <FileUp aria-hidden className="size-4 text-accent" /> Ingest lecture notes
          </h2>
          <p className="text-sm text-muted">
            PDF (with a text layer), Markdown or text, up to 10 MB. Each section becomes a proposal:
            which concept it teaches, or a new concept. Uses one AI request per four sections.
          </p>
        </div>
        <input
          ref={input}
          type="file"
          accept=".pdf,.md,.markdown,.txt"
          className="sr-only"
          id="ingest-file"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
          }}
        />
        <Button onClick={() => input.current?.click()} disabled={busy}>
          {busy ? (
            <Loader2 aria-hidden className="size-4 animate-spin" />
          ) : (
            <FileUp aria-hidden className="size-4" />
          )}
          Upload a file
        </Button>
      </div>
      {docs.data && docs.data.items.length > 0 && (
        <ul className="divide-y divide-border rounded-xl border border-border text-sm">
          {docs.data.items.slice(0, 5).map((d) => (
            <li key={d.id} className="flex flex-wrap items-center gap-3 px-3 py-2">
              <span className="min-w-0 flex-1 truncate font-medium">{d.filename}</span>
              <span className="text-xs text-muted">
                {d.pages ? `${d.pages} pages · ` : ""}
                {d.sections} sections · {d.proposals} proposals
              </span>
              {d.status === "processing" ? (
                <Badge variant="outline">
                  <Loader2 aria-hidden className="animate-spin" /> tagging
                </Badge>
              ) : d.status === "failed" ? (
                <Badge variant="destructive">failed</Badge>
              ) : (
                <Button variant="ghost" size="xs" onClick={() => onShow(d.id)}>
                  Show proposals
                </Button>
              )}
              {d.error && <p className="w-full text-xs text-warning">{d.error}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Preview({ detail }: { detail: ProposalDetail }) {
  const { concepts, edges } = detail.preview;
  if (!concepts.length) return null;
  const name = (id: string) => concepts.find((c) => c.id === id)?.name ?? id;
  const prereq = edges.filter((e) => e.type === "PREREQUISITE_OF");
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold">Affected part of the graph today</h3>
      {prereq.length === 0 ? (
        <p className="text-sm text-muted">These concepts have no prerequisite edges yet.</p>
      ) : (
        <ul className="grid gap-1 text-sm sm:grid-cols-2">
          {prereq.slice(0, 16).map((e) => (
            <li
              key={`${e.source}>${e.target}`}
              className="truncate rounded-md bg-surface-2/60 px-2 py-1"
            >
              {name(e.source)} <span className="text-muted">→</span> {name(e.target)}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function EditFields({
  detail,
  concepts,
  edits,
  setEdits,
}: {
  detail: ProposalDetail;
  concepts: AdminConcept[];
  edits: Record<string, unknown>;
  setEdits: (e: Record<string, unknown>) => void;
}) {
  const p = { ...detail.payload, ...edits };
  const set = (k: string, v: unknown) => setEdits({ ...edits, [k]: v });
  if (detail.type === "tag_chunk") {
    return (
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Concept" htmlFor="ed-concept">
          <select
            id="ed-concept"
            className={fieldClass}
            value={str(p.concept_id)}
            onChange={(e) => set("concept_id", e.target.value)}
          >
            {concepts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Kind" htmlFor="ed-kind">
          <select
            id="ed-kind"
            className={fieldClass}
            value={str(p.kind)}
            onChange={(e) => set("kind", e.target.value)}
          >
            {CHUNK_KINDS.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </Field>
        <Field label="Heading" htmlFor="ed-heading" className="sm:col-span-2">
          <input
            id="ed-heading"
            className={fieldClass}
            value={str(p.heading)}
            onChange={(e) => set("heading", e.target.value)}
          />
        </Field>
        <Field label="Text" htmlFor="ed-text" className="sm:col-span-2">
          <textarea
            id="ed-text"
            rows={8}
            className={cn(fieldClass, "font-mono text-xs")}
            value={str(p.text)}
            onChange={(e) => set("text", e.target.value)}
          />
        </Field>
      </div>
    );
  }
  if (detail.type === "add_edge" || detail.type === "remove_edge") {
    return (
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setEdits({ ...edits, source: p.target, target: p.source })}
        >
          Swap direction
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            set("edge_type", p.edge_type === "RELATED_TO" ? "PREREQUISITE_OF" : "RELATED_TO")
          }
        >
          Make it {p.edge_type === "RELATED_TO" ? "a prerequisite" : "related"}
        </Button>
      </div>
    );
  }
  const c = {
    ...(detail.payload.concept as Record<string, unknown>),
    ...((edits.concept as Record<string, unknown>) ?? {}),
  };
  const setC = (k: string, v: unknown) =>
    setEdits({
      ...edits,
      concept: { ...((edits.concept as Record<string, unknown>) ?? {}), [k]: v },
    });
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Id" htmlFor="ed-cid">
        <input
          id="ed-cid"
          className={fieldClass}
          value={str(c.id)}
          onChange={(e) => setC("id", e.target.value.trim())}
        />
      </Field>
      <Field label="Name" htmlFor="ed-cname">
        <input
          id="ed-cname"
          className={fieldClass}
          value={str(c.name)}
          onChange={(e) => setC("name", e.target.value)}
        />
      </Field>
      <Field label="Cluster" htmlFor="ed-ccluster">
        <input
          id="ed-ccluster"
          className={fieldClass}
          value={str(c.cluster)}
          onChange={(e) => setC("cluster", e.target.value.trim())}
        />
      </Field>
      <Field label="Description" htmlFor="ed-cdesc" className="sm:col-span-2">
        <textarea
          id="ed-cdesc"
          rows={2}
          className={fieldClass}
          value={str(c.description)}
          onChange={(e) => setC("description", e.target.value)}
        />
      </Field>
    </div>
  );
}

function DetailPane({ id, concepts }: { id: string; concepts: AdminConcept[] }) {
  const { data, isPending, error } = useProposal(id);
  const { approve, reject } = useProposalDecisions();
  const [note, setNote] = useState("");
  const [editing, setEditing] = useState(false);
  const [edits, setEdits] = useState<Record<string, unknown>>({});
  if (isPending) return <Skeleton className="h-96" aria-label="Loading proposal" />;
  if (error || !data) return <ErrorState message={error?.message} />;
  const pl = data.payload;
  const name = (v: unknown) =>
    data.names?.[str(v)] ?? concepts.find((c) => c.id === v)?.name ?? str(v);
  const pending = data.status === "pending";
  const decide = (kind: "approve" | "reject") => {
    const opts = {
      onSuccess: () => toast.success(kind === "approve" ? "Approved and applied." : "Rejected."),
      onError: (e: Error) => toast.error(e instanceof ApiError ? e.message : "Failed."),
    };
    if (kind === "approve") {
      approve.mutate(
        { id, note, edits: editing && Object.keys(edits).length ? edits : undefined },
        opts,
      );
    } else {
      reject.mutate({ id, note }, opts);
    }
  };
  return (
    <article
      className="space-y-5 rounded-2xl border border-border bg-surface p-5"
      aria-label="Proposal detail"
    >
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline">{TYPE_LABEL[data.type]}</Badge>
          <Badge variant="secondary">confidence {confidenceLabel(data.confidence)}</Badge>
          <Badge variant={data.status === "rejected" ? "destructive" : "outline"}>
            {data.status}
          </Badge>
          {Boolean(pl.document_name) && (
            <span className="text-xs text-muted">from {str(pl.document_name)}</span>
          )}
        </div>
        <h2 className="text-lg font-semibold">{summary({ ...data, names: data.names })}</h2>
      </header>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="space-y-2">
          <h3 className="text-sm font-semibold">Proposal</h3>
          {(data.type === "add_edge" || data.type === "remove_edge") && (
            <p className="text-sm">
              {pl.edge_type === "RELATED_TO" ? (
                <>
                  <strong>{name(pl.source)}</strong> is related to{" "}
                  <strong>{name(pl.target)}</strong>
                </>
              ) : (
                <>
                  <strong>{name(pl.source)}</strong> must be learned before{" "}
                  <strong>{name(pl.target)}</strong>
                </>
              )}
              {data.type === "remove_edge" && " (remove)"}
            </p>
          )}
          {data.type === "tag_chunk" && (
            <div className="max-h-80 overflow-y-auto rounded-lg border border-border bg-bg p-3 text-sm">
              <p className="mb-2 text-xs text-muted">
                {str(pl.kind)} chunk for{" "}
                <strong className="text-text">{name(pl.concept_id)}</strong>
              </p>
              <Markdown text={str(pl.text)} />
            </div>
          )}
          {data.type === "new_concept" && (
            <div className="space-y-1 text-sm">
              <p>
                <strong>{str((pl.concept as Record<string, unknown>)?.name)}</strong>{" "}
                <span className="font-mono text-xs text-muted">
                  {str((pl.concept as Record<string, unknown>)?.id)}
                </span>
              </p>
              <p className="text-muted">
                {str((pl.concept as Record<string, unknown>)?.description)}
              </p>
              {Array.isArray(pl.prerequisites) && pl.prerequisites.length > 0 && (
                <p className="text-xs">
                  Prerequisites: {(pl.prerequisites as string[]).map(name).join(", ")}
                </p>
              )}
            </div>
          )}
        </section>
        <section className="space-y-2">
          <h3 className="text-sm font-semibold">Model&apos;s rationale</h3>
          <p className="text-sm text-muted">{data.rationale ?? "No rationale given."}</p>
          {data.cycle && (
            <div
              role="alert"
              className="rounded-lg border border-danger/60 bg-danger/10 p-3 text-sm"
            >
              <p className="font-medium">Approving would create a cycle.</p>
              <p className="mt-1 font-mono text-xs break-words">{data.cycle.path.join(" → ")}</p>
            </div>
          )}
        </section>
      </div>
      <Preview detail={data} />
      {pending ? (
        <div className="space-y-3 border-t border-border pt-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={editing}
              onChange={(e) => setEditing(e.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
            Edit before approving
          </label>
          {editing && (
            <EditFields detail={data} concepts={concepts} edits={edits} setEdits={setEdits} />
          )}
          <Field label="Note (optional)" htmlFor="decision-note">
            <input
              id="decision-note"
              className={fieldClass}
              maxLength={1000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => decide("approve")}
              disabled={approve.isPending || Boolean(data.cycle && !editing)}
            >
              <Check aria-hidden className="size-4" /> {editing ? "Approve with edits" : "Approve"}
            </Button>
            <Button variant="outline" onClick={() => decide("reject")} disabled={reject.isPending}>
              <X aria-hidden className="size-4" /> Reject
            </Button>
          </div>
        </div>
      ) : (
        <p className="border-t border-border pt-4 text-sm text-muted">
          {data.status === "approved" ? "Approved" : "Rejected"}
          {data.decided_at ? ` on ${new Date(data.decided_at).toLocaleString()}` : ""}
          {data.note ? `: ${data.note}` : "."}
        </p>
      )}
    </article>
  );
}

function BulkBar({ filters }: { filters: ProposalFilters }) {
  const { bulk } = useProposalDecisions();
  const [threshold, setThreshold] = useState(0.85);
  const run = async () => {
    const q = new URLSearchParams({ min_confidence: String(threshold) });
    if (filters.type) q.set("type", filters.type);
    if (filters.documentId) q.set("document_id", filters.documentId);
    const { matching } = await api<{ matching: number }>(`/admin/proposals-count?${q}`);
    if (matching === 0) {
      toast.message("No pending proposals at or above that confidence.");
      return;
    }
    const scope = filters.type ? TYPE_LABEL[filters.type].toLowerCase() : "all types";
    if (
      !window.confirm(
        `Approve ${matching} pending proposal(s) (${scope}) with confidence ≥ ${Math.round(threshold * 100)}%? Each is applied to the graph.`,
      )
    )
      return;
    bulk.mutate(
      {
        min_confidence: threshold,
        type: filters.type || null,
        document_id: filters.documentId || null,
        expected_count: matching,
      },
      {
        onSuccess: (r) =>
          r.failed.length
            ? toast.warning(
                `${r.approved.length} approved, ${r.failed.length} failed (e.g. ${r.failed[0].message})`,
              )
            : toast.success(`${r.approved.length} approved.`),
        onError: (e) => toast.error(e instanceof ApiError ? e.message : "Bulk approval failed."),
      },
    );
  };
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-2/40 px-4 py-3 text-sm">
      <label htmlFor="bulk-threshold" className="font-medium">
        Bulk approve at ≥ {Math.round(threshold * 100)}%
      </label>
      <input
        id="bulk-threshold"
        type="range"
        min={0.5}
        max={1}
        step={0.05}
        value={threshold}
        onChange={(e) => setThreshold(Number(e.target.value))}
        className="w-40 accent-[var(--primary)]"
      />
      <Button size="sm" variant="outline" onClick={() => void run()} disabled={bulk.isPending}>
        Review count and approve
      </Button>
    </div>
  );
}

/** Review queue for LLM proposals (report Gap I: the model proposes, a human verifies). */
export function ProposalsReview() {
  const graph = useAdminGraph();
  const stats = useProposalStats();
  const [filters, setFilters] = useState<ProposalFilters>({
    status: "pending",
    type: "",
    minConfidence: 0,
    documentId: "",
  });
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const list = useProposals(filters, page);
  const set = (f: Partial<ProposalFilters>) => {
    setFilters({ ...filters, ...f });
    setPage(1);
    setSelected(null);
  };
  const total = stats.data?.total;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reviewer"
        title="Proposals"
        description="Edges and content suggested by the model. Nothing reaches students until a reviewer approves it."
        actions={
          total && (
            <p className="text-sm text-muted">
              Accepted after review:{" "}
              <strong className="text-text">
                {total.acceptance_rate === null
                  ? "—"
                  : `${Math.round(total.acceptance_rate * 100)}%`}
              </strong>{" "}
              ({total.approved} approved, {total.rejected} rejected
              {stats.data?.approved_after_edit
                ? `, ${stats.data.approved_after_edit} edited first`
                : ""}
              )
            </p>
          )
        }
      />
      <UploadCard onShow={(documentId) => set({ documentId, status: "pending" })} />
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Status" htmlFor="f-status" className="w-36">
          <select
            id="f-status"
            className={fieldClass}
            value={filters.status}
            onChange={(e) => set({ status: e.target.value as ProposalFilters["status"] })}
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </Field>
        <Field label="Type" htmlFor="f-type" className="w-40">
          <select
            id="f-type"
            className={fieldClass}
            value={filters.type}
            onChange={(e) => set({ type: e.target.value as ProposalFilters["type"] })}
          >
            <option value="">All types</option>
            {(Object.keys(TYPE_LABEL) as ProposalType[]).map((t) => (
              <option key={t} value={t}>
                {TYPE_LABEL[t]}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label={`Min confidence ${Math.round(filters.minConfidence * 100)}%`}
          htmlFor="f-conf"
          className="w-48"
        >
          <input
            id="f-conf"
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={filters.minConfidence}
            onChange={(e) => set({ minConfidence: Number(e.target.value) })}
            className="w-full accent-[var(--primary)]"
          />
        </Field>
        {filters.documentId && (
          <Button variant="ghost" size="sm" onClick={() => set({ documentId: "" })}>
            <X aria-hidden className="size-4" /> Clear document filter
          </Button>
        )}
      </div>
      {filters.status === "pending" && <BulkBar filters={filters} />}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,380px)_minmax(0,1fr)]">
        <div className="space-y-2">
          {list.isPending ? (
            Array.from({ length: 5 }, (_, i) => <Skeleton key={i} className="h-16" />)
          ) : list.error ? (
            <ErrorState message={list.error.message} onRetry={() => void list.refetch()} />
          ) : list.data.items.length === 0 ? (
            <EmptyState
              icon={filters.status === "pending" ? <Inbox /> : <Sparkles />}
              title={filters.status === "pending" ? "Queue is empty" : "Nothing here"}
              description="Upload lecture notes or use “Suggest missing edges” in the graph editor."
            />
          ) : (
            <>
              <ul className="space-y-2" aria-label="Proposals">
                {list.data.items.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(p.id)}
                      aria-current={selected === p.id ? "true" : undefined}
                      className={cn(
                        "w-full rounded-xl border bg-surface px-4 py-3 text-left transition-colors duration-150 hover:border-accent",
                        selected === p.id ? "border-accent" : "border-border",
                      )}
                    >
                      <div className="flex items-center gap-2 text-xs text-muted">
                        <span>{TYPE_LABEL[p.type]}</span>
                        <span className="ml-auto tabular-nums">
                          {confidenceLabel(p.confidence)}
                        </span>
                      </div>
                      <p className="mt-1 truncate text-sm font-medium">{summary(p)}</p>
                    </button>
                  </li>
                ))}
              </ul>
              {list.data.total > list.data.page_size && (
                <div className="flex items-center justify-between text-sm text-muted">
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </Button>
                  <span>
                    Page {page} of {Math.ceil(list.data.total / list.data.page_size)}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={page * list.data.page_size >= list.data.total}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
        <div className="min-w-0">
          {selected ? (
            <DetailPane key={selected} id={selected} concepts={graph.data?.concepts ?? []} />
          ) : (
            <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
              Select a proposal to see the rationale, the affected subgraph and the decision
              buttons.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
