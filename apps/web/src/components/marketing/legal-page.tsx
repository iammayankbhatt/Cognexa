export function LegalPage({
  title,
  updated,
  intro,
  sections,
}: {
  title: string;
  updated: string;
  intro: string;
  sections: { heading: string; body: string[] }[];
}) {
  return (
    <article className="mx-auto max-w-3xl space-y-8 px-4 py-14 sm:px-6">
      <header className="space-y-3">
        <h1 className="text-4xl font-semibold tracking-tight text-text">{title}</h1>
        <p className="text-sm text-muted">Last updated {updated}</p>
        <p className="text-lg text-muted">{intro}</p>
      </header>
      {sections.map((s) => (
        <section key={s.heading} className="space-y-2">
          <h2 className="text-xl font-semibold text-text">{s.heading}</h2>
          {s.body.map((p, i) => (
            <p key={i} className="text-muted">
              {p}
            </p>
          ))}
        </section>
      ))}
    </article>
  );
}
