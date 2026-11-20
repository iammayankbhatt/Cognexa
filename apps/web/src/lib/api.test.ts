import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const session = { token: "tok-1" as string | null, refreshed: "tok-2" as string | null };
vi.mock("@/lib/supabase/client", () => ({
  getSupabase: () => ({
    auth: {
      getSession: async () => ({
        data: { session: session.token ? { access_token: session.token } : null },
      }),
      refreshSession: async () => ({
        data: { session: session.refreshed ? { access_token: session.refreshed } : null },
      }),
    },
  }),
}));

import { api, ApiError, COLD_START_MS, onWakingChange } from "@/lib/api";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  session.token = "tok-1";
  session.refreshed = "tok-2";
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const auth = (call: number) =>
  new Headers(fetchMock.mock.calls[call][1].headers).get("Authorization");

describe("api()", () => {
  it("attaches the access token and parses JSON", async () => {
    fetchMock.mockResolvedValueOnce(json(200, { ok: true }));
    await expect(api("/me")).resolves.toEqual({ ok: true });
    expect(auth(0)).toBe("Bearer tok-1");
  });

  it("sends JSON bodies with a content type", async () => {
    fetchMock.mockResolvedValueOnce(json(200, {}));
    await api("/me", { method: "PATCH", body: { theme: "neon-noir" } });
    const init = fetchMock.mock.calls[0][1];
    expect(init.body).toBe('{"theme":"neon-noir"}');
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("sends a fresh request id the API accepts on every call", async () => {
    fetchMock.mockImplementation(async () => json(200, {}));
    await api("/me");
    await api("/me");
    const ids = [0, 1].map((i) =>
      new Headers(fetchMock.mock.calls[i][1].headers).get("X-Request-ID"),
    );
    for (const id of ids) expect(id).toMatch(/^[A-Za-z0-9._-]{8,64}$/);
    expect(ids[0]).not.toBe(ids[1]);
  });

  it("does not send a token for anonymous requests", async () => {
    fetchMock.mockResolvedValueOnce(json(200, {}));
    await api("/health", { anonymous: true });
    expect(auth(0)).toBeNull();
  });

  it("retries ONCE with a refreshed token after a 401", async () => {
    fetchMock
      .mockResolvedValueOnce(json(401, { error: { code: "unauthorized", message: "expired" } }))
      .mockResolvedValueOnce(json(200, { ok: 1 }));
    await expect(api("/me")).resolves.toEqual({ ok: 1 });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(auth(1)).toBe("Bearer tok-2");
  });

  it("gives up if the retry is also rejected (no loops)", async () => {
    fetchMock.mockImplementation(async () =>
      json(401, { error: { code: "unauthorized", message: "nope", request_id: "r1" } }),
    );
    await expect(api("/me")).rejects.toMatchObject({ status: 401, code: "unauthorized" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("maps the error envelope to ApiError with the request id", async () => {
    fetchMock.mockResolvedValueOnce(
      json(403, { error: { code: "forbidden", message: "No.", request_id: "abc123" } }),
    );
    const err = await api("/admin/users").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 403,
      code: "forbidden",
      message: "No.",
      requestId: "abc123",
    });
  });

  it("keeps error details (e.g. the quota reset time)", async () => {
    fetchMock.mockResolvedValueOnce(
      json(429, {
        error: {
          code: "QUOTA_EXCEEDED",
          message: "limit",
          request_id: "r9",
          details: { reset_at: "2026-11-21T00:00:00+00:00", retry_after_s: 7200 },
        },
      }),
    );
    const err = (await api("/admin/llm/check", { method: "POST" }).catch(
      (e: unknown) => e,
    )) as ApiError;
    expect(err.status).toBe(429);
    expect(err.details).toEqual({ reset_at: "2026-11-21T00:00:00+00:00", retry_after_s: 7200 });
  });

  it("handles non-JSON error bodies and network failures", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response("oops", { status: 502, statusText: "Bad Gateway" }),
    );
    await expect(api("/x")).rejects.toMatchObject({ status: 502, code: "http_error" });
    fetchMock.mockRejectedValueOnce(new TypeError("failed to fetch"));
    await expect(api("/x")).rejects.toMatchObject({ status: 0, code: "network_error" });
  });

  it("returns undefined for 204 responses", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(api("/x", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("raises the 'waking up' signal only for slow requests, then clears it", async () => {
    vi.useFakeTimers();
    const states: boolean[] = [];
    const off = onWakingChange((w) => states.push(w));
    let finish: (r: Response) => void = () => undefined;
    fetchMock.mockReturnValueOnce(new Promise<Response>((r) => (finish = r)));
    const p = api("/me");
    await vi.advanceTimersByTimeAsync(COLD_START_MS + 50);
    expect(states).toEqual([true]);
    finish(json(200, {}));
    await p;
    expect(states).toEqual([true, false]);

    states.length = 0;
    fetchMock.mockResolvedValueOnce(json(200, {}));
    await api("/fast");
    expect(states).toEqual([]); // a quick request never shows the banner
    off();
  });
});
