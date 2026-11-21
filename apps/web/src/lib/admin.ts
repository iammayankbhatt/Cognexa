"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Body } from "@/lib/api-contract";
import { api } from "@/lib/api";

// ---------------------------------------------------------------- graph editor
export type EdgeType = "PREREQUISITE_OF" | "RELATED_TO";

export interface AdminConcept {
  id: string;
  subject_id: string;
  name: string;
  cluster: string;
  difficulty: number;
  order_index: number;
  description: string;
  aliases: string[];
  keywords: string[];
  status: string;
}

export interface AdminEdge {
  source: string;
  target: string;
  type: EdgeType;
  weight: number;
  source_kind: "human" | "llm";
  status: string;
  rationale: string | null;
}

export interface AdminGraph {
  subject_id: string;
  concepts: AdminConcept[];
  edges: AdminEdge[];
}

export interface ConceptInput {
  name: string;
  cluster: string;
  difficulty: number;
  description: string;
  aliases: string[];
  keywords: string[];
}

export const ADMIN_GRAPH_KEY = ["admin", "graph"] as const;

export function useAdminGraph() {
  return useQuery({
    queryKey: ADMIN_GRAPH_KEY,
    queryFn: () => api<AdminGraph>("/admin/graph"),
  });
}

export interface CycleCheck {
  ok: boolean;
  message: string | null;
  path: string[];
}

export function checkEdge(source: string, target: string) {
  const q = new URLSearchParams({ source, target });
  return api<CycleCheck>(`/admin/graph/edges/check?${q}`);
}

/** All graph mutations; each refreshes the editor's graph. */
export function useGraphMutations() {
  const qc = useQueryClient();
  const refresh = () => void qc.invalidateQueries({ queryKey: ADMIN_GRAPH_KEY });
  return {
    createConcept: useMutation({
      mutationFn: (body: ConceptInput & { id: string } & Body<"ConceptCreate">) =>
        api<AdminConcept>("/admin/graph/concepts", { method: "POST", body }),
      onSuccess: refresh,
    }),
    updateConcept: useMutation({
      mutationFn: ({ id, ...body }: ConceptInput & { id: string }) =>
        api<AdminConcept>(`/admin/graph/concepts/${id}`, {
          method: "PUT",
          body: body satisfies Body<"ConceptIn">,
        }),
      onSuccess: refresh,
    }),
    addEdge: useMutation({
      mutationFn: (body: {
        source: string;
        target: string;
        type: EdgeType;
        rationale: string | null;
      }) =>
        api<AdminEdge>("/admin/graph/edges", {
          method: "POST",
          body: body satisfies Body<"EdgeIn">,
        }),
      onSuccess: refresh,
    }),
    removeEdge: useMutation({
      mutationFn: (e: { source: string; target: string; type: EdgeType; rationale?: string }) => {
        const q = new URLSearchParams({ source: e.source, target: e.target, type: e.type });
        if (e.rationale) q.set("rationale", e.rationale);
        return api<void>(`/admin/graph/edges?${q}`, { method: "DELETE" });
      },
      onSuccess: refresh,
    }),
    suggest: useMutation({
      mutationFn: (conceptId: string) =>
        api<{ created: string[]; skipped: { other_id: string; reason: string }[] }>(
          `/admin/graph/concepts/${conceptId}/suggest-edges`,
          { method: "POST" },
        ),
      onSuccess: () => void qc.invalidateQueries({ queryKey: ["admin", "proposals"] }),
    }),
  };
}

// ---------------------------------------------------------------- proposals
export type ProposalType = "add_edge" | "remove_edge" | "tag_chunk" | "new_concept";
export type ProposalStatus = "pending" | "approved" | "rejected";

export interface Proposal {
  id: string;
  type: ProposalType;
  payload: Record<string, unknown>;
  rationale: string | null;
  confidence: number | null;
  status: ProposalStatus;
  proposed_by: "llm" | "user";
  decided_at: string | null;
  note: string | null;
  created_at: string;
  names?: Record<string, string>;
}

export interface ProposalDetail extends Proposal {
  cycle: { message: string; path: string[] } | null;
  preview: { concepts: AdminConcept[]; edges: AdminEdge[] };
}

export interface ProposalStats {
  by_type: Record<
    string,
    { pending: number; approved: number; rejected: number; acceptance_rate: number | null }
  >;
  total: { pending: number; approved: number; rejected: number; acceptance_rate: number | null };
  approved_after_edit: number;
}

export interface ProposalFilters {
  status: ProposalStatus;
  type: ProposalType | "";
  minConfidence: number;
  documentId: string;
}

export function useProposals(f: ProposalFilters, page: number) {
  const q = new URLSearchParams({ status: f.status, page: String(page), page_size: "20" });
  if (f.type) q.set("type", f.type);
  if (f.minConfidence > 0) q.set("min_confidence", String(f.minConfidence));
  if (f.documentId) q.set("document_id", f.documentId);
  return useQuery({
    queryKey: ["admin", "proposals", "list", q.toString()],
    queryFn: () =>
      api<{ items: Proposal[]; total: number; page: number; page_size: number }>(
        `/admin/proposals?${q}`,
      ),
  });
}

export function useProposal(id: string | null) {
  return useQuery({
    queryKey: ["admin", "proposals", "one", id],
    queryFn: () => api<ProposalDetail>(`/admin/proposals/${id}`),
    enabled: Boolean(id),
  });
}

export function useProposalStats() {
  return useQuery({
    queryKey: ["admin", "proposals", "stats"],
    queryFn: () => api<ProposalStats>("/admin/proposals/stats"),
  });
}

export function useProposalDecisions() {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["admin", "proposals"] });
    void qc.invalidateQueries({ queryKey: ADMIN_GRAPH_KEY });
    void qc.invalidateQueries({ queryKey: ["admin", "overview"] });
  };
  return {
    approve: useMutation({
      mutationFn: (v: { id: string; note?: string; edits?: Record<string, unknown> }) =>
        api<{ proposal: Proposal; applied: Record<string, unknown> }>(
          `/admin/proposals/${v.id}/approve`,
          {
            method: "POST",
            body: { note: v.note || null, edits: v.edits ?? null } satisfies Body<"DecisionIn">,
          },
        ),
      onSuccess: refresh,
    }),
    reject: useMutation({
      mutationFn: (v: { id: string; note?: string }) =>
        api<{ proposal: Proposal }>(`/admin/proposals/${v.id}/reject`, {
          method: "POST",
          body: { note: v.note || null } satisfies Body<"DecisionIn">,
        }),
      onSuccess: refresh,
    }),
    bulk: useMutation({
      mutationFn: (body: {
        min_confidence: number;
        type: ProposalType | null;
        document_id: string | null;
        expected_count: number;
      }) =>
        api<{ approved: string[]; failed: { id: string; code: string; message: string }[] }>(
          "/admin/proposals/bulk-approve",
          { method: "POST", body: body satisfies Body<"BulkIn"> },
        ),
      onSuccess: refresh,
    }),
  };
}

export interface IngestDocument {
  id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  pages: number | null;
  sections: number;
  proposals: number;
  status: "processing" | "done" | "failed";
  error: string | null;
  created_at: string;
}

export function useIngestDocuments() {
  return useQuery({
    queryKey: ["admin", "ingest"],
    queryFn: () => api<{ items: IngestDocument[] }>("/admin/ingest"),
    // keep polling while a document is still being tagged
    refetchInterval: (q) =>
      q.state.data?.items.some((d) => d.status === "processing") ? 2000 : false,
  });
}

// ---------------------------------------------------------------- overview & moderation
export interface Overview {
  users: number;
  dau: number;
  wau: number;
  ai_requests_today: number;
  global_cap: number;
  cache_hit_rate_today: number | null;
  est_cost_today_usd: number;
  open_reports: number;
  pending_proposals: number;
  last_eval_run: { id: string; name: string; finished_at: string | null } | null;
}

export function useOverview() {
  return useQuery({
    queryKey: ["admin", "overview"],
    queryFn: () => api<Overview>("/admin/overview"),
  });
}

export interface TraceConceptRef {
  id: string;
  name: string;
  role: string;
}

export interface Report {
  id: string;
  reason: string;
  comment: string | null;
  status: "open" | "reviewing" | "resolved" | "dismissed";
  resolution_note: string | null;
  reported_at: string;
  reporter: string | null;
  message: {
    id: string;
    content: string;
    mode: string | null;
    answered_at: string;
    question: string | null;
    concepts: TraceConceptRef[];
    trace: Record<string, unknown> | null;
  };
}

export function useReports(status: Report["status"]) {
  return useQuery({
    queryKey: ["admin", "reports", status],
    queryFn: () =>
      api<{ items: Report[]; total: number }>(`/admin/reports?status=${status}&page_size=50`),
  });
}

export interface ConceptFeedback {
  concept_id: string;
  name: string;
  thumbs_down: number;
  thumbs_up: number;
  reports: number;
}

export function useFeedbackByConcept() {
  return useQuery({
    queryKey: ["admin", "feedback-by-concept"],
    queryFn: () => api<{ items: ConceptFeedback[] }>("/admin/feedback/by-concept"),
  });
}

// ---------------------------------------------------------------- content
export interface AdminChunk {
  id: string;
  concept_id: string;
  kind: string;
  heading: string;
  text: string;
  order: number;
  reviewed: boolean;
  source: "notes" | "llm" | "admin";
  embedded: boolean;
}

export interface QuestionStats {
  attempts: number;
  pct_correct: number | null;
  discrimination: number | null;
  flags: ("too_easy" | "too_hard" | "low_discrimination")[];
}

export interface AdminOption {
  id: string;
  text: string;
  why_wrong?: string | null;
}

export interface AdminQuestion {
  id: string;
  concept_id: string;
  type: "mcq" | "multi_select" | "true_false" | "code_output" | "short_answer";
  difficulty: number;
  prompt: string;
  code: string | null;
  language: "python" | "cpp";
  options: AdminOption[] | null;
  answer: unknown;
  explanation: string;
  rubric: { key_points: string[]; max_score?: number; partial_credit?: boolean } | null;
  misconception_tag: string | null;
  diagnoses_prereq: string | null;
  status: "active" | "inactive" | "draft";
  source: string | null;
  reviewed: boolean;
  stats: QuestionStats;
}

export interface ConceptContent {
  concept: AdminConcept;
  chunks: AdminChunk[];
  chunk_kinds: string[];
  questions: AdminQuestion[];
}

export function useConceptContent(conceptId: string | null) {
  return useQuery({
    queryKey: ["admin", "content", conceptId],
    queryFn: () => api<ConceptContent>(`/admin/content/concepts/${conceptId}`),
    enabled: Boolean(conceptId),
  });
}

/** Chunk ids contain "#" (e.g. "stack#overview"), so they must be encoded in URLs. */
export function chunkPath(id: string): string {
  return `/admin/content/chunks/${encodeURIComponent(id)}`;
}

export function useContentMutations(conceptId: string | null) {
  const qc = useQueryClient();
  const refresh = () => void qc.invalidateQueries({ queryKey: ["admin", "content", conceptId] });
  return {
    editChunk: useMutation({
      mutationFn: ({
        id,
        ...body
      }: {
        id: string;
        heading: string;
        text: string;
        kind: string;
        reviewed?: boolean;
      }) =>
        api<AdminChunk & { warning: string | null }>(chunkPath(id), {
          method: "PUT",
          body: body satisfies Body<"ChunkEdit">,
        }),
      onSuccess: refresh,
    }),
    reviewChunk: useMutation({
      mutationFn: (v: { id: string; reviewed: boolean }) =>
        api<AdminChunk>(chunkPath(v.id), {
          method: "PATCH",
          body: { reviewed: v.reviewed } satisfies Body<"Flags">,
        }),
      onSuccess: refresh,
    }),
    editQuestion: useMutation({
      mutationFn: ({ id, body }: { id: string; body: Body<"QuestionEdit"> }) =>
        api<AdminQuestion>(`/admin/content/questions/${encodeURIComponent(id)}`, {
          method: "PUT",
          body,
        }),
      onSuccess: refresh,
    }),
    flagQuestion: useMutation({
      mutationFn: ({
        id,
        ...body
      }: {
        id: string;
        reviewed?: boolean;
        status?: "active" | "inactive";
      }) =>
        api<AdminQuestion>(`/admin/content/questions/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body,
        }),
      onSuccess: refresh,
    }),
  };
}

export function useModerationActions() {
  const qc = useQueryClient();
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["admin", "reports"] });
    void qc.invalidateQueries({ queryKey: ["admin", "overview"] });
  };
  return {
    act: useMutation({
      mutationFn: (v: {
        id: string;
        status: "reviewing" | "resolved" | "dismissed";
        note?: string;
      }) =>
        api<{ id: string; status: string }>(`/admin/reports/${v.id}`, {
          method: "POST",
          body: { status: v.status, note: v.note?.trim() || null } satisfies Body<"ReportAction">,
        }),
      onSuccess: refresh,
    }),
    invalidate: useMutation({
      mutationFn: (id: string) =>
        api<{ removed: number; had_cache_key: boolean }>(`/admin/reports/${id}/invalidate-cache`, {
          method: "POST",
        }),
    }),
  };
}

export interface UserUsage {
  user_id: string;
  days: number;
  history: {
    date: string;
    ai_requests: number;
    tokens_in: number;
    tokens_out: number;
    est_cost_usd: number;
  }[];
  totals: {
    ai_requests: number;
    est_cost_usd: number;
    quizzes: number;
    tutor_questions: number;
    reports_filed: number;
  };
}

export function useUserUsage(userId: string | null) {
  return useQuery({
    queryKey: ["admin", "user-usage", userId],
    queryFn: () => api<UserUsage>(`/admin/users/${userId}/usage?days=30`),
    enabled: Boolean(userId),
  });
}

/** Save a Blob from the API as a file download. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
