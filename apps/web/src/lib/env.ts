/** Public (browser-safe) configuration. Only NEXT_PUBLIC_* values are readable in the browser. */
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

/** Unfilled cloud values are the literal REPLACE_ME (or empty) until the human adds real ones. */
export function isConfigured(value: string): boolean {
  return value.trim() !== "" && value.trim() !== "REPLACE_ME";
}

export const authConfigured = (): boolean =>
  isConfigured(SUPABASE_URL) && isConfigured(SUPABASE_ANON_KEY);
