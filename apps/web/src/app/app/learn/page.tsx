import type { Metadata } from "next";
import { Suspense } from "react";

import { LearnLibrary } from "@/components/learn/learn-library";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Learn" };

export default function Page() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" aria-label="Loading concepts" />}>
      <LearnLibrary />
    </Suspense>
  );
}
