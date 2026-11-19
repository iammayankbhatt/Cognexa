import type { Metadata } from "next";

import { LegalPage } from "@/components/marketing/legal-page";

export const metadata: Metadata = { title: "Terms" };

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of use"
      updated="19 November 2026"
      intro="By creating an account you agree to these terms. Cognexa is an educational project provided free of charge."
      sections={[
        {
          heading: "Educational use",
          body: [
            "Cognexa helps you study Data Structures & Algorithms. It is a learning aid, not a substitute for your course materials, teachers or textbooks.",
          ],
        },
        {
          heading: "AI answers can be wrong",
          body: [
            "Answers are written by a language model from the study notes we provide, and they cite the concepts used. They can still contain mistakes or miss nuance. Check important facts against a textbook, and use the report button if an answer looks wrong.",
          ],
        },
        {
          heading: "Fair use and limits",
          body: [
            "Each account has a daily and per-minute limit on AI requests, and there is a global daily cap, because we run on free tiers. Do not try to bypass the limits, overload the service, probe it for weaknesses or submit harmful or unlawful content.",
          ],
        },
        {
          heading: "Your account",
          body: [
            "Keep your password private. You can delete your account at any time from Settings. We may suspend accounts that abuse the service.",
          ],
        },
        {
          heading: "No warranty",
          body: [
            "The service is provided as is, without warranties of any kind, and may change, pause or stop without notice. To the extent the law allows, the project team is not liable for losses arising from its use.",
          ],
        },
      ]}
    />
  );
}
