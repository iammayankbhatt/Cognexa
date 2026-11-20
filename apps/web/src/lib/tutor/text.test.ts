import { describe, expect, it } from "vitest";

import {
  citedIds,
  conceptIdFromHref,
  linkCitations,
  parseTrailer,
  splitCode,
  stripTrailer,
} from "@/lib/tutor/text";

describe("citations", () => {
  it("links [[id]] citations outside code only", () => {
    const md =
      "Uses [[call_stack]].\n\n```python\nx = a[[0]]  # [[not_a_cite]]\n```\n\nSee `[[inline]]` and [[recursion]].";
    const out = linkCitations(md);
    expect(out).toContain("[call_stack](#concept=call_stack)");
    expect(out).toContain("[recursion](#concept=recursion)");
    expect(out).toContain("# [[not_a_cite]]");
    expect(out).toContain("`[[inline]]`");
  });

  it("lists cited ids once, in order, ignoring code", () => {
    expect(citedIds("[[b]] then [[a]] and [[b]] `[[c]]`")).toEqual(["b", "a"]);
  });

  it("rejects malformed ids", () => {
    expect(linkCitations("[[Bad-Id]] [[1abc]]")).toBe("[[Bad-Id]] [[1abc]]");
    expect(conceptIdFromHref("#concept=call_stack")).toBe("call_stack");
    expect(conceptIdFromHref("#concept=../../x")).toBeNull();
    expect(conceptIdFromHref("https://example.com")).toBeNull();
    expect(conceptIdFromHref(undefined)).toBeNull();
  });

  it("treats an unclosed fence as code to the end (still streaming)", () => {
    const parts = splitCode("text [[a]]\n```\ncode [[b]]");
    expect(parts.map((p) => p.code)).toEqual([false, true]);
    expect(linkCitations("text [[a]]\n```\ncode [[b]]")).toContain("code [[b]]");
  });
});

describe("follow-up trailer", () => {
  it("strips a complete or streaming trailer, or a partial opening tag", () => {
    expect(stripTrailer('Answer.\n\n<followups>["a?","b?"]</followups>')).toBe("Answer.");
    expect(stripTrailer('Answer.\n<followups>["a?"')).toBe("Answer.");
    expect(stripTrailer("Answer. <follo")).toBe("Answer. ");
    expect(stripTrailer("Answer.")).toBe("Answer.");
  });

  it("parses JSON trailers and keeps at most two", () => {
    expect(parseTrailer('x <followups>["One?", "Two?", "Three?"]</followups>')).toEqual([
      "One?",
      "Two?",
    ]);
  });

  it("falls back to question lines when the trailer is not JSON", () => {
    expect(parseTrailer("x <followups>here you go\n- First?\n- Second?</followups>")).toEqual([
      "First?",
      "Second?",
    ]);
    expect(parseTrailer("no trailer")).toEqual([]);
  });
});
