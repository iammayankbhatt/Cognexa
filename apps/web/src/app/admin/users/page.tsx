import type { Metadata } from "next";

import { AdminUsersTable } from "./users-table";

export const metadata: Metadata = { title: "Users" };

// AdminGate (in the admin layout) deliberately does not render this segment for
// non-admins, so the dev-only instant-navigation validator cannot see it and reports a
// "dropped segment". The page is fully client-side behind the gate; opt it out.
export const instant = false;

export default function AdminUsersPage() {
  return <AdminUsersTable />;
}
