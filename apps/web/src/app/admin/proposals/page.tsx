import type { Metadata } from "next";

import { ProposalsReview } from "@/components/admin/proposals-review";

export const instant = false; // behind the client-side AdminGate (BUG-034)

export const metadata: Metadata = { title: "Proposals" };

export default function AdminProposalsPage() {
  return <ProposalsReview />;
}
