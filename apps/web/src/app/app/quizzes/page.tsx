import type { Metadata } from "next";

import { QuizHome } from "@/components/quiz/quiz-home";

export const metadata: Metadata = { title: "Quizzes" };

export default function Page() {
  return <QuizHome />;
}
