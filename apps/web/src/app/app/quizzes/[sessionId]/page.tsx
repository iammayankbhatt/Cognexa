import type { Metadata } from "next";
import { Suspense } from "react";

import { QuizSessionView } from "@/components/quiz/quiz-session-view";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Quiz" };

async function Session({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <QuizSessionView sessionId={sessionId} />;
}

export default function Page({ params }: PageProps<"/app/quizzes/[sessionId]">) {
  // The id is request data (cacheComponents): read it inside a Suspense boundary.
  return (
    <Suspense fallback={<Skeleton className="mx-auto h-64 max-w-3xl" aria-label="Loading quiz" />}>
      <Session params={params} />
    </Suspense>
  );
}
