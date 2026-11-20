"use client";

import dynamic from "next/dynamic";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Recharts is about 100 KB of JavaScript; it is loaded only when a chart is on screen, so the
 * rest of the page becomes interactive first (Phase 13 performance).
 */
const chartSkeleton = () => <Skeleton className="h-56 w-full" aria-label="Loading chart" />;

export const AccuracyTrend = dynamic(
  () => import("@/components/dashboard/charts").then((m) => m.AccuracyTrend),
  { ssr: false, loading: chartSkeleton },
);

export const ClusterBars = dynamic(
  () => import("@/components/dashboard/charts").then((m) => m.ClusterBars),
  { ssr: false, loading: chartSkeleton },
);

export const UsageChart = dynamic(
  () => import("@/components/app/usage-chart").then((m) => m.UsageChart),
  { ssr: false, loading: chartSkeleton },
);
