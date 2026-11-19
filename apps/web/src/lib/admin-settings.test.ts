import { describe, expect, it } from "vitest";

import { validateSection } from "@/lib/admin-settings";

describe("validateSection", () => {
  it("coerces numeric strings from inputs", () => {
    const r = validateSection("quota", {
      daily_ai_requests: "50",
      per_minute: "6",
      max_input_chars: "2000",
      max_output_tokens: "900",
    });
    expect(r).toEqual({
      ok: true,
      value: {
        daily_ai_requests: 50,
        per_minute: 6,
        max_input_chars: 2000,
        max_output_tokens: 900,
      },
    });
  });

  it("reports the first error per field, matching backend bounds", () => {
    const r = validateSection("quota", {
      daily_ai_requests: "-1",
      per_minute: "0",
      max_input_chars: "2000.5",
      max_output_tokens: "abc",
    });
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.daily_ai_requests).toBe("At least 0");
      expect(r.errors.per_minute).toBe("At least 1");
      expect(r.errors.max_input_chars).toBe("Whole numbers only");
      expect(r.errors.max_output_tokens).toBe("Enter a number");
    }
  });

  it("treats an empty field as an error, not zero", () => {
    const r = validateSection("global_cap", { ai_requests: "  " });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.ai_requests).toBe("Enter a number");
  });

  it("validates pricing rows and flags", () => {
    expect(
      validateSection("pricing", {
        default: { input_per_1m: "0.5", output_per_1m: "1.5" },
        models: { "some-model": { input_per_1m: 0.1, output_per_1m: 0.2 } },
      }).ok,
    ).toBe(true);
    expect(validateSection("features", { AGENTIC_MODE: true, STUDY_MODE: "yes" }).ok).toBe(false);
  });
});
