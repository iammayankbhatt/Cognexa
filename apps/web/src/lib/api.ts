import { API_URL } from "@/lib/env";
import { getSupabase } from "@/lib/supabase/client";

/** Shape of every error the backend returns: {error: {code, message, request_id, details?}}. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly requestId?: string,
    public readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Listener = (waking: boolean) => void;
const listeners = new Set<Listener>();
let inflightSlow = 0;
export const COLD_START_MS = 3000;

/** Subscribe to the "waking up the server" state (a request taking longer than 3 s). */
export function onWakingChange(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
const notify = () => listeners.forEach((l) => l(inflightSlow > 0));

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as {
      error?: {
        code?: string;
        message?: string;
        request_id?: string;
        details?: Record<string, unknown>;
      };
    };
    const e = body.error;
    if (e)
      return new ApiError(
        res.status,
        e.code ?? "http_error",
        e.message ?? res.statusText,
        e.request_id,
        e.details,
      );
  } catch {
    // not JSON
  }
  return new ApiError(res.status, "http_error", res.statusText || "Request failed");
}

async function accessToken(forceRefresh = false): Promise<string | null> {
  const supabase = getSupabase();
  if (forceRefresh) {
    const { data } = await supabase.auth.refreshSession();
    return data.session?.access_token ?? null;
  }
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function send(path: string, init: RequestInit, token: string | null): Promise<Response> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  return fetch(`${API_URL}${path}`, { ...init, headers });
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  /** Skip the Authorization header (public endpoints such as /health). */
  anonymous?: boolean;
}

/**
 * Typed fetch wrapper. Attaches the access token, retries ONCE with a refreshed token on 401,
 * and throws ApiError with the backend's code, message and request id. If a request takes
 * longer than COLD_START_MS the "waking up the server" banner state is raised (Render free tier).
 */
export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, anonymous, ...rest } = options;
  const init: RequestInit = {
    ...rest,
    body: body === undefined ? undefined : JSON.stringify(body),
  };
  let slow = false;
  const timer = setTimeout(() => {
    slow = true;
    inflightSlow += 1;
    notify();
  }, COLD_START_MS);
  try {
    let token = anonymous ? null : await accessToken();
    let res = await send(path, init, token);
    if (res.status === 401 && !anonymous) {
      token = await accessToken(true);
      if (token) res = await send(path, init, token);
    }
    if (!res.ok) throw await parseError(res);
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    throw new ApiError(0, "network_error", "Could not reach the server. Check your connection.");
  } finally {
    clearTimeout(timer);
    if (slow) {
      inflightSlow -= 1;
      notify();
    }
  }
}

/**
 * POST that returns the raw streaming Response (Server-Sent Events). Same auth, 401 retry and
 * error envelope as `api`; an error status throws ApiError before any event is read.
 */
export async function apiStream(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<Response> {
  const init: RequestInit = {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: { Accept: "text/event-stream" },
    signal,
  };
  let slow = false;
  const timer = setTimeout(() => {
    slow = true;
    inflightSlow += 1;
    notify();
  }, COLD_START_MS);
  try {
    let token = await accessToken();
    let res = await send(path, init, token);
    if (res.status === 401) {
      token = await accessToken(true);
      if (token) res = await send(path, init, token);
    }
    if (!res.ok) throw await parseError(res);
    if (!res.body) throw new ApiError(0, "network_error", "The server sent no answer stream.");
    return res;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "Could not reach the server. Check your connection.");
  } finally {
    clearTimeout(timer);
    if (slow) {
      inflightSlow -= 1;
      notify();
    }
  }
}

/** Fire-and-forget warm-up so a sleeping free-tier backend is awake by the time it is needed. */
export function warmApi(): void {
  void api("/health", { anonymous: true }).catch(() => undefined);
}

export interface Usage {
  date: string;
  ai_requests: number;
  tokens_in: number;
  tokens_out: number;
  daily_quota: number;
}
export interface Me {
  id: string;
  email: string | null;
  display_name: string | null;
  role: "student" | "reviewer" | "admin";
  theme: string;
  study_group: string;
  onboarding_completed: boolean;
  experience_level: string | null;
  created_at: string | null;
  usage: Usage;
}

export interface UsageDay {
  date: string;
  ai_requests: number;
  tokens_in: number;
  tokens_out: number;
  est_cost_usd: number;
}
export interface UsageSummary {
  today: UsageDay & { remaining: number; resets_at: string };
  limits: {
    daily_ai_requests: number;
    per_minute: number;
    max_input_chars: number;
    max_output_tokens: number;
  };
  history: UsageDay[];
}
