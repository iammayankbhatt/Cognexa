"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, ListChecks, MessageSquare, NotebookPen } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import type { Body } from "@/lib/api-contract";
import { tutorLink } from "@/components/quiz/feedback-panel";
import { clusterLabel } from "@/components/quiz/quiz-home";
import { ConceptChip } from "@/components/shared/concept-chip";
import { ErrorState } from "@/components/shared/error-state";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { Markdown } from "@/components/tutor/markdown";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { useConceptPage, useCreateQuiz } from "@/lib/quiz/use-quiz";
import type { ConceptLink } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

const LANG_LABEL: Record<string, string> = { python: "Python", cpp: "C++", "c++": "C++" };

/** Split a Markdown code section into its fenced blocks by language (Python / C++ tabs). */
export function codeBlocks(text: string): { lang: string; code: string }[] {
  const out: { lang: string; code: string }[] = [];
  for (const m of text.matchAll(/```(\w[\w+]*)?\n([\s\S]*?)```/g)) {
    out.push({ lang: (m[1] ?? "text").toLowerCase(), code: m[2].replace(/\n$/, "") });
  }
  return out;
}

interface Note {
  concept_id: string;
  body: string;
  bookmarked: boolean;
  updated_at: string | null;
}

function Links({ title, items }: { title: string; items: ConceptLink[] }) {
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold tracking-wide text-muted uppercase">{title}</h3>
      <div className="flex flex-wrap gap-2">
        {items.map((c) => (
          <ConceptChip
            key={c.id}
            name={c.name}
            href={`/app/learn/${c.id}`}
            mastery={c.mastery ?? undefined}
          />
        ))}
      </div>
    </div>
  );
}

function NoteBox({ conceptId }: { conceptId: string }) {
  const qc = useQueryClient();
  const key = ["note", conceptId];
  const note = useQuery({ queryKey: key, queryFn: () => api<Note>(`/notes/${conceptId}`) });
  const [draft, setDraft] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const save = useMutation({
    mutationFn: (body: Partial<Pick<Note, "body" | "bookmarked">> & Body<"NoteIn">) =>
      api<Note>(`/notes/${conceptId}`, { method: "PUT", body }),
    onSuccess: (n) => qc.setQueryData(key, n),
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save."),
  });
  const bookmarked = note.data?.bookmarked ?? false;
  const body = draft ?? note.data?.body ?? "";
  return (
    <>
      <Button
        variant="outline"
        aria-pressed={bookmarked}
        disabled={note.isPending || save.isPending}
        onClick={() => save.mutate({ bookmarked: !bookmarked })}
      >
        <Bookmark aria-hidden className={cn("size-4", bookmarked && "fill-accent text-accent")} />
        {bookmarked ? "Bookmarked" : "Bookmark"}
      </Button>
      <Button variant="outline" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        <NotebookPen aria-hidden className="size-4" />
        {note.data?.body ? "My note" : "Add a note"}
      </Button>
      {open && (
        <form
          className="basis-full space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(
              { body },
              {
                onSuccess: () => {
                  setDraft(null);
                  toast.success("Note saved.");
                },
              },
            );
          }}
        >
          <label htmlFor="concept-note" className="sr-only">
            Your note
          </label>
          <textarea
            id="concept-note"
            value={body}
            maxLength={20000}
            rows={4}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Write what you want to remember about this concept (Markdown works)."
            className="w-full resize-y rounded-xl border border-border bg-surface px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
          />
          <Button type="submit" size="sm" disabled={save.isPending || draft === null}>
            Save note
          </Button>
        </form>
      )}
    </>
  );
}

export function ConceptPageView({ conceptId }: { conceptId: string }) {
  const router = useRouter();
  const page = useConceptPage(conceptId);
  const create = useCreateQuiz();
  if (page.isPending) {
    return (
      <div className="space-y-4" aria-label="Loading concept">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (page.error || !page.data) {
    const notFound = page.error instanceof ApiError && page.error.status === 404;
    return (
      <ErrorState
        title={notFound ? "Concept not found" : "Couldn't load this concept"}
        message={page.error?.message}
        onRetry={notFound ? undefined : () => void page.refetch()}
      />
    );
  }
  const c = page.data;
  const practise = async () => {
    try {
      const s = await create.mutateAsync({ mode: "concept", concept_id: c.id, count: 8 });
      router.push(`/app/quizzes/${s.id}`);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start the quiz.");
    }
  };
  const names = Object.fromEntries(
    [...c.prerequisites, ...c.leads_to, ...c.related].map((l) => [l.id, l.name]),
  );
  return (
    <article className="space-y-6">
      <header className="space-y-3">
        <nav aria-label="Breadcrumb" className="text-xs text-muted">
          <Link href="/app/learn" className="hover:underline">
            Learn
          </Link>{" "}
          / {clusterLabel(c.cluster)}
        </nav>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">{c.name}</h1>
          {c.mastery ? (
            <MasteryBadge value={c.mastery.effective} />
          ) : (
            <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted">
              Not practised yet
            </span>
          )}
        </div>
        <p className="max-w-3xl text-muted">{c.description}</p>
        {c.mastery && (
          <p className="text-xs text-muted">
            {c.mastery.attempts} answers, {c.mastery.correct} correct
            {c.mastery.last_practiced_at
              ? ` · last practised ${new Date(c.mastery.last_practiced_at).toLocaleDateString()}`
              : ""}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Link
            href={tutorLink(`Explain ${c.name}.`)}
            className={buttonVariants({ variant: "default" })}
          >
            <MessageSquare aria-hidden className="size-4" />
            Ask the tutor about this
          </Link>
          <Button
            variant="outline"
            onClick={() => void practise()}
            disabled={create.isPending || c.question_count === 0}
          >
            <ListChecks aria-hidden className="size-4" />
            Practice this concept
          </Button>
          <NoteBox conceptId={c.id} />
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_16rem]">
        <div className="min-w-0 space-y-6">
          {c.sections.map((s) => {
            const blocks = s.kind === "code" ? codeBlocks(s.text) : [];
            return (
              <section
                key={s.kind}
                className="space-y-2 rounded-2xl border border-border bg-surface p-5"
                aria-label={s.heading}
              >
                <h2 className="text-lg font-semibold">{s.heading}</h2>
                {blocks.length > 1 ? (
                  <Tabs defaultValue={blocks[0].lang}>
                    <TabsList>
                      {blocks.map((b) => (
                        <TabsTrigger key={b.lang} value={b.lang}>
                          {LANG_LABEL[b.lang] ?? b.lang}
                        </TabsTrigger>
                      ))}
                    </TabsList>
                    {blocks.map((b) => (
                      <TabsContent key={b.lang} value={b.lang}>
                        <Markdown text={`\`\`\`${b.lang}\n${b.code}\n\`\`\``} />
                      </TabsContent>
                    ))}
                  </Tabs>
                ) : (
                  <Markdown text={s.text} conceptNames={names} />
                )}
              </section>
            );
          })}
        </div>
        <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start" aria-label="Related concepts">
          <Links title="Builds on" items={c.prerequisites} />
          <Links title="Leads to" items={c.leads_to} />
          <Links title="Related" items={c.related} />
        </aside>
      </div>
    </article>
  );
}
