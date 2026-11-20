import type { Metadata } from "next";

import { AdminGate } from "@/components/app/admin-gate";

import { StudyConsole } from "@/components/admin/study-console";

// Admin pages render only after the client-side role check (AdminGate), so prerendering
// intentionally omits them; opt out of instant-navigation validation (BUG-034).
export const instant = false;

export const metadata: Metadata = { title: "User study" };

export default function Page() {
  return (
    <AdminGate minimum="admin">
      <StudyConsole />
    </AdminGate>
  );
}
