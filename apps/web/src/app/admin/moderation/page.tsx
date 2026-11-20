import type { Metadata } from "next";

import { ModerationQueue } from "@/components/admin/moderation-queue";

export const instant = false; // behind the client-side AdminGate (BUG-034)

export const metadata: Metadata = { title: "Moderation" };

export default function AdminModerationPage() {
  return <ModerationQueue />;
}
