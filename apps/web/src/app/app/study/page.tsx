import type { Metadata } from "next";

import { StudyPage } from "@/components/study/study-page";

export const metadata: Metadata = { title: "Study" };

export default function Page() {
  return <StudyPage />;
}
