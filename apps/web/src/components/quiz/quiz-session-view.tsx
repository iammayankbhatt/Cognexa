"use client";

import { useQueryClient } from "@tanstack/react-query";

import { QuizPlayer } from "@/components/quiz/quiz-player";
import { QuizResults } from "@/components/quiz/quiz-results";
import { ErrorState } from "@/components/shared/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { quizKey, useQuizSession } from "@/lib/quiz/use-quiz";

/** A quiz: the player while it is open, the results once it is submitted. */
export function QuizSessionView({ sessionId }: { sessionId: string }) {
  const qc = useQueryClient();
  const { data, error, isPending, refetch } = useQuizSession(sessionId);
  if (isPending) {
    return (
      <div className="mx-auto max-w-3xl space-y-4" aria-label="Loading quiz">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error || !data) {
    return (
      <ErrorState
        title="Couldn't open this quiz"
        message={error?.message}
        requestId={error instanceof ApiError ? error.requestId : undefined}
        onRetry={() => void refetch()}
      />
    );
  }
  if (data.submitted_at) return <QuizResults session={data} />;
  return <QuizPlayer session={data} onFinished={(s) => qc.setQueryData(quizKey(sessionId), s)} />;
}
