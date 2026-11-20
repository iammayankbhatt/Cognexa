import type { Metadata } from "next";

import { GraphEditor } from "@/components/admin/graph-editor";

export const instant = false; // behind the client-side AdminGate (BUG-034)

export const metadata: Metadata = { title: "Graph editor" };

export default function AdminGraphPage() {
  return <GraphEditor />;
}
