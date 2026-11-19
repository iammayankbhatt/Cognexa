"use client";

import { BookOpen, ClipboardCheck, MessageSquareText, Sparkles } from "lucide-react";
import Link from "next/link";

import { useMe } from "@/components/app/me-provider";
import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { StatCard } from "@/components/shared/stat-card";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function DashboardPage() {
  const { data: me, isPending } = useMe();

  if (isPending) {
    return (
      <div className="space-y-6" aria-busy="true" aria-label="Loading dashboard">
        <Skeleton className="h-24 w-full" />
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      </div>
    );
  }
  if (!me) return null;
  const first = (me.display_name ?? "there").split(" ")[0];

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Dashboard"
        title={`Welcome, ${first}`}
        description="Your progress, weak spots and recommended next steps will appear here as you learn."
        actions={
          <Link href="/app/tutor" className={cn(buttonVariants({ variant: "default" }))}>
            <MessageSquareText aria-hidden /> Ask the tutor
          </Link>
        }
      />
      <section aria-label="Today" className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="AI requests today"
          value={`${me.usage.ai_requests}/${me.usage.daily_quota}`}
          hint="Resets at midnight UTC"
          icon={<Sparkles />}
        />
        <StatCard
          label="Concepts practised"
          value={0}
          hint="Take a quiz to start"
          icon={<ClipboardCheck />}
        />
        <StatCard
          label="Concepts explored"
          value={0}
          hint="Open any concept to begin"
          icon={<BookOpen />}
        />
      </section>
      <EmptyState
        icon={<ClipboardCheck />}
        title="No activity yet"
        description="Once you ask the tutor questions or take quizzes, your mastery map and recommendations show up here."
      />
    </div>
  );
}
