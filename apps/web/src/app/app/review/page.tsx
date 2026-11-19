import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

export const metadata: Metadata = { title: "Review" };

export default function Page() {
  return (
    <ComingSoon
      title="Review"
      description="Spaced review of the concepts you are about to forget."
      phase={9}
    />
  );
}
