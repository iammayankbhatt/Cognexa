import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About",
  description: "The team and project behind Cognexa.",
};

const TEAM = [
  { name: "Ansh Karki", id: "2318402" },
  { name: "Mayank Bhatt", id: "2319093" },
  { name: "Divyanshi Kaushik", id: "2318770" },
  { name: "Harshita Pant", id: "2318850" },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-10 px-4 py-14 sm:px-6">
      <header className="space-y-3">
        <p className="text-xs font-semibold tracking-widest text-accent uppercase">About</p>
        <h1 className="text-4xl font-semibold tracking-tight text-balance text-text">
          Built as a B.Tech final-year project
        </h1>
        <p className="text-lg text-muted">
          Cognexa implements the project{" "}
          <em>
            Towards Agentic GraphRAG: A Knowledge-Graph-Grounded Tutoring System for Adaptive
            Computer Science Education
          </em>{" "}
          as a complete, deployable product.
        </p>
      </header>

      <section className="space-y-3" aria-labelledby="team">
        <h2 id="team" className="text-xl font-semibold text-text">
          Team CSE27-125
        </h2>
        <ul className="grid gap-3 sm:grid-cols-2">
          {TEAM.map((m) => (
            <li key={m.id} className="rounded-xl border border-border bg-surface p-4">
              <p className="font-medium text-text">{m.name}</p>
              <p className="text-sm text-muted">Roll no. {m.id}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-2" aria-labelledby="guide">
        <h2 id="guide" className="text-xl font-semibold text-text">
          Guide
        </h2>
        <p className="text-muted">Mr. Akash Chauhan, Assistant Professor</p>
      </section>

      <section className="space-y-2" aria-labelledby="uni">
        <h2 id="uni" className="text-xl font-semibold text-text">
          Institution
        </h2>
        <p className="text-muted">Graphic Era Hill University, Dehradun</p>
      </section>

      <section className="space-y-2" aria-labelledby="stack">
        <h2 id="stack" className="text-xl font-semibold text-text">
          Built with
        </h2>
        <p className="text-muted">
          Next.js, FastAPI, Neo4j, Postgres with pgvector, and Supabase Auth, all on free tiers. The
          first subject is Data Structures &amp; Algorithms; the system is designed so other
          subjects can be added as content packs.
        </p>
      </section>
    </div>
  );
}
