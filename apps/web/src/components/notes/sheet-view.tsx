"use client";

import { ArrowLeft, Download, Printer } from "lucide-react";
import Link from "next/link";

import { ErrorState } from "@/components/shared/error-state";
import { Markdown } from "@/components/tutor/markdown";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { sheetFileName, useSheet } from "@/lib/notes";

/** One revision sheet: Markdown with concept chips, download as .md, print-friendly view. */
export function SheetView({ sheetId }: { sheetId: string }) {
  const { data, isPending, error, refetch } = useSheet(sheetId);
  if (isPending) return <Skeleton className="mx-auto h-96 max-w-3xl" aria-label="Loading sheet" />;
  if (error || !data) {
    return (
      <ErrorState
        title="Couldn't open this sheet"
        message={error?.message}
        onRetry={() => void refetch()}
      />
    );
  }
  const download = () => {
    const blob = new Blob([data.content], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = sheetFileName(data);
    a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center gap-2 print:hidden">
        <Link href="/app/notes" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft aria-hidden className="size-4" /> Notes
        </Link>
        <span className="text-xs text-muted">{new Date(data.created_at).toLocaleString()}</span>
        <Button variant="outline" size="sm" className="ml-auto" onClick={download}>
          <Download aria-hidden className="size-4" /> Markdown
        </Button>
        <Button size="sm" onClick={() => window.print()}>
          <Printer aria-hidden className="size-4" /> Print / PDF
        </Button>
      </div>
      <article className="print-sheet rounded-2xl border border-border bg-surface p-6 sm:p-8">
        <Markdown text={data.content} />
      </article>
    </div>
  );
}
