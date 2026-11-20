import { describe, expect, it } from "vitest";

import { readSSE, SSEParser } from "@/lib/tutor/sse";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
}

describe("SSEParser", () => {
  it("parses complete events", () => {
    const p = new SSEParser();
    const out = p.feed('event: trace\ndata: {"a":1}\n\nevent: token\ndata: {"text":"hi"}\n\n');
    expect(out).toEqual([
      { event: "trace", data: '{"a":1}' },
      { event: "token", data: '{"text":"hi"}' },
    ]);
  });

  it("joins events split across chunks at any position", () => {
    const text = 'event: token\ndata: {"text":"Hello"}\n\nevent: done\ndata: {"id":"x"}\n\n';
    for (const size of [1, 2, 5, 13]) {
      const p = new SSEParser();
      const out = [];
      for (let i = 0; i < text.length; i += size) out.push(...p.feed(text.slice(i, i + size)));
      expect(out.map((e) => e.event)).toEqual(["token", "done"]);
      expect(JSON.parse(out[0].data)).toEqual({ text: "Hello" });
    }
  });

  it("handles CRLF, comments, multi-line data and a default event name", () => {
    const p = new SSEParser();
    const out = p.feed(": keep-alive\r\n\r\ndata: line1\r\ndata: line2\r\n\r\n");
    expect(out).toEqual([{ event: "message", data: "line1\nline2" }]);
  });

  it("delivers a final event without the trailing blank line on flush", () => {
    const p = new SSEParser();
    expect(p.feed("event: done\ndata: {}")).toEqual([]);
    expect(p.flush()).toEqual([{ event: "done", data: "{}" }]);
    expect(p.flush()).toEqual([]);
  });

  it("keeps a token's own spaces and colons", () => {
    const p = new SSEParser();
    const [e] = p.feed('event: token\ndata: {"text":"  a: b "}\n\n');
    expect(JSON.parse(e.data).text).toBe("  a: b ");
  });
});

describe("readSSE", () => {
  it("reads a byte stream including multi-byte characters split across chunks", async () => {
    const enc = new TextEncoder();
    const bytes = enc.encode('event: token\ndata: {"text":"Ünïcode ✓"}\n\n');
    const mid = 30; // inside a multi-byte sequence
    const stream = new ReadableStream<Uint8Array>({
      start(c) {
        c.enqueue(bytes.slice(0, mid));
        c.enqueue(bytes.slice(mid));
        c.close();
      },
    });
    const events = [];
    for await (const e of readSSE(stream)) events.push(e);
    expect(JSON.parse(events[0].data).text).toBe("Ünïcode ✓");
  });

  it("yields events in order", async () => {
    const events = [];
    for await (const e of readSSE(streamOf(["event: a\ndata: 1\n\nevent: b\n", "data: 2\n\n"]))) {
      events.push(e.event);
    }
    expect(events).toEqual(["a", "b"]);
  });
});
