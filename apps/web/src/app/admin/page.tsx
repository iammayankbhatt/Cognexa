import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

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
