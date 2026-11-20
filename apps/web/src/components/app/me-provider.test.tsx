import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ME_KEY, useMe } from "@/components/app/me-provider";

vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/supabase/client", () => ({ getSupabase: () => ({ auth: {} }) }));

function Probe() {
  const { data, isPending } = useMe();
  return <p>{isPending || !data ? "loading" : `hi ${data.display_name}`}</p>;
}

function wrap(client: QueryClient) {
  return (
    <QueryClientProvider client={client}>
      <Probe />
    </QueryClientProvider>
  );
}

describe("useMe hydration (BUG-026)", () => {
  it("matches the server HTML even when /me is already cached on the client", async () => {
    const html = renderToString(wrap(new QueryClient()));
    expect(html).toContain("loading");

    const client = new QueryClient();
    client.setQueryData(ME_KEY, { display_name: "Ada" });
    const container = document.createElement("div");
    container.innerHTML = html;
    const recoverable = vi.fn();
    await act(async () => {
      hydrateRoot(container, wrap(client), { onRecoverableError: recoverable });
    });
    expect(recoverable).not.toHaveBeenCalled();
    expect(container.textContent).toBe("hi Ada"); // shown right after hydration
  });
});
