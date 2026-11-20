/** Tutor API types (mirror apps/api/app/tutor/trace.py and app/api/tutor.py). */

export type Mode = "graphrag" | "plain_rag";
export type Intent = "explain" | "debug" | "compare" | "example" | "complexity" | "other";

export interface ConceptMatch {
  id: string;
  name: string;
  confidence: number;
  reason: string;
  source: "llm" | "fulltext" | "embedding" | "fusion" | "continued";
}

export interface TraceEdge {
  source: string;
  target: string;
  type: string;
}

export interface TraceConcept {
  id: string;
  name: string;
  role: "matched" | "prerequisite" | "related";
  depth: number;
  weak: boolean | null;
  mastery: number | null;
  path: TraceEdge[];
}

export interface TraceChunk {
  id: string;
  concept_id: string;
  kind: string;
  tokens: number;
  score: number | null;
}

export interface ControllerStep {
  action: "answer_now" | "ask_diagnostic" | "expand_traversal";
  reason: string;
  question: string | null;
}

export interface RetrievalTrace {
  version: number;
  mode: Mode;
  question: string;
  is_on_topic: boolean;
  intent: Intent;
  classification_path: "llm" | "hybrid" | "continued" | "cache" | "none";
  matched: ConceptMatch[];
  fallback: { fulltext: string[]; embedding: string[]; fused: string[] } | null;
  depth: number;
  concepts: TraceConcept[];
  controller: ControllerStep[];
  diagnostic: string | null;
  diagnostic_reply: string | null;
  chunks: TraceChunk[];
  budget_tokens: number;
  used_tokens: number;
  timings_ms: Record<string, number>;
  cached: boolean;
  truncated: boolean;
  citations: string[];
  followups: string[];
  summary?: string;
}

export interface Thread {
  id: string;
  subject_id: string;
  title: string;
  archived: boolean;
  created_at: string;
  updated_at: string;
  last_message_at?: string | null;
  message_count?: number | null;
}

export interface ThreadPage {
  items: Thread[];
  page: number;
  page_size: number;
  total: number;
}

export interface Feedback {
  rating: -1 | 1 | null;
  reported: boolean;
}

export interface ServerMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  mode: Mode | null;
  retrieval_trace: RetrievalTrace | null;
  provider: string | null;
  model: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  latency_ms: number | null;
  cached: boolean;
  truncated: boolean;
  reply_to: string | null;
  created_at: string;
  feedback: Feedback | null;
}

export interface ThreadDetail {
  thread: Thread;
  messages: ServerMessage[];
}

export interface DoneData {
  message_id: string;
  thread_id: string;
  content: string;
  moderated: boolean;
  cached: boolean;
  truncated: boolean;
  diagnostic: boolean;
  usage: {
    provider: string | null;
    model: string | null;
    tokens_in: number;
    tokens_out: number;
    latency_ms: number;
    model_calls: number;
  };
}

export interface StreamErrorData {
  code: string;
  message: string;
  message_id: string | null;
}

export interface Suggestions {
  starters: { title: string; prompt: string }[];
  continue: {
    id: string | null;
    concept_id: string;
    name: string;
    reason: string;
    rule: "R1" | "R2" | "R3" | "R4" | "R5" | "BASELINE";
    action: "learn" | "practice" | "review";
    path: { source: string; target: string }[];
    names?: Record<string, string>;
  } | null;
}

export interface CompareSide {
  content: string;
  trace: RetrievalTrace;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
}

export interface CompareResult {
  question: string;
  graphrag: CompareSide;
  plain_rag: CompareSide;
}

export type ReportReason = "incorrect" | "incomplete" | "off_topic" | "harmful" | "other";

/** A message as the chat view holds it (server messages plus in-flight streaming state). */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: Mode;
  status: "done" | "streaming" | "error" | "stopped";
  trace: RetrievalTrace | null;
  followups: string[];
  feedback: Feedback | null;
  diagnostic: boolean;
  truncated: boolean;
  cached: boolean;
  moderated?: boolean;
  provider?: string | null;
  model?: string | null;
  tokensIn?: number | null;
  tokensOut?: number | null;
  latencyMs?: number | null;
  error?: StreamErrorData;
  /** Not yet saved on the server (optimistic). */
  local?: boolean;
}
