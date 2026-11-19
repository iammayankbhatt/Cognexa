"use client";

import { Check } from "lucide-react";

import { useTheme } from "@/components/theme/theme-provider";
import { THEMES } from "@/lib/themes";
import { cn } from "@/lib/utils";

/** Segmented radio group for choosing a theme. Each swatch is scoped to its own theme's variables. */
export function ThemeSwitcher({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Colour theme"
      className={cn("inline-flex gap-1 rounded-lg border border-border bg-surface p-1", className)}
    >
      {THEMES.map((t) => {
        const active = t.id === theme;
        return (
          <button
            key={t.id}
            type="button"
            role="radio"
            aria-checked={active}
            title={t.description}
            onClick={() => setTheme(t.id)}
            className={cn(
              "inline-flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active ? "bg-surface-2 text-text" : "text-muted hover:text-text",
            )}
          >
            <span
              aria-hidden
              data-theme={t.id}
              className="size-4 rounded-full border border-border bg-[linear-gradient(135deg,var(--bg)_50%,var(--primary)_50%)]"
            />
            <span className="hidden sm:inline">{t.label}</span>
            {active && <Check aria-hidden className="size-3.5 text-accent" />}
          </button>
        );
      })}
    </div>
  );
}
