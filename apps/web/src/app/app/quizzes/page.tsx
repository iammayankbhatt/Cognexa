import type { Metadata } from "next";

import { ComingSoon } from "@/components/app/coming-soon";

export const metadata: Metadata = { title: "Quizzes" };

export default function Page() {
  return (
    <ComingSoon
      title="Quizzes"
      description="Practise concepts, take adaptive quizzes and track mastery."
      phase={8}
    />
  );
}
