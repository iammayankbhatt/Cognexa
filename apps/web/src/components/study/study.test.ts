import { describe, expect, it } from "vitest";

import { stepText, type StudyState } from "@/lib/study";

const base: StudyState = {
  enabled: true,
  step: "consent",
  group: "none",
  enrolled_at: null,
  consent_at: null,
  pretest: null,
  posttest: null,
  posttest_unlock_at: null,
  pretest_minutes: 20,
};

describe("study step text", () => {
  it("describes each step", () => {
    expect(stepText(base).title).toMatch(/invited/);
    expect(stepText({ ...base, step: "pretest" }).body).toContain("20 minutes");
    expect(stepText({ ...base, step: "posttest" }).title).toMatch(/post-test is open/);
    expect(stepText({ ...base, step: "off" })).toEqual({ title: "", body: "" });
  });

  it("counts down to the post-test", () => {
    const now = new Date("2026-11-20T12:00:00Z");
    const s = { ...base, step: "learning" as const, posttest_unlock_at: "2026-11-23T10:00:00Z" };
    expect(stepText(s, now).body).toContain("opens in 3 days");
    expect(stepText({ ...s, posttest_unlock_at: null }, now).body).toBe(
      "Use Cognexa as you normally would.",
    );
  });
});
