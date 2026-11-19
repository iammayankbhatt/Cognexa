"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";

import { DEFAULT_THEME, THEME_STORAGE_KEY, isThemeId, type ThemeId } from "@/lib/themes";

interface ThemeContextValue {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

function getSnapshot(): ThemeId {
  const attr = document.documentElement.getAttribute("data-theme");
  return isThemeId(attr) ? attr : DEFAULT_THEME;
}

const getServerSnapshot = (): ThemeId => DEFAULT_THEME;

/**
 * The source of truth is the data-theme attribute (set before paint by ThemeScript).
 * Persistence is localStorage for now; syncing to the user profile arrives in Phase 4.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  const setTheme = useCallback((next: ThemeId) => {
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Storage can be unavailable (private mode); the theme still applies for this page view.
    }
    listeners.forEach((l) => l());
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
