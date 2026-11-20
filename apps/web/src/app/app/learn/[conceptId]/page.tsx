import type { Metadata } from "next";
import { Suspense } from "react";

import { ConceptPageView } from "@/components/learn/concept-page";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Concept" };

async function Concept({ params }: { params: Promise<{ conceptId: string }> }) {
  const { conceptId } = await params;
  return <ConceptPageView conceptId={conceptId} />;
}

export default function Page({ params }: PageProps<"/app/learn/[conceptId]">) {
  // The id is request data (cacheComponents): read it inside a Suspense boundary.
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" aria-label="Loading concept" />}>
      <Concept params={params} />
    </Suspense>
  );
}
