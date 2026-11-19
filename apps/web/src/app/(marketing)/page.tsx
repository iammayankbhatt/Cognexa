import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { FailureCase } from "@/components/marketing/failure-case";
import { GraphBackground } from "@/components/marketing/graph-background";
import { Comparison, FeatureGrid, Pipeline } from "@/components/marketing/sections";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  intro?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <p className="text-xs font-semibold tracking-widest text-accent uppercase">{eyebrow}</p>
      <h2 className="mt-2 max-w-2xl text-3xl font-semibold tracking-tight text-balance text-text">
        {title}
      </h2>
      {intro && <p className="mt-3 max-w-2xl text-muted">{intro}</p>}
      <div className="mt-8">{children}</div>
    </section>
  );
}

export default function LandingPage() {
  const showDesign = process.env.NODE_ENV !== "production";
  return (
    <>
      <section className="relative isolate overflow-hidden border-b border-border">
        <GraphBackground className="absolute inset-0 -z-10 size-full opacity-60" />
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-transparent via-bg/40 to-bg" />
        <div className="mx-auto flex max-w-4xl flex-col items-center gap-6 px-4 py-24 text-center sm:px-6 sm:py-32">
          <p className="rounded-full border border-border bg-surface/80 px-3 py-1 text-xs text-muted">
            GraphRAG tutoring for Data Structures &amp; Algorithms
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-balance text-text sm:text-6xl">
            Cognexa finds the prerequisite you didn&apos;t know to ask about
          </h1>
          <p className="max-w-2xl text-lg text-balance text-muted">
            Ask about a crash, a wrong output or a concept. Cognexa maps your question onto a graph
            of 69 DSA concepts, walks back to what you are missing and explains it from vetted
            notes.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              prefetch={false}
              href="/signup"
              className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-base")}
            >
              Start learning free <ArrowRight aria-hidden />
            </Link>
            <Link
              href="/how-it-works"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "h-11 px-5 text-base",
              )}
            >
              How it works
            </Link>
          </div>
        </div>
      </section>

      <Section
        eyebrow="The failure case"
        title="Plain search answers the question you typed, not the one you needed"
        intro="A student whose recursive function overflows never says the word “stack”. That is exactly where similarity search runs dry."
      >
        <FailureCase />
      </Section>

      <Section
        id="pipeline"
        eyebrow="How it works"
        title="Five steps from a vague question to a grounded answer"
      >
        <Pipeline />
      </Section>

      <Section eyebrow="Features" title="A tutor, a quiz engine and a study plan on one graph">
        <FeatureGrid />
      </Section>

      <Section
        eyebrow="Comparison"
        title="Plain RAG versus Cognexa"
        intro="Both use the same notes. The difference is the graph that connects them."
      >
        <Comparison />
      </Section>

      <section className="border-t border-border bg-surface">
        <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 px-4 py-16 text-center sm:px-6">
          <h2 className="text-3xl font-semibold tracking-tight text-balance text-text">
            Learn the thing underneath the thing
          </h2>
          <p className="text-muted">Free to use. No credit card. Sign up in a minute.</p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              prefetch={false}
              href="/signup"
              className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-base")}
            >
              Create your account
            </Link>
            {showDesign && (
              <Link
                href="/design"
                className={cn(buttonVariants({ variant: "outline", size: "lg" }), "h-11")}
              >
                Design reference
              </Link>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
