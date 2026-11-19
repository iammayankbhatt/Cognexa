import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

export const metadata: Metadata = { title: "Notes" };

export default function Page() {
  return (
    <ComingSoon
      title="Notes"
      description="Your notes, bookmarks and personalised revision sheets."
      phase={10}
    />
  );
}
