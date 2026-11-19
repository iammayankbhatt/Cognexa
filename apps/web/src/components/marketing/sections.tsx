import {
  Check,
  ClipboardCheck,
  GitBranch,
  Map,
  Minus,
  NotebookPen,
  Route,
  ShieldCheck,
} from "lucide-react";

import { cn } from "@/lib/utils";

export const PIPELINE = [
  {
    title: "Ask",
    text: "You describe a problem in your own words, including symptoms like an error message.",
  },
  {
    title: "Classify",
    text: "The question is mapped to one or more concepts in the prerequisite graph.",
  },
  {
    title: "Traverse",
    text: "The graph is walked backwards along PREREQUISITE_OF edges to find what you may be missing.",
  },
  {
    title: "Gather",
    text: "Notes for those concepts are collected, weighted toward your weak spots.",
  },
  {
    title: "Answer",
    text: "The tutor answers using only that material and cites the concepts it used.",
  },
] as const;

export function Pipeline({ className }: { className?: string }) {
  return (
    <ol className={cn("grid gap-3 sm:grid-cols-5", className)}>
      {PIPELINE.map((s, i) => (
        <li key={s.title} className="relative rounded-xl border border-border bg-surface p-4">
          <span className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-fg">
            {i + 1}
          </span>
          <h3 className="mt-3 font-semibold text-text">{s.title}</h3>
          <p className="mt-1 text-sm text-muted">{s.text}</p>
        </li>
      ))}
    </ol>
  );
}

const FEATURES = [
  {
    icon: GitBranch,
    title: "Graph-grounded answers",
    text: "69 DSA concepts and their prerequisites power every explanation.",
  },
  {
    icon: Route,
    title: "Adaptive recommendations",
    text: "Rules walk the graph from your weak concepts to the real gap.",
  },
  {
    icon: ClipboardCheck,
    title: "Quizzes that diagnose",
    text: "Each wrong answer points at the prerequisite you should revisit.",
  },
  {
    icon: Map,
    title: "Knowledge map",
    text: "See mastery coloured across the whole concept graph.",
  },
  {
    icon: NotebookPen,
    title: "Notes and revision",
    text: "Bookmarks and personalised revision sheets you can export.",
  },
  {
    icon: ShieldCheck,
    title: "Grounded and safe",
    text: "Answers cite their sources; your text is treated as untrusted input.",
  },
] as const;

export function FeatureGrid() {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {FEATURES.map((f) => (
        <li key={f.title} className="rounded-xl border border-border bg-surface p-5">
          <span className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-accent">
            <f.icon aria-hidden className="size-5" />
          </span>
          <h3 className="mt-3 font-semibold text-text">{f.title}</h3>
          <p className="mt-1 text-sm text-muted">{f.text}</p>
        </li>
      ))}
    </ul>
  );
}

const ROWS: [string, boolean, boolean][] = [
  ["Finds the concept you named", true, true],
  ["Finds the prerequisite you did not name", false, true],
  ["Explains why, using prerequisite links", false, true],
  ["Personalises to your weak concepts", false, true],
  ["Shows the edge responsible for a retrieval", false, true],
];

export function Comparison() {
  const cell = (yes: boolean) =>
    yes ? (
      <span className="inline-flex items-center gap-1 text-success">
        <Check aria-hidden className="size-4" /> Yes
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 text-muted">
        <Minus aria-hidden className="size-4" /> Not reliably
      </span>
    );
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full min-w-[32rem] text-left text-sm">
        <caption className="sr-only">Plain RAG compared with Cognexa</caption>
        <thead className="text-xs text-muted uppercase">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">
              Capability
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              Plain RAG
            </th>
            <th scope="col" className="px-4 py-3 font-medium text-accent">
              Cognexa (GraphRAG)
            </th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([label, plain, graph]) => (
            <tr key={label} className="border-t border-border">
              <th scope="row" className="px-4 py-3 font-normal text-text">
                {label}
              </th>
              <td className="px-4 py-3">{cell(plain)}</td>
              <td className="px-4 py-3">{cell(graph)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
