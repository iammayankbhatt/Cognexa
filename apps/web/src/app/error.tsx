"use client";

import { TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect } from "react";

import { Button, buttonVariants } from "@/components/ui/button";

/** Error boundary for every route below the root layout (designed 500 page). */
export default function RouteError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  // Server errors arrive with a digest that matches the server log; never show raw messages.
  const digest =
    error instanceof Error && "digest" in error && typeof error.digest === "string"
      ? error.digest
      : null;
  return (
    <main
      role="alert"
      className="flex min-h-[60vh] items-center justify-center bg-bg px-6 py-16 text-text"
    >
      <div className="flex max-w-md flex-col items-center gap-4 text-center">
        <span
          aria-hidden
          className="flex size-14 items-center justify-center rounded-full bg-danger/10 text-danger"
        >
          <TriangleAlert className="size-7" />
        </span>
        <h1 className="text-2xl font-semibold">Something went wrong on this page</h1>
        <p className="text-sm text-muted">
          Your progress is saved. Try again, or go back to the dashboard.
        </p>
        {digest && (
          <p className="font-mono text-xs text-muted">
            Error ID: <span className="text-text">{digest}</span>
          </p>
        )}
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          <Button onClick={() => retry()}>Try again</Button>
          <Link href="/app" className={buttonVariants({ variant: "outline" })}>
            Dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
