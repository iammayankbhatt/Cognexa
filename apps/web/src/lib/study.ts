"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";

export type StudyStep =
  "off" | "consent" | "pretest" | "learning" | "posttest" | "complete" | "withdrawn";

interface TestView {
  session_id: string;
  submitted: boolean;
  score: number | null;
  max_score: number | null;
}

export interface StudyState {
  enabled: boolean;
  step: StudyStep;
  group: string;
  enrolled_at: string | null;
  consent_at: string | null;
  pretest: TestView | null;
  posttest: TestView | null;
  posttest_unlock_at: string | null;
  pretest_minutes: number;
}

export interface AdminStudy {
  enabled: boolean;
  assignment: "random" | "alternate";
  posttest_unlock_at: string | null;
  posttest_after_days: number;
  pretest_minutes: number;
  started_at: string | null;
  funnel: Record<string, Record<string, number>>;
}

export const STUDY_KEY = ["study", "me"] as const;

export function useStudy() {
  return useQuery({
    queryKey: STUDY_KEY,
    queryFn: () => api<StudyState>("/study/me"),
    staleTime: 30_000,
  });
}

export function useStudyActions() {
  const qc = useQueryClient();
  const done = (s: StudyState) => {
    qc.setQueryData(STUDY_KEY, s);
    void qc.invalidateQueries({ queryKey: ["me"] });
    void qc.invalidateQueries({ queryKey: ["recommendations"] });
    void qc.invalidateQueries({ queryKey: ["dashboard"] });
  };
  const consent = useMutation({
    mutationFn: () => api<StudyState>("/study/consent", { method: "POST" }),
    onSuccess: done,
  });
  const withdraw = useMutation({
    mutationFn: () => api<StudyState>("/study/withdraw", { method: "POST" }),
    onSuccess: done,
  });
  return { consent, withdraw };
}

/** Words for the current step, used by the dashboard banner and the study page. */
export function stepText(s: StudyState, now: Date = new Date()): { title: string; body: string } {
  switch (s.step) {
    case "consent":
      return {
        title: "You're invited to a short study",
        body: "Help evaluate Cognexa: read what it involves and decide.",
      };
    case "pretest":
      return {
        title: "Take the pre-test",
        body: `20 questions, ${s.pretest_minutes} minutes, no AI help. It sets your starting point.`,
      };
    case "learning": {
      const when = s.posttest_unlock_at ? new Date(s.posttest_unlock_at) : null;
      const days = when
        ? Math.max(0, Math.ceil((when.getTime() - now.getTime()) / 86_400_000))
        : null;
      return {
        title: "Learning period",
        body:
          days === null
            ? "Use Cognexa as you normally would."
            : `Use Cognexa as you normally would. The post-test opens in ${days} day${days === 1 ? "" : "s"}.`,
      };
    }
    case "posttest":
      return {
        title: "The post-test is open",
        body: "20 new questions, same length as the pre-test. It completes your part of the study.",
      };
    case "complete":
      return {
        title: "Thank you for taking part",
        body: "Your part of the study is complete. Keep using Cognexa as much as you like.",
      };
    default:
      return { title: "", body: "" };
  }
}
