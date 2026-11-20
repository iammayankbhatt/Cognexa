import type { Metadata } from "next";

import { AdminGate } from "@/components/app/admin-gate";

import { SettingsForm } from "./settings-form";

export const metadata: Metadata = { title: "AI settings" };

// Client page behind AdminGate (see admin/users/page.tsx): opt out of instant-navigation checks.
export const instant = false;

export default function AdminSettingsPage() {
  return (
    <AdminGate minimum="admin">
      <SettingsForm />
    </AdminGate>
  );
}
