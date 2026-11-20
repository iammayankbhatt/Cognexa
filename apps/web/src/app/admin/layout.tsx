import type { Metadata } from "next";
import { Suspense } from "react";

import { AdminGate } from "@/components/app/admin-gate";
import { AppShell } from "@/components/app/app-shell";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: { default: "Admin", template: "%s · Admin · Cognexa" } };

export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  // Same reason as the /app layout: the shell reads the pathname, which is request data on
  // routes with dynamic segments.
  return (
    <Suspense fallback={<Skeleton className="m-6 h-64" aria-label="Loading" />}>
      <AppShell>
        <AdminGate>{children}</AdminGate>
      </AppShell>
    </Suspense>
  );
}
