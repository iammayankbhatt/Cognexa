"use client";

import { cn } from "@/lib/utils";

/** Shared input styling for admin forms (theme tokens only). */
export const fieldClass =
  "w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  className,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  error?: string | null;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={htmlFor} className="block text-sm font-medium text-text">
        {label}
      </label>
      {children}
      {error ? (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-muted">{hint}</p>
      )}
    </div>
  );
}

/** "a, b, c" <-> ["a", "b", "c"] for alias / keyword inputs. */
export function splitList(text: string): string[] {
  return [
    ...new Set(
      text
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  ];
}

export function confidenceLabel(c: number | null): string {
  return c === null ? "—" : `${Math.round(c * 100)}%`;
}
