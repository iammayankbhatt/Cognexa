import type { Metadata } from "next";

import { EvaluationConsole } from "@/components/admin/evaluation-console";

// Admin pages render only after the client-side role check (AdminGate), so prerendering
// intentionally omits them; opt out of instant-navigation validation (BUG-034).
export const instant = false;

export const metadata: Metadata = { title: "Evaluation" };

export default function Page() {
  return <EvaluationConsole />;
}
