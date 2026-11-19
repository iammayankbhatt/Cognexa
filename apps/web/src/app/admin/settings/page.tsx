import type { Metadata } from "next";

import { SettingsForm } from "./settings-form";

export const metadata: Metadata = { title: "AI settings" };

// Client page behind AdminGate (see admin/users/page.tsx): opt out of instant-navigation checks.
export const instant = false;

export default function AdminSettingsPage() {
  return <SettingsForm />;
}
