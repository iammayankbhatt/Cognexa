import type { ChatMessage, ServerMessage, Thread } from "@/lib/tutor/types";

export type ThreadGroup = "Today" | "Yesterday" | "Last 7 days" | "Older";
const ORDER: ThreadGroup[] = ["Today", "Yesterday", "Last 7 days", "Older"];

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

export function groupOf(iso: string, now: Date = new Date()): ThreadGroup {
  const day = 86_400_000;
  const t = startOfDay(new Date(iso));
  const today = startOfDay(now);
  if (t >= today) return "Today";
  if (t >= today - day) return "Yesterday";
  if (t >= today - 6 * day) return "Last 7 days";
  return "Older";
}

/** Threads grouped by their last activity, newest first, empty groups left out. */
export function groupThreads(
  threads: Thread[],
  now: Date = new Date(),
): { group: ThreadGroup; threads: Thread[] }[] {
  const activity = (t: Thread) => t.last_message_at ?? t.updated_at;
  const sorted = [...threads].sort((a, b) => activity(b).localeCompare(activity(a)));
  const by = new Map<ThreadGroup, Thread[]>();
  for (const t of sorted) {
    const g = groupOf(activity(t), now);
    by.set(g, [...(by.get(g) ?? []), t]);
  }
  return ORDER.filter((g) => by.has(g)).map((g) => ({ group: g, threads: by.get(g)! }));
}

/** Server messages → chat view messages. */
export function toChatMessages(messages: ServerMessage[]): ChatMessage[] {
  return messages
    .filter((m): m is ServerMessage & { role: "user" | "assistant" } => m.role !== "system")
    .map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      mode: m.mode ?? "graphrag",
      status: m.truncated ? "stopped" : "done",
      trace: m.retrieval_trace,
      followups: m.retrieval_trace?.followups ?? [],
      feedback: m.feedback,
      diagnostic: Boolean(m.retrieval_trace?.diagnostic),
      truncated: m.truncated,
      cached: m.cached,
      provider: m.provider,
      model: m.model,
      tokensIn: m.tokens_in,
      tokensOut: m.tokens_out,
      latencyMs: m.latency_ms,
    }));
}
