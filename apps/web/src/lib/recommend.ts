"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type Surface = "dashboard" | "tutor" | "quiz" | "review" | "learn";

export interface RecommendationItem {
  id: string | null;
  concept_id: string;
  name: string;
  rule: "R1" | "R2" | "R3" | "R4" | "R5" | "BASELINE";
  reason: string;
  action: "learn" | "practice" | "review";
  path: { source: string; target: string }[];
  names?: Record<string, string>;
}

export interface Recommendations {
  study_group: string;
  engine: "adaptive" | "baseline";
  items: RecommendationItem[];
}

export interface ReviewDue {
  due: {
    concept_id: string;
    name: string;
    effective: number;
    band: string;
    next_review_at: string;
    question_ids: string[];
  }[];
  next_due_at: string | null;
  scheduled: number;
  streak_days: number;
}

export const recKey = (surface: Surface) => ["recommendations", surface] as const;

export function useRecommendations(surface: Surface, limit = 3) {
  return useQuery({
    queryKey: [...recKey(surface), limit],
    queryFn: () => api<Recommendations>(`/recommendations?surface=${surface}&limit=${limit}`),
    staleTime: 60_000,
  });
}

export function useReviewDue() {
  return useQuery({ queryKey: ["review", "due"], queryFn: () => api<ReviewDue>("/review/due") });
}

/** Log that a recommendation was followed (study analysis); failures are ignored. */
export function useRecommendationClick() {
  return useMutation({
    mutationFn: (id: string) =>
      api<void>(`/recommendations/${id}/click`, { method: "POST" }).catch(() => undefined),
  });
}

/** Concept ids along a recommendation path, from the gap to the concept it unlocks. */
export function pathConcepts(path: RecommendationItem["path"]): string[] {
  if (!path.length) return [];
  return [path[0].source, ...path.map((e) => e.target)];
}

export const RULE_LABEL: Record<RecommendationItem["rule"], string> = {
  R1: "Fix the root cause",
  R2: "Focused review",
  R3: "Due for review",
  R4: "Next in the syllabus",
  R5: "Start here",
  BASELINE: "Next in the syllabus",
};
