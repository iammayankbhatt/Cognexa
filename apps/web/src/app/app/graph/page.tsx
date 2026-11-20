import type { Metadata } from "next";

import { KnowledgeMap } from "@/components/graph/knowledge-map";

export const metadata: Metadata = { title: "Knowledge map" };

export default function Page() {
  return <KnowledgeMap />;
}
