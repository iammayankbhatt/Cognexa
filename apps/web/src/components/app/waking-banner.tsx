"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { onWakingChange, warmApi } from "@/lib/api";

/** Warms the API on load and explains the pause when the free-tier server is waking up. */
export function WakingBanner() {
  const [waking, setWaking] = useState(false);
  useEffect(() => {
    warmApi();
    return onWakingChange(setWaking);
  }, []);
  if (!waking) return null;
  return (
    <div
      role="status"
      className="flex items-center justify-center gap-2 border-b border-border bg-surface-2 px-4 py-2 text-sm text-text"
    >
      <Loader2 aria-hidden className="size-4 animate-spin text-accent" />
      Waking up the server. The first request after a quiet spell can take up to a minute.
    </div>
  );
}
