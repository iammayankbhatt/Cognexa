import type { Metadata } from "next";

import { AdminOverview } from "@/components/admin/admin-overview";

// Admin pages render only after the client-side role check (AdminGate), so prerendering
// intentionally omits them; opt out of instant-navigation validation (BUG-034).
export const instant = false;

export const metadata: Metadata = { title: "Overview" };

export default function AdminOverviewPage() {
  return <AdminOverview />;
}
