"use client";

import { useQuery } from "@tanstack/react-query";
import { Bookmark, FileText, NotebookPen, Plus, Search, Sparkles, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { clusterLabel } from "@/components/quiz/quiz-home";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Markdown } from "@/components/tutor/markdown";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { friendlyError } from "@/lib/errors";
import {
  useNoteMutations,
  useNotes,
  useSheetMutations,
  useSheets,
  type NoteItem,
} from "@/lib/notes";
import { cn } from "@/lib/utils";

const CLUSTERS = [
  "foundations",
  "complexity",
  "linear",
  "searching_hashing",
  "sorting",
  "trees",
  "graphs",
  "paradigms",
];

function NoteCard({ note }: { note: NoteItem }) {
  const { save, remove } = useNoteMutations();
  const [draft, setDraft] = useState<string | null>(null);
  const [preview, setPreview] = useState(true);
  const body = draft ?? note.body;
  return (
    <li className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Link href={`/app/learn/${note.concept_id}`} className="font-medium hover:underline">
          {note.name}
        </Link>
        <span className="text-xs text-muted">{clusterLabel(note.cluster)}</span>
        <button
          type="button"
          aria-pressed={note.bookmarked}
          aria-label={note.bookmarked ? "Remove bookmark" : "Bookmark"}
          onClick={() => save.mutate({ conceptId: note.concept_id, bookmarked: !note.bookmarked })}
          className="ml-auto rounded p-1 text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Bookmark className={cn("size-4", note.bookmarked && "fill-accent text-accent")} />
        </button>
        <button
          type="button"
          aria-label={`Delete note on ${note.name}`}
          onClick={() =>
            remove.mutate(note.concept_id, {
              onSuccess: () => toast("Note deleted"),
              onError: () => toast.error("Could not delete the note."),
            })
          }
          className="rounded p-1 text-muted outline-none hover:bg-surface-2 hover:text-danger focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Trash2 className="size-4" />
        </button>
      </div>
      {preview && draft === null ? (
        <button
          type="button"
          onClick={() => setPreview(false)}
          className="block w-full text-left"
          aria-label={`Edit note on ${note.name}`}
        >
          {note.body.trim() ? (
            <Markdown text={note.body} />
          ) : (
            <span className="text-sm text-muted">Bookmarked. Click to add a note.</span>
          )}
        </button>
      ) : (
        <form
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(
              { conceptId: note.concept_id, body },
              {
                onSuccess: () => {
                  setDraft(null);
                  setPreview(true);
                  toast.success("Note saved.");
                },
                onError: (err) =>
                  toast.error(err instanceof ApiError ? err.message : "Could not save."),
              },
            );
          }}
        >
          <Tabs defaultValue="write">
            <TabsList>
              <TabsTrigger value="write">Write</TabsTrigger>
              <TabsTrigger value="preview">Preview</TabsTrigger>
            </TabsList>
            <TabsContent value="write">
              <label htmlFor={`note-${note.concept_id}`} className="sr-only">
                Note on {note.name}
              </label>
              <textarea
                id={`note-${note.concept_id}`}
                value={body}
                maxLength={20000}
                rows={6}
                onChange={(e) => setDraft(e.target.value)}
                className="w-full resize-y rounded-xl border border-border bg-bg px-3 py-2 font-mono text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
            </TabsContent>
            <TabsContent value="preview">
              <div className="min-h-24 rounded-xl border border-border bg-bg px-3 py-2">
                {body.trim() ? (
                  <Markdown text={body} />
                ) : (
                  <p className="text-sm text-muted">Nothing to preview.</p>
                )}
              </div>
            </TabsContent>
          </Tabs>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={save.isPending}>
              Save
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                setDraft(null);
                setPreview(true);
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      )}
      <p className="text-xs text-muted">Updated {new Date(note.updated_at).toLocaleString()}</p>
    </li>
  );
}

function NotesTab() {
  const [q, setQ] = useState("");
  const [cluster, setCluster] = useState("all");
  const [bookmarked, setBookmarked] = useState(false);
  const { data, isPending, error, refetch } = useNotes({ q, cluster, bookmarked });
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-48 flex-1">
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted"
          />
          <label htmlFor="notes-search" className="sr-only">
            Search notes
          </label>
          <input
            id="notes-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            maxLength={100}
            placeholder="Search notes"
            className="h-9 w-full rounded-lg border border-border bg-surface pr-3 pl-9 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <label htmlFor="notes-cluster" className="sr-only">
          Cluster
        </label>
        <select
          id="notes-cluster"
          value={cluster}
          onChange={(e) => setCluster(e.target.value)}
          className="h-9 rounded-lg border border-border bg-surface px-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="all">All clusters</option>
          {CLUSTERS.map((c) => (
            <option key={c} value={c}>
              {clusterLabel(c)}
            </option>
          ))}
        </select>
        <Button
          variant={bookmarked ? "default" : "outline"}
          aria-pressed={bookmarked}
          onClick={() => setBookmarked((b) => !b)}
        >
          <Bookmark aria-hidden className="size-4" /> Bookmarked
        </Button>
      </div>
      {isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : error || !data ? (
        <ErrorState message={error?.message} onRetry={() => void refetch()} />
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={<NotebookPen />}
          title={q || cluster !== "all" || bookmarked ? "No matching notes" : "No notes yet"}
          description="Open any concept in Learn and use “Add a note” or “Bookmark”. Your notes show up here."
          action={
            <Link href="/app/learn" className="text-sm text-accent underline">
              Go to Learn
            </Link>
          }
        />
      ) : (
        <ul className="space-y-3">
          {data.items.map((n) => (
            <NoteCard key={n.concept_id} note={n} />
          ))}
        </ul>
      )}
    </div>
  );
}

interface ConceptLite {
  id: string;
  name: string;
  cluster: string;
}

function SheetsTab() {
  const router = useRouter();
  const sheets = useSheets();
  const { create, remove } = useSheetMutations();
  const concepts = useQuery({
    queryKey: ["concepts"],
    queryFn: () => api<ConceptLite[]>("/concepts"),
    staleTime: 300_000,
  });
  const [picked, setPicked] = useState<string[]>([]);
  const [choosing, setChoosing] = useState(false);
  const make = async (ids?: string[]) => {
    try {
      const s = await create.mutateAsync(ids);
      router.push(`/app/notes/sheets/${s.id}`);
    } catch (err) {
      const f = friendlyError(err);
      toast.error(
        err instanceof ApiError && err.code === "nothing_to_revise"
          ? err.message
          : `${f.title}. ${f.description}`,
      );
    }
  };
  return (
    <div className="space-y-4">
      <section className="space-y-3 rounded-2xl border border-border bg-surface p-5">
        <div className="flex items-start gap-3">
          <Sparkles aria-hidden className="mt-0.5 size-5 shrink-0 text-accent" />
          <div className="flex-1 space-y-1">
            <h2 className="text-base font-semibold">New revision sheet</h2>
            <p className="text-sm text-muted">
              A one-to-two page summary written from the course notes of your weak concepts and the
              prerequisites they build on, with concept citations. Uses one AI request.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void make()} disabled={create.isPending}>
            {create.isPending ? "Writing…" : "From my weak spots"}
          </Button>
          <Button variant="outline" aria-expanded={choosing} onClick={() => setChoosing((c) => !c)}>
            <Plus aria-hidden className="size-4" /> Choose concepts
          </Button>
        </div>
        {choosing && (
          <div className="space-y-2">
            <p className="text-xs text-muted">Pick up to 5 ({picked.length} chosen)</p>
            <ul className="grid max-h-56 gap-1 overflow-y-auto sm:grid-cols-2 lg:grid-cols-3">
              {(concepts.data ?? []).map((c) => (
                <li key={c.id}>
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={picked.includes(c.id)}
                      disabled={!picked.includes(c.id) && picked.length >= 5}
                      onChange={(e) =>
                        setPicked((p) =>
                          e.target.checked ? [...p, c.id] : p.filter((x) => x !== c.id),
                        )
                      }
                      className="size-4 accent-[var(--primary)]"
                    />
                    {c.name}
                  </label>
                </li>
              ))}
            </ul>
            <Button
              size="sm"
              disabled={!picked.length || create.isPending}
              onClick={() => void make(picked)}
            >
              Write sheet for {picked.length} concept(s)
            </Button>
          </div>
        )}
      </section>
      {sheets.isPending ? (
        <Skeleton className="h-32 w-full" />
      ) : sheets.error || !sheets.data ? (
        <ErrorState message={sheets.error?.message} onRetry={() => void sheets.refetch()} />
      ) : sheets.data.items.length === 0 ? (
        <EmptyState
          icon={<FileText />}
          title="No revision sheets yet"
          description="Your saved sheets appear here, ready to print or download."
        />
      ) : (
        <ul className="divide-y divide-border rounded-2xl border border-border bg-surface">
          {sheets.data.items.map((s) => {
            const title =
              s.content
                .split("\n")
                .find((l) => l.trim())
                ?.replace(/^#+\s*/, "") ?? "Revision sheet";
            return (
              <li key={s.id} className="flex items-center gap-3 px-4 py-3">
                <FileText aria-hidden className="size-4 shrink-0 text-accent" />
                <Link
                  href={`/app/notes/sheets/${s.id}`}
                  className="min-w-0 flex-1 truncate text-sm font-medium hover:underline"
                >
                  {title}
                </Link>
                <span className="text-xs text-muted">
                  {new Date(s.created_at).toLocaleDateString()}
                </span>
                <button
                  type="button"
                  aria-label={`Delete ${title}`}
                  onClick={() => remove.mutate(s.id, { onSuccess: () => toast("Sheet deleted") })}
                  className="rounded p-1 text-muted outline-none hover:bg-surface-2 hover:text-danger focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function NotesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Notes"
        description="Your notes and bookmarks per concept, and personalised revision sheets."
      />
      <Tabs defaultValue="notes">
        <TabsList>
          <TabsTrigger value="notes">Notes &amp; bookmarks</TabsTrigger>
          <TabsTrigger value="sheets">Revision sheets</TabsTrigger>
        </TabsList>
        <TabsContent value="notes" className="pt-4">
          <NotesTab />
        </TabsContent>
        <TabsContent value="sheets" className="pt-4">
          <SheetsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
