import { execSync } from "node:child_process";
import { randomUUID } from "node:crypto";

/**
 * Helpers for e2e tests that need the local Supabase stack (`npx supabase start`) and the API
 * (`uvicorn` on :8000). Secrets are read from `supabase status` at run time and never printed.
 */
export interface LocalStack {
  url: string;
  serviceKey: string;
  anonKey: string;
  mailpit: string;
}

export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const PASSWORD = "Str0ng-pass!e2e";

export async function localStack(): Promise<LocalStack | null> {
  try {
    // Read once per run by global-setup.ts; fall back to a direct lookup (single spec runs).
    const raw =
      process.env.E2E_SUPABASE_STATUS ??
      execSync("npx supabase status -o json", {
        cwd: "../..",
        stdio: ["ignore", "pipe", "ignore"],
        timeout: 60_000,
      }).toString();
    const s = JSON.parse(raw) as Record<string, string>;
    const stack = {
      url: s.API_URL,
      serviceKey: s.SERVICE_ROLE_KEY,
      anonKey: s.ANON_KEY,
      mailpit: s.MAILPIT_URL,
    };
    const [auth, api] = await Promise.all([
      fetch(`${stack.url}/auth/v1/health`).then(
        (r) => r.ok,
        () => false,
      ),
      fetch(`${API}/health`).then(
        (r) => r.ok,
        () => false,
      ),
    ]);
    if (!(auth && api)) return required("the local Supabase stack or the API is not reachable");
    return stack;
  } catch (err) {
    if (err instanceof RequiredStackError) throw err;
    return required("`npx supabase status` could not be read");
  }
}

class RequiredStackError extends Error {}

/** Locally a missing stack skips the specs that need it; in CI (E2E_REQUIRE_STACK=1) it fails. */
function required(reason: string): null {
  if (process.env.E2E_REQUIRE_STACK === "1") throw new RequiredStackError(reason);
  return null;
}

export async function createUser(stack: LocalStack, name = "E2E Student") {
  const email = `e2e-${randomUUID().slice(0, 8)}@example.com`;
  const res = await fetch(`${stack.url}/auth/v1/admin/users`, {
    method: "POST",
    headers: {
      apikey: stack.serviceKey,
      Authorization: `Bearer ${stack.serviceKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password: PASSWORD,
      email_confirm: true,
      user_metadata: { full_name: name },
    }),
  });
  if (!res.ok) throw new Error(`could not create test user: ${res.status}`);
  const body = (await res.json()) as { id: string };
  return { id: body.id, email, password: PASSWORD };
}

export async function deleteUser(stack: LocalStack, id: string) {
  await fetch(`${stack.url}/auth/v1/admin/users/${id}`, {
    method: "DELETE",
    headers: { apikey: stack.serviceKey, Authorization: `Bearer ${stack.serviceKey}` },
  });
}

export async function messagesTo(stack: LocalStack, email: string) {
  const res = await fetch(
    `${stack.mailpit}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`,
  );
  const body = (await res.json()) as { messages?: { Subject: string }[] };
  return body.messages ?? [];
}

/** Password-grant sign-in against the local Auth server; returns the access token. */
export async function accessTokenFor(stack: LocalStack, email: string, password = PASSWORD) {
  const res = await fetch(`${stack.url}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: { apikey: stack.anonKey, "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`sign-in failed: ${res.status}`);
  return ((await res.json()) as { access_token: string }).access_token;
}

/**
 * Update a profile row through the local Supabase REST API with the service key (local stack
 * only). Do it before the user's first API call: the API caches roles for 30 s.
 */
export async function setProfile(stack: LocalStack, id: string, fields: Record<string, unknown>) {
  const res = await fetch(`${stack.url}/rest/v1/profiles?id=eq.${id}`, {
    method: "PATCH",
    headers: {
      apikey: stack.serviceKey,
      Authorization: `Bearer ${stack.serviceKey}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal",
    },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error(`could not update profile: ${res.status} ${await res.text()}`);
}
