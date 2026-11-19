import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api";
import { formatWait, friendlyError } from "@/lib/errors";

const now = new Date("2026-11-20T22:00:00Z");

describe("formatWait", () => {
  it.each([
    [0.2, "in 1 s"],
    [45, "in 45 s"],
    [61, "in 2 min"],
    [3600, "in 1 h"],
    [7500, "in 2 h 5 min"],
  ])("%s seconds -> %s", (s, text) => expect(formatWait(s)).toBe(text));
});

describe("friendlyError", () => {
  const err = (code: string, details?: Record<string, unknown>, status = 429) =>
    new ApiError(status, code, "backend message", "rid", details);

  it("explains the daily quota with the reset time", () => {
    const f = friendlyError(err("QUOTA_EXCEEDED", { reset_at: "2026-11-21T00:00:00+00:00" }), now);
    expect(f.title).toBe("Daily AI limit reached");
    expect(f.description).toContain("resets in 2 h (at");
    expect(f.description).toContain("Review mode");
  });

  it("explains the per-minute limit and the global cap", () => {
    const rl = friendlyError(err("RATE_LIMITED", { reset_at: "2026-11-20T22:00:40+00:00" }), now);
    expect(rl.description).toContain("resets in 40 s");
    expect(friendlyError(err("GLOBAL_CAP", {}), now).title).toBe("Cognexa is resting");
  });

  it("works without details and for other errors", () => {
    expect(friendlyError(err("QUOTA_EXCEEDED"), now).description).not.toContain("resets");
    expect(friendlyError(err("INPUT_TOO_LONG", undefined, 413)).description).toBe(
      "backend message",
    );
    expect(friendlyError(err("weird", undefined, 500)).description).toBe("backend message");
    expect(friendlyError(new Error("x")).title).toBe("Something went wrong");
  });
});
