"use client";

import { ShieldAlert } from "lucide-react";
import Link from "next/link";

import { useMe } from "@/components/app/me-provider";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";

/**
 * UI-side role check for /admin. It only decides what to render: every admin API call is
 * checked again on the server (403 for non-admins), so this is never the security boundary.
 */
export function AdminGate({
  children,
  minimum = "admin",
}: {
  children: React.ReactNode;
  minimum?: "reviewer" | "admin";
}) {
  const { data: me, isPending } = useMe();
  if (isPending) return <Skeleton className="h-40 w-full" aria-label="Checking permissions" />;
  const rank = { student: 0, reviewer: 1, admin: 2 } as const;
  if (!me || rank[me.role] < rank[minimum]) {
    return (
      <EmptyState
        icon={<ShieldAlert />}
        title="403: Not allowed"
        description={
          minimum === "admin"
            ? "This area is only available to administrators."
            : "This area is only available to reviewers and administrators."
        }
        action={
          <Link href="/app" className={buttonVariants({ variant: "outline" })}>
            Back to dashboard
          </Link>
        }
      />
    );
  }
  return <>{children}</>;
}
