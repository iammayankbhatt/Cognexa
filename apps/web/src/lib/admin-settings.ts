import { z } from "zod";

/** Mirrors the bounds in apps/api/app/api/admin_ai.py (the backend validates again). */
// Empty inputs must be an error, not 0 (Number("") === 0 would silently save zero).
const blankToUndefined = (v: unknown) => (typeof v === "string" && v.trim() === "" ? undefined : v);
const int = (min: number, max: number) =>
  z.preprocess(
    blankToUndefined,
    z.coerce
      .number({ error: "Enter a number" })
      .int("Whole numbers only")
      .min(min, `At least ${min}`)
      .max(max, `At most ${max}`),
  );
const num = (min: number, max: number) =>
  z.preprocess(
    blankToUndefined,
    z.coerce
      .number({ error: "Enter a number" })
      .min(min, `At least ${min}`)
      .max(max, `At most ${max}`),
  );

export const quotaSchema = z.object({
  daily_ai_requests: int(0, 10000),
  per_minute: int(1, 600),
  max_input_chars: int(100, 20000),
  max_output_tokens: int(50, 8000),
});
export const roleMultipliersSchema = z.object({
  student: int(1, 100),
  reviewer: int(1, 100),
  admin: int(1, 100),
});
export const globalCapSchema = z.object({ ai_requests: int(0, 1_000_000) });
export const cacheSchema = z.object({
  enabled: z.boolean(),
  response_ttl_days: num(0.01, 90),
  classification_ttl_days: num(0.01, 90),
  embedding_ttl_days: num(0.01, 365),
});
export const featuresSchema = z.object({
  AGENTIC_MODE: z.boolean(),
  STUDY_MODE: z.boolean(),
  PLAIN_RAG_VISIBLE_TO_STUDENTS: z.boolean(),
});
const price = z.object({ input_per_1m: num(0, 1000), output_per_1m: num(0, 1000) });
export const pricingSchema = z.object({
  default: price,
  models: z.record(z.string().trim().min(1).max(120), price),
});

export const SECTIONS = {
  quota: quotaSchema,
  role_multipliers: roleMultipliersSchema,
  global_cap: globalCapSchema,
  cache: cacheSchema,
  features: featuresSchema,
  pricing: pricingSchema,
} as const;
export type SectionName = keyof typeof SECTIONS;

export interface AdminSettings {
  quota: z.infer<typeof quotaSchema>;
  role_multipliers: z.infer<typeof roleMultipliersSchema>;
  global_cap: z.infer<typeof globalCapSchema>;
  cache: z.infer<typeof cacheSchema>;
  features: z.infer<typeof featuresSchema>;
  pricing: z.infer<typeof pricingSchema>;
  providers: {
    primary: { provider: string; model: string };
    fallback: { provider: string | null; model: string | null };
    judge: { provider: string; model: string };
    embedding: { provider: string; model: string; dim: number };
    keys: { groq: boolean; gemini: boolean };
  };
}

/** Validate one section; returns the parsed value or a map of field -> first error message. */
export function validateSection(
  name: SectionName,
  value: unknown,
): { ok: true; value: unknown } | { ok: false; errors: Record<string, string> } {
  const r = SECTIONS[name].safeParse(value);
  if (r.success) return { ok: true, value: r.data };
  const errors: Record<string, string> = {};
  for (const issue of r.error.issues) {
    const key = issue.path.join(".") || "_";
    errors[key] ??= issue.message;
  }
  return { ok: false, errors };
}

export const FLAG_HELP: Record<keyof z.infer<typeof featuresSchema>, string> = {
  AGENTIC_MODE:
    "Let the tutor run one bounded extra step (diagnostic check or expanded retrieval).",
  STUDY_MODE: "User-study mode: students are split into adaptive and baseline groups.",
  PLAIN_RAG_VISIBLE_TO_STUDENTS: "Show the plain-RAG comparison to students (normally admin-only).",
};
