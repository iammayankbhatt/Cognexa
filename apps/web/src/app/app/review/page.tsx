import type { Metadata } from "next";

import { ReviewPage } from "@/components/recommend/review-page";

export const metadata: Metadata = { title: "Review" };

export default function Page() {
  return <ReviewPage />;
}
