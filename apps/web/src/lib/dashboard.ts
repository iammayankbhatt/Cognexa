"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Recommendations } from "@/lib/recommend";

export interface DashboardData {
  subject_id: string;
  overall_mastery: number;
  concepts_total: number;
  concepts_practised: number;
  bands: { weak: number; developing: number; strong: number; not_started: number };
  streak_days: number;
  time_on_task_minutes_7d: number;
  quizzes_this_week: number;
  tutor_questions_this_week: number;
  accuracy_trend: { date: string; accuracy: number | null; answers: number }[];
  per_cluster: { cluster: string; concepts: number; practised: number; mastery: number }[];
  weak_concepts: {
    concept_id: string;
    name: string;
    mastery: number | null;
    asked: number;
    fix: { concept_id: string; name: string } | null;
  }[];
  activity: (
    | {
        kind: "quiz";
        at: string;
        id: string;
        mode: string;
        concept_id: string | null;
        name: string | null;
        score: number;
        max_score: number;
      }
    | { kind: "question"; at: string; thread_id: string; text: string }
    | { kind: "note"; at: string; concept_id: string; name: string; bookmarked: boolean }
  )[];
  recommendations: Recommendations;
  review_due: number;
  usage_today: { ai_requests: number; daily_quota: number };
}

export interface MapNode {
  id: string;
  name: string;
  cluster: string;
  difficulty: number;
  order_index: number;
  description: string;
  mastery: number | null;
  band: "weak" | "developing" | "strong" | "not_started";
  attempts: number;
  last_practiced_at: string | null;
  next_review_at: string | null;
}

export interface MasteryGraph {
  subject_id: string;
  nodes: MapNode[];
  edges: { source: string; target: string; type: string }[];
}

export function useDashboard() {
  return useQuery({ queryKey: ["dashboard"], queryFn: () => api<DashboardData>("/dashboard") });
}

export function useMasteryGraph() {
  return useQuery({
    queryKey: ["graph", "mastery"],
    queryFn: () => api<MasteryGraph>("/graph/mastery"),
  });
}

/** "2 h ago", "yesterday", "3 days ago". */
export function timeAgo(iso: string, now: Date = new Date()): string {
  const s = Math.max(0, (now.getTime() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86_400) return `${Math.floor(s / 3600)} h ago`;
  const d = Math.floor(s / 86_400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}
