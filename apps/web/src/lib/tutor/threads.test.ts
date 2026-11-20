import { describe, expect, it } from "vitest";

import { groupOf, groupThreads, toChatMessages } from "@/lib/tutor/threads";
import type { ServerMessage, Thread } from "@/lib/tutor/types";

const now = new Date(2026, 10, 20, 15, 0, 0); // local time

function thread(id: string, at: Date): Thread {
  const iso = at.toISOString();
  return { id, subject_id: "dsa", title: id, archived: false, created_at: iso, updated_at: iso };
}

describe("thread grouping", () => {
  it("assigns Today / Yesterday / Last 7 days / Older by local day", () => {
    expect(groupOf(new Date(2026, 10, 20, 0, 5).toISOString(), now)).toBe("Today");
    expect(groupOf(new Date(2026, 10, 19, 23, 59).toISOString(), now)).toBe("Yesterday");
    expect(groupOf(new Date(2026, 10, 14, 9, 0).toISOString(), now)).toBe("Last 7 days");
    expect(groupOf(new Date(2026, 10, 13, 9, 0).toISOString(), now)).toBe("Older");
  });

  it("orders groups and threads newest first and drops empty groups", () => {
    const groups = groupThreads(
      [
        thread("old", new Date(2026, 9, 1)),
        thread("today-early", new Date(2026, 10, 20, 8)),
        thread("today-late", new Date(2026, 10, 20, 14)),
      ],
      now,
    );
    expect(groups.map((g) => g.group)).toEqual(["Today", "Older"]);
    expect(groups[0].threads.map((t) => t.id)).toEqual(["today-late", "today-early"]);
  });

  it("uses the last message time when it is present", () => {
    const t = { ...thread("t", new Date(2026, 9, 1)), last_message_at: now.toISOString() };
    expect(groupThreads([t], now)[0].group).toBe("Today");
  });
});

describe("toChatMessages", () => {
  it("maps server messages, skipping system ones", () => {
    const base: Omit<ServerMessage, "id" | "role" | "content"> = {
      mode: "graphrag",
      retrieval_trace: null,
      provider: null,
      model: null,
      tokens_in: null,
      tokens_out: null,
      latency_ms: null,
      cached: false,
      truncated: false,
      reply_to: null,
      created_at: now.toISOString(),
      feedback: null,
    };
    const out = toChatMessages([
      { ...base, id: "1", role: "user", content: "q" },
      { ...base, id: "2", role: "system", content: "s" },
      { ...base, id: "3", role: "assistant", content: "a", truncated: true },
    ]);
    expect(out.map((m) => m.id)).toEqual(["1", "3"]);
    expect(out[1].status).toBe("stopped");
  });
});
