import type { Metadata } from "next";

import { LiveGraph } from "@/components/marketing/live-graph";
import { Pipeline } from "@/components/marketing/sections";

export const metadata: Metadata = {
  title: "How it works",
  description: "GraphRAG, the DSA knowledge graph, the recommender and how Cognexa is evaluated.",
};

function Block({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="space-y-4">
      <h2 className="text-2xl font-semibold tracking-tight text-text">{title}</h2>
      <div className="space-y-3 text-muted [&_strong]:text-text">{children}</div>
    </section>
  );
}

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-14 px-4 py-14 sm:px-6">
      <header className="space-y-3">
        <p className="text-xs font-semibold tracking-widest text-accent uppercase">How it works</p>
        <h1 className="text-4xl font-semibold tracking-tight text-balance text-text">
          A tutor that reasons over a map of what you need to know
        </h1>
        <p className="max-w-2xl text-lg text-muted">
          Cognexa combines a prerequisite knowledge graph with retrieval-augmented generation, and
          uses the same graph to decide what you should study next.
        </p>
      </header>

      <Block id="graphrag" title="GraphRAG in five steps">
        <p>
          A normal retrieval system finds text that looks like your question. Cognexa first decides
          which <strong>concept</strong> your question is about, then walks the graph to gather that
          concept&apos;s notes <strong>plus the notes of its prerequisites</strong>, and only then
          asks the language model to answer from that material.
        </p>
        <Pipeline />
        <p>
          The model is told to answer only from the supplied notes and to cite the concepts it used.
          Your own text is wrapped in delimiters and treated as untrusted, so instructions hidden in
          a question are ignored.
        </p>
      </Block>

      <Block id="graph" title="The knowledge graph (live)">
        <p>
          Every concept is a node. An arrow from <strong>A to B</strong> means A must be learned
          before B. The graph is a directed acyclic graph, so a valid study order always exists.
          This is the real graph served by the backend, read-only. Hover or focus a node to
          highlight its links.
        </p>
        <LiveGraph />
      </Block>

      <Block id="recommender" title="The recommender uses the same graph">
        <p>
          Quizzes update a mastery score per concept. When a concept is weak, a small set of
          transparent rules walks the prerequisite edges <strong>backward</strong> to find the
          earliest weak prerequisite, because that is usually the real reason for the struggle. Each
          recommendation explains which rule fired. There is no black-box model to trust.
        </p>
      </Block>

      <Block id="evaluation" title="How we measure it">
        <p>
          An offline test set of 85 questions covers direct questions, symptoms with an unnamed
          prerequisite, multi-concept comparisons, misconceptions and off-topic requests. We compare
          Cognexa with a plain similarity-search baseline that uses the <strong>same notes</strong>,
          using retrieval metrics (did it find the gold prerequisite?) and reference-free answer
          quality metrics. A user study with matched pre- and post-tests measures learning gain for
          adaptive versus non-adaptive recommendations.
        </p>
      </Block>
    </div>
  );
}
