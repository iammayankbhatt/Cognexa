import { describe, expect, it } from "vitest";

import { fillDays, formatUsd, shortDate } from "@/lib/usage";

describe("fillDays", () => {
  const today = new Date("2026-11-20T23:30:00Z");
  it("returns exactly N days ending today with zeros for gaps", () => {
    const rows = fillDays(
      [{ date: "2026-11-18", ai_requests: 3, tokens_in: 10, tokens_out: 5, est_cost_usd: 0.1 }],
      4,
      today,
    );
    expect(rows.map((r) => r.date)).toEqual([
      "2026-11-17",
      "2026-11-18",
      "2026-11-19",
      "2026-11-20",
    ]);
    expect(rows.map((r) => r.ai_requests)).toEqual([0, 3, 0, 0]);
  });

  it("crosses month boundaries", () => {
    const rows = fillDays([], 3, new Date("2026-12-01T00:10:00Z"));
    expect(rows.map((r) => r.date)).toEqual(["2026-11-29", "2026-11-30", "2026-12-01"]);
  });
});

describe("formatting", () => {
  it("formats dates in UTC and small costs precisely", () => {
    expect(shortDate("2026-11-20", "en-US")).toBe("Nov 20");
    expect(formatUsd(0)).toBe("$0");
    expect(formatUsd(0.00042)).toBe("$0.0004");
    expect(formatUsd(1.5)).toBe("$1.50");
  });
});
