import type { Metadata } from "next";

import { AdminGate } from "@/components/app/admin-gate";

import { UsageDashboard } from "./usage-dashboard";

export const metadata: Metadata = { title: "AI usage" };

// Client page behind AdminGate (see admin/users/page.tsx): opt out of instant-navigation checks.
export const instant = false;

export default function AdminUsagePage() {
  return (
    <AdminGate minimum="admin">
      <UsageDashboard />
    </AdminGate>
  );
}
