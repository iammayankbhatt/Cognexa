"use client";

import "./globals.css";

import { ThemeScript } from "@/components/theme/theme-script";

/**
 * Last-resort error page when the root layout itself fails. It replaces the whole document, so
 * it brings its own <html>, global styles and the theme script (Next.js docs: global-error).
 */
export default function GlobalError({ error, retry }: { error: unknown; retry: () => void }) {
  const digest =
    error instanceof Error && "digest" in error && typeof error.digest === "string"
      ? error.digest
      : null;
  return (
    <html lang="en" data-theme="neon-noir" suppressHydrationWarning>
      <head>
        <title>Something went wrong · Cognexa</title>
        <ThemeScript />
      </head>
      <body className="flex min-h-dvh items-center justify-center bg-bg px-6 text-text">
        <main role="alert" className="flex max-w-md flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-semibold">Cognexa hit an unexpected error</h1>
          <p className="text-sm text-muted">
            Reload to try again. If it keeps happening, the server may be waking up (it sleeps when
            idle on the free tier); wait a minute and retry.
          </p>
          {digest && <p className="font-mono text-xs text-muted">Error ID: {digest}</p>}
          <button
            type="button"
            onClick={() => retry()}
            className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-fg outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Try again
          </button>
        </main>
      </body>
    </html>
  );
}
