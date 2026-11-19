import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

export const metadata: Metadata = { title: "Learn" };

export default function Page() {
  return (
    <ComingSoon
      title="Learn"
      description="Browse concepts, notes and the prerequisite map."
      phase={8}
    />
  );
}
