import type { Metadata } from "next";

import { LegalPage } from "@/components/marketing/legal-page";

export const metadata: Metadata = { title: "Privacy" };

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy"
      updated="19 November 2026"
      intro="Cognexa is a student project. This page says plainly what we collect, who processes it and how you can remove it."
      sections={[
        {
          heading: "What we store",
          body: [
            "Your email address and display name (through our sign-in provider, Supabase), your chosen theme and experience level, your quiz answers and mastery scores, your tutor conversations and notes, and counts of how many AI requests you make each day.",
            "We do not use advertising or third-party analytics trackers. Sign-in uses cookies that keep you signed in; a small preference (the colour theme) is also kept in your browser.",
          ],
        },
        {
          heading: "AI providers process your questions",
          body: [
            "When you ask the tutor something, the text of your question and the relevant study notes are sent to a large-language-model provider to write the answer. Our primary provider is Groq; if it is unavailable we fall back to Google's Gemini API.",
            "We do not send your name or email address to these providers. Do not put personal or sensitive information into your questions. Google's free Gemini tier may use prompts and responses to improve its products, so avoid submitting anything you would not want used that way.",
          ],
        },
        {
          heading: "Where it lives",
          body: [
            "Account and learning data are stored in a Supabase Postgres database. The concept graph and study notes are stored in a Neo4j database. The website is hosted on Vercel and the API on Render. Each acts as a processor for us under its own terms.",
          ],
        },
        {
          heading: "Your controls",
          body: [
            "Settings, then Your data, lets you download everything we hold about you as a JSON file and permanently delete your account. Deleting your account removes your profile, quiz history, mastery, conversations and notes.",
            "A small record that an account was deleted (with no personal content) is kept in our audit log so administrators can see that the action happened.",
          ],
        },
        {
          heading: "Contact",
          body: [
            "Questions or requests about your data can be sent to the project team listed on the About page.",
          ],
        },
      ]}
    />
  );
}
