import type { Metadata } from "next";
import { Suspense } from "react";

import { TutorWorkspace } from "@/components/tutor/tutor-workspace";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Tutor" };

export default function Page() {
  return (
    <Suspense fallback={<Skeleton className="m-6 h-[60vh]" aria-label="Loading tutor" />}>
      <TutorWorkspace />
    </Suspense>
  );
}
