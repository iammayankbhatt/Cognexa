/**
 * Minimal Server-Sent Events parser for fetch() streams (EventSource cannot POST or send an
 * Authorization header). Handles events split across chunks, CRLF line endings, multi-line
 * `data:` fields and comment lines.
 */

export interface SSEMessage {
  event: string;
  data: string;
}

export class SSEParser {
  private buffer = "";

  /** Feed a decoded text chunk; returns the complete events it finished. */
  feed(chunk: string): SSEMessage[] {
    this.buffer += chunk.replace(/\r\n?/g, "\n");
    const out: SSEMessage[] = [];
    let end = this.buffer.indexOf("\n\n");
    while (end >= 0) {
      const block = this.buffer.slice(0, end);
      this.buffer = this.buffer.slice(end + 2);
      const msg = parseBlock(block);
      if (msg) out.push(msg);
      end = this.buffer.indexOf("\n\n");
    }
    return out;
  }

  /** End of stream: a final event without the blank line is still delivered. */
  flush(): SSEMessage[] {
    const rest = this.buffer.trim();
    this.buffer = "";
    const msg = rest ? parseBlock(rest) : null;
    return msg ? [msg] : [];
  }
}

function parseBlock(block: string): SSEMessage | null {
  let event = "message";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon < 0 ? line : line.slice(0, colon);
    let value = colon < 0 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
  }
  if (!data.length) return null;
  return { event, data: data.join("\n") };
}

/** Read a streaming Response body as SSE messages. */
export async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<SSEMessage> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  const parser = new SSEParser();
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      for (const msg of parser.feed(decoder.decode(value, { stream: true }))) yield msg;
    }
    for (const msg of parser.feed(decoder.decode())) yield msg;
    for (const msg of parser.flush()) yield msg;
  } finally {
    reader.releaseLock();
  }
}
