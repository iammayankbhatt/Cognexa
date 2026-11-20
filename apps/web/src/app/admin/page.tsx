import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

// Admin pages render only after the client-side role check (AdminGate), so prerendering
// intentionally omits them; opt out of instant-navigation validation (BUG-034).
export const instant = false;

export const metadata: Metadata = { title: "Overview" };

export default function AdminOverviewPage() {
  return (
    <ComingSoon
      title="Admin overview"
      description="Usage, moderation queue and system health. Manage people under Users."
      phase={11}
    />
  );
}
