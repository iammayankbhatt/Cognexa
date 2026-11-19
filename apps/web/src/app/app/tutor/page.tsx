import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

export const metadata: Metadata = { title: "Tutor" };

export default function Page() {
  return (
    <ComingSoon
      title="Tutor"
      description="Ask a DSA question and get an answer grounded in the concept graph."
      phase={7}
    />
  );
}
