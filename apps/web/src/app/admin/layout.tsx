import type { Metadata } from "next";

import { AdminGate } from "@/components/app/admin-gate";
import { AppShell } from "@/components/app/app-shell";

export const metadata: Metadata = { title: { default: "Admin", template: "%s · Admin · Cognexa" } };

export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return (
    <AppShell>
      <AdminGate>{children}</AdminGate>
    </AppShell>
  );
}
