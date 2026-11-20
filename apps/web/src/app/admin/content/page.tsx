import type { Metadata } from "next";
import { Suspense } from "react";

import { ContentEditor } from "@/components/admin/content-editor";
import { Skeleton } from "@/components/ui/skeleton";

export const instant = false; // behind the client-side AdminGate (BUG-034)

export const metadata: Metadata = { title: "Content" };

export default function AdminContentPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" aria-label="Loading content" />}>
      <ContentEditor />
    </Suspense>
  );
}
