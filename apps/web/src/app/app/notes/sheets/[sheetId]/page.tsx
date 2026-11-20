import type { Metadata } from "next";
import { Suspense } from "react";

import { SheetView } from "@/components/notes/sheet-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Revision sheet" };

async function Sheet({ params }: { params: Promise<{ sheetId: string }> }) {
  const { sheetId } = await params;
  return <SheetView sheetId={sheetId} />;
}

export default function Page({ params }: PageProps<"/app/notes/sheets/[sheetId]">) {
  // The id is request data (cacheComponents): read it inside a Suspense boundary.
  return (
    <Suspense fallback={<Skeleton className="mx-auto h-96 max-w-3xl" aria-label="Loading sheet" />}>
      <Sheet params={params} />
    </Suspense>
  );
}
