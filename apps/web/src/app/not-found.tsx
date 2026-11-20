import { Compass } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";

export const metadata: Metadata = { title: "Page not found" };

/** Designed 404 for any unknown URL (and for notFound() calls in pages). */
export default function NotFound() {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-bg px-6 py-16 text-text">
      <div className="flex max-w-md flex-col items-center gap-4 text-center">
        <span
          aria-hidden
          className="flex size-14 items-center justify-center rounded-full bg-surface-2 text-accent"
        >
          <Compass className="size-7" />
        </span>
        <p className="font-mono text-sm text-muted">404</p>
        <h1 className="text-2xl font-semibold">This page is not on the map</h1>
        <p className="text-sm text-muted">
          The link may be old or mistyped. Every concept is still reachable from the knowledge map.
        </p>
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          <Link href="/app" className={buttonVariants()}>
            Go to your dashboard
          </Link>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            Home page
          </Link>
        </div>
      </div>
    </main>
  );
}
