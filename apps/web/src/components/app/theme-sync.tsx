"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import type { Body } from "@/lib/api-contract";
import { ME_KEY, useMe } from "@/components/app/me-provider";
import { useTheme } from "@/components/theme/theme-provider";
import { api, type Me } from "@/lib/api";
import { isThemeId } from "@/lib/themes";

/**
 * Keeps the colour theme in sync with the profile. The profile wins on first load (so the
 * theme follows the user across devices); after that, every change the user makes is saved.
 */
export function ThemeSync() {
  const { data: me } = useMe();
  const { theme, setTheme } = useTheme();
  const qc = useQueryClient();
  const applied = useRef(false);
  const saved = useRef<string | null>(null);

  useEffect(() => {
    if (!me || applied.current) return;
    applied.current = true;
    saved.current = me.theme;
    if (isThemeId(me.theme) && me.theme !== theme) setTheme(me.theme);
  }, [me, theme, setTheme]);

  useEffect(() => {
    if (!applied.current || saved.current === theme) return;
    saved.current = theme;
    void api<Me>("/me", { method: "PATCH", body: { theme } satisfies Body<"MePatch"> })
      .then((next) => qc.setQueryData(ME_KEY, next))
      .catch(() => undefined); // offline: the theme still applies locally
  }, [theme, qc]);

  return null;
}
