import type { Metadata } from "next";

import { AppShell } from "@/components/app/app-shell";

export const metadata: Metadata = { title: { default: "App", template: "%s · Cognexa" } };

export default function AppLayout({ children }: LayoutProps<"/app">) {
  return <AppShell>{children}</AppShell>;
}
