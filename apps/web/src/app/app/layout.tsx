import type { Metadata } from "next";
import { Suspense } from "react";

import { AppShell } from "@/components/app/app-shell";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: { default: "App", template: "%s · Cognexa" } };

/** Shown while the shell streams in on routes with dynamic segments (cacheComponents). */
function ShellFallback() {
  return (
    <div className="flex min-h-dvh bg-bg" aria-label="Loading">
      <div className="hidden w-60 border-r border-border bg-surface md:block" />
      <div className="flex-1 space-y-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

export default function AppLayout({ children }: LayoutProps<"/app">) {
  // The shell reads the pathname (active nav item); on dynamic routes such as
  // /app/learn/[conceptId] that is request data, so it must sit inside a Suspense boundary.
  return (
    <Suspense fallback={<ShellFallback />}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}
