/**
 * Request types generated from the API's OpenAPI schema (Phase 14 contract check).
 * Regenerate with `uv run --project apps/api python scripts/export_openapi.py` then
 * `npm run api:types`; CI fails when the committed files are stale.
 *
 * Call sites write `body: {...} satisfies Body<"MePatch">`, so renaming or retyping a field in
 * the API breaks the web build instead of failing at runtime.
 */
import type { components } from "./schema";

export type Schemas = components["schemas"];
export type Body<N extends keyof Schemas> = Schemas[N];
