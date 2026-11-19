"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { friendlyAuthError } from "@/lib/auth-schemas";
import { getSupabase } from "@/lib/supabase/client";

export function Divider() {
  return (
    <div className="flex items-center gap-3 text-xs text-muted" aria-hidden>
      <span className="h-px flex-1 bg-border" /> or <span className="h-px flex-1 bg-border" />
    </div>
  );
}

export function GoogleButton({ next, onError }: { next: string; onError: (m: string) => void }) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      type="button"
      variant="outline"
      className="h-9 w-full"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        const { error } = await getSupabase().auth.signInWithOAuth({
          provider: "google",
          options: {
            redirectTo: `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`,
          },
        });
        if (error) {
          setBusy(false);
          onError(
            friendlyAuthError(
              error.code,
              "Google sign-in isn't available right now. Use email and password instead.",
            ),
          );
        }
      }}
    >
      <span
        aria-hidden
        className="flex size-4 items-center justify-center rounded-full border border-current text-[10px] leading-none font-bold"
      >
        G
      </span>
      {busy ? "Opening Google…" : "Continue with Google"}
    </Button>
  );
}
