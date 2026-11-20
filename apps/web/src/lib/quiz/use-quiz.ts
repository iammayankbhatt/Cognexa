"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  AnswerView,
  ConceptPage,
  CreateQuizBody,
  MasteryView,
  QuizHistory,
  QuizSession,
  ResponseValue,
} from "@/lib/quiz/types";

export const MASTERY_KEY = ["me", "mastery"] as const;
export const quizKey = (id: string) => ["quiz", id] as const;
export const conceptKey = (id: string) => ["concept", id] as const;

export function useMastery() {
  return useQuery({
    queryKey: MASTERY_KEY,
    queryFn: () => api<MasteryView>("/me/mastery"),
    staleTime: 30_000,
  });
}

export function useConceptPage(id: string) {
  return useQuery({
    queryKey: conceptKey(id),
    queryFn: () => api<ConceptPage>(`/concepts/${encodeURIComponent(id)}`),
  });
}

export function useQuizHistory() {
  return useQuery({
    queryKey: ["quiz", "history"],
    queryFn: () => api<QuizHistory>("/quiz/history?page_size=50"),
  });
}

export function useQuizSession(id: string) {
  return useQuery({
    queryKey: quizKey(id),
    queryFn: () => api<QuizSession>(`/quiz/sessions/${id}`),
    staleTime: Infinity,
  });
}

export function useCreateQuiz() {
  return useMutation({
    mutationFn: (body: CreateQuizBody) =>
      api<QuizSession>("/quiz/sessions", { method: "POST", body }),
  });
}

/** Mastery, history and concept pages change after grading. */
function useRefreshLearning() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: MASTERY_KEY });
    void qc.invalidateQueries({ queryKey: ["quiz", "history"] });
    void qc.invalidateQueries({ queryKey: ["concept"] });
    void qc.invalidateQueries({ queryKey: ["me"] });
    void qc.invalidateQueries({ queryKey: ["tutor", "suggestions"] });
    void qc.invalidateQueries({ queryKey: ["recommendations"] });
    void qc.invalidateQueries({ queryKey: ["review"] });
  };
}

export function useAnswer(sessionId: string) {
  const refresh = useRefreshLearning();
  return useMutation({
    mutationFn: (body: { question_id: string; response: ResponseValue; time_ms?: number }) =>
      api<AnswerView>(`/quiz/sessions/${sessionId}/answers`, { method: "POST", body }),
    onSuccess: (a) => {
      if (!a.saved) refresh();
    },
  });
}

export function useSubmit(sessionId: string) {
  const qc = useQueryClient();
  const refresh = useRefreshLearning();
  return useMutation({
    mutationFn: (responses: Record<string, ResponseValue>) =>
      api<QuizSession>(`/quiz/sessions/${sessionId}/submit`, {
        method: "POST",
        body: { responses },
      }),
    onSuccess: (s) => {
      qc.setQueryData(quizKey(sessionId), s);
      refresh();
    },
  });
}

export function useRegrade(sessionId: string) {
  const qc = useQueryClient();
  const refresh = useRefreshLearning();
  return useMutation({
    mutationFn: () => api<QuizSession>(`/quiz/sessions/${sessionId}/regrade`, { method: "POST" }),
    onSuccess: (s) => {
      qc.setQueryData(quizKey(sessionId), s);
      refresh();
    },
  });
}

/** Has the student given an answer of the right shape (not empty)? */
export function isAnswered(value: ResponseValue | undefined): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim().length > 0;
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

export const MODE_LABEL: Record<string, string> = {
  concept: "Concept quiz",
  adaptive: "Smart quiz",
  review: "Review",
  diagnostic: "Diagnostic",
  pretest: "Pre-test",
  posttest: "Post-test",
};
