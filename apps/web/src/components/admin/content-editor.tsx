"use client";

import { AlertTriangle, BookOpenCheck, Check, FileText, Pencil, Plus, Trash2 } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { Field, fieldClass } from "@/components/admin/form-bits";
import { QuestionView, TYPE_LABEL } from "@/components/quiz/question-view";
import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Markdown } from "@/components/tutor/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useAdminGraph,
  useConceptContent,
  useContentMutations,
  type AdminChunk,
  type AdminConcept,
  type AdminQuestion,
} from "@/lib/admin";
import {
  changeType,
  draftFrom,
  draftToBody,
  emptyOptions,
  OPTION_IDS,
  validateDraft,
  type QType,
  type QuestionDraft,
} from "@/lib/admin-question";
import { ApiError } from "@/lib/api";
import type { QuizQuestion, ResponseValue } from "@/lib/quiz/types";
import { cn } from "@/lib/utils";

const FLAG_LABEL: Record<string, string> = {
  too_easy: "Everyone gets it right",
  too_hard: "Almost nobody gets it right",
  low_discrimination: "Does not separate strong and weak learners",
};

function errorText(e: unknown, fallback: string): string {
  return e instanceof ApiError ? e.message : fallback;
}

// ---------------------------------------------------------------- chunks
function ChunkEditor({
  chunk,
  kinds,
  conceptId,
  onDone,
}: {
  chunk: AdminChunk;
  kinds: string[];
  conceptId: string;
  onDone: () => void;
}) {
  const { editChunk } = useContentMutations(conceptId);
  const [heading, setHeading] = useState(chunk.heading);
  const [kind, setKind] = useState(chunk.kind);
  const [text, setText] = useState(chunk.text);
  const [reviewed, setReviewed] = useState(chunk.reviewed);
  const tooShort = text.trim().length < 20;
  const id = chunk.id.replace(/[^a-z0-9]/gi, "-");
  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (tooShort || !heading.trim()) return;
        editChunk.mutate(
          { id: chunk.id, heading: heading.trim(), text, kind, reviewed },
          {
            onSuccess: (r) => {
              if (r.warning) toast.warning(r.warning);
              else toast.success("Chunk saved and re-embedded.");
              onDone();
            },
            onError: (err) => toast.error(errorText(err, "Could not save the chunk.")),
          },
        );
      }}
    >
      <div className="grid gap-3 sm:grid-cols-[1fr_12rem]">
        <Field label="Heading" htmlFor={`${id}-heading`}>
          <input
            id={`${id}-heading`}
            className={fieldClass}
            value={heading}
            maxLength={200}
            onChange={(e) => setHeading(e.target.value)}
            required
          />
        </Field>
        <Field label="Kind" htmlFor={`${id}-kind`}>
          <select
            id={`${id}-kind`}
            className={fieldClass}
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            {kinds.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </Field>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Field
          label="Markdown"
          htmlFor={`${id}-text`}
          hint={`${text.length} / 12000 characters`}
          error={tooShort ? "At least 20 characters." : null}
        >
          <textarea
            id={`${id}-text`}
            className={cn(fieldClass, "min-h-80 resize-y font-mono text-xs leading-relaxed")}
            value={text}
            maxLength={12000}
            onChange={(e) => setText(e.target.value)}
          />
        </Field>
        <div className="space-y-1.5">
          <p className="text-sm font-medium">Preview</p>
          <div className="max-h-[26rem] min-h-80 overflow-y-auto rounded-lg border border-border bg-bg p-3 text-sm">
            <Markdown text={text} />
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={reviewed}
            onChange={(e) => setReviewed(e.target.checked)}
            className="size-4 accent-[var(--primary)]"
          />
          Reviewed by a human
        </label>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={onDone}>
            Cancel
          </Button>
          <Button type="submit" disabled={editChunk.isPending || tooShort}>
            {editChunk.isPending ? "Saving…" : "Save chunk"}
          </Button>
        </div>
      </div>
    </form>
  );
}

function ChunkCard({
  chunk,
  kinds,
  conceptId,
  open,
  onOpen,
}: {
  chunk: AdminChunk;
  kinds: string[];
  conceptId: string;
  open: boolean;
  onOpen: (id: string | null) => void;
}) {
  const { reviewChunk } = useContentMutations(conceptId);
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (open) ref.current?.scrollIntoView({ block: "start", behavior: "smooth" });
  }, [open]);
  return (
    <article
      ref={ref}
      id={`chunk-${chunk.id}`}
      className={cn(
        "scroll-mt-24 rounded-xl border bg-surface p-4",
        open ? "border-accent" : "border-border",
      )}
    >
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-1">
          <h3 className="font-medium text-text">{chunk.heading}</h3>
          <div className="flex flex-wrap gap-1.5">
            <Badge variant="outline">{chunk.kind}</Badge>
            <Badge variant="outline">source: {chunk.source}</Badge>
            {chunk.reviewed ? (
              <Badge variant="outline" className="border-success text-success">
                reviewed
              </Badge>
            ) : (
              <Badge variant="outline" className="border-warning text-warning">
                not reviewed
              </Badge>
            )}
            {!chunk.embedded && (
              <Badge variant="outline" className="border-danger text-danger">
                not embedded
              </Badge>
            )}
          </div>
        </div>
        {!open && (
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={reviewChunk.isPending}
              onClick={() =>
                reviewChunk.mutate(
                  { id: chunk.id, reviewed: !chunk.reviewed },
                  { onError: (e) => toast.error(errorText(e, "Could not update it.")) },
                )
              }
            >
              <Check aria-hidden className="size-4" />
              {chunk.reviewed ? "Unmark reviewed" : "Mark reviewed"}
            </Button>
            <Button size="sm" onClick={() => onOpen(chunk.id)}>
              <Pencil aria-hidden className="size-4" /> Edit
            </Button>
          </div>
        )}
      </header>
      {open ? (
        <div className="mt-4">
          <ChunkEditor
            chunk={chunk}
            kinds={kinds}
            conceptId={conceptId}
            onDone={() => onOpen(null)}
          />
        </div>
      ) : (
        <p className="mt-2 line-clamp-3 text-sm text-muted">{chunk.text}</p>
      )}
    </article>
  );
}

// ---------------------------------------------------------------- questions
function previewQuestion(d: QuestionDraft, conceptName: string): QuizQuestion {
  return {
    id: "preview",
    concept_id: "preview",
    concept_name: conceptName,
    type: d.type,
    difficulty: d.difficulty,
    prompt: d.prompt || "_(prompt)_",
    code: d.code.trim() ? d.code : null,
    language: d.language,
    options: d.options.map((o) => ({ id: o.id, text: o.text || "_(empty option)_" })),
    answer: null,
  };
}

function QuestionPreview({ draft, conceptName }: { draft: QuestionDraft; conceptName: string }) {
  const [value, setValue] = useState<ResponseValue>(null);
  const [reveal, setReveal] = useState(false);
  const q = previewQuestion(draft, conceptName);
  const auto = draft.type === "mcq" || draft.type === "multi_select" || draft.type === "true_false";
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Preview (as the student sees it)</p>
        <label className="flex items-center gap-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={reveal}
            onChange={(e) => setReveal(e.target.checked)}
            className="size-3.5 accent-[var(--primary)]"
          />
          Show answer
        </label>
      </div>
      <div className="rounded-xl border border-border bg-bg p-4">
        <QuestionView
          question={q}
          value={value ?? undefined}
          onChange={setValue}
          graded={
            reveal && auto
              ? { question_id: "preview", response: value, correct_answer: draft.answer }
              : null
          }
        />
        {reveal && (
          <div className="mt-4 space-y-2 border-t border-border pt-3 text-sm">
            {!auto && (
              <p>
                <span className="text-muted">Answer: </span>
                <span className="font-mono whitespace-pre-wrap">{String(draft.answer)}</span>
              </p>
            )}
            <Markdown text={draft.explanation || "_(explanation)_"} />
          </div>
        )}
      </div>
    </div>
  );
}

function OptionsEditor({
  draft,
  setDraft,
}: {
  draft: QuestionDraft;
  setDraft: (d: QuestionDraft) => void;
}) {
  const multi = draft.type === "multi_select";
  const isCorrect = (id: string) =>
    multi ? Array.isArray(draft.answer) && draft.answer.includes(id) : draft.answer === id;
  const toggle = (id: string) => {
    if (!multi) return setDraft({ ...draft, answer: id });
    const list = Array.isArray(draft.answer) ? draft.answer : [];
    setDraft({
      ...draft,
      answer: list.includes(id) ? list.filter((x) => x !== id) : [...list, id].sort(),
    });
  };
  const setOption = (i: number, patch: Partial<QuestionDraft["options"][number]>) =>
    setDraft({
      ...draft,
      options: draft.options.map((o, j) => (j === i ? { ...o, ...patch } : o)),
    });
  return (
    <fieldset className="space-y-3">
      <legend className="text-sm font-medium">
        Options ({multi ? "tick every correct option" : "pick the correct option"})
      </legend>
      {draft.options.map((o, i) => (
        <div key={o.id} className="space-y-2 rounded-lg border border-border p-3">
          <div className="flex items-center gap-2">
            <input
              type={multi ? "checkbox" : "radio"}
              name="correct-option"
              aria-label={`Option ${o.id.toUpperCase()} is correct`}
              checked={isCorrect(o.id)}
              onChange={() => toggle(o.id)}
              className="size-4 accent-[var(--primary)]"
            />
            <span className="font-mono text-xs text-muted">{o.id.toUpperCase()}</span>
            <input
              aria-label={`Option ${o.id.toUpperCase()} text`}
              className={fieldClass}
              value={o.text}
              maxLength={400}
              onChange={(e) => setOption(i, { text: e.target.value })}
            />
            {multi && draft.options.length > 4 && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                aria-label={`Remove option ${o.id.toUpperCase()}`}
                onClick={() => {
                  const kept = draft.options.filter((_, j) => j !== i);
                  const relabel = kept.map((k, j) => ({ ...k, id: OPTION_IDS[j] }));
                  const map = new Map(kept.map((k, j) => [k.id, OPTION_IDS[j] as string]));
                  const ans = Array.isArray(draft.answer) ? draft.answer : [];
                  setDraft({
                    ...draft,
                    options: relabel,
                    answer: ans.filter((a) => map.has(a)).map((a) => map.get(a) as string),
                  });
                }}
              >
                <Trash2 aria-hidden className="size-4" />
              </Button>
            )}
          </div>
          {!isCorrect(o.id) && (
            <input
              aria-label={`Why option ${o.id.toUpperCase()} is wrong`}
              placeholder="Why is this wrong? (the misconception it represents)"
              className={cn(fieldClass, "text-xs")}
              value={o.why_wrong ?? ""}
              maxLength={500}
              onChange={(e) => setOption(i, { why_wrong: e.target.value })}
            />
          )}
        </div>
      ))}
      {multi && draft.options.length < OPTION_IDS.length && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() =>
            setDraft({
              ...draft,
              options: [
                ...draft.options,
                ...emptyOptions(draft.options.length + 1).slice(draft.options.length),
              ],
            })
          }
        >
          <Plus aria-hidden className="size-4" /> Add option
        </Button>
      )}
    </fieldset>
  );
}

function QuestionForm({
  question,
  concepts,
  conceptName,
  onDone,
}: {
  question: AdminQuestion;
  concepts: AdminConcept[];
  conceptName: string;
  onDone: () => void;
}) {
  const { editQuestion } = useContentMutations(question.concept_id);
  const [draft, setDraft] = useState<QuestionDraft>(() => draftFrom(question));
  const [reviewed, setReviewed] = useState(question.reviewed);
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const errors = validateDraft(draft);
  const choice = draft.type === "mcq" || draft.type === "multi_select";
  return (
    <form
      className="grid gap-6 lg:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        setSubmitted(true);
        setServerError(null);
        if (errors.length) return;
        editQuestion.mutate(
          { id: question.id, body: draftToBody(draft, reviewed) },
          {
            onSuccess: () => {
              toast.success("Question saved.");
              onDone();
            },
            onError: (err) => setServerError(errorText(err, "Could not save the question.")),
          },
        );
      }}
    >
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="Type" htmlFor="q-type">
            <select
              id="q-type"
              className={fieldClass}
              value={draft.type}
              onChange={(e) => setDraft(changeType(draft, e.target.value as QType))}
            >
              {Object.entries(TYPE_LABEL).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Difficulty" htmlFor="q-difficulty">
            <select
              id="q-difficulty"
              className={fieldClass}
              value={draft.difficulty}
              onChange={(e) => setDraft({ ...draft, difficulty: Number(e.target.value) })}
            >
              <option value={1}>1 · easy</option>
              <option value={2}>2 · medium</option>
              <option value={3}>3 · hard</option>
            </select>
          </Field>
          <Field label="Code language" htmlFor="q-language">
            <select
              id="q-language"
              className={fieldClass}
              value={draft.language}
              onChange={(e) =>
                setDraft({ ...draft, language: e.target.value as QuestionDraft["language"] })
              }
            >
              <option value="python">Python</option>
              <option value="cpp">C++</option>
            </select>
          </Field>
        </div>
        <Field label="Prompt (Markdown)" htmlFor="q-prompt" hint={`${draft.prompt.length} / 1200`}>
          <textarea
            id="q-prompt"
            className={cn(fieldClass, "min-h-24")}
            value={draft.prompt}
            maxLength={1200}
            onChange={(e) => setDraft({ ...draft, prompt: e.target.value })}
          />
        </Field>
        <Field label={draft.type === "code_output" ? "Code" : "Code (optional)"} htmlFor="q-code">
          <textarea
            id="q-code"
            className={cn(fieldClass, "min-h-20 font-mono text-xs")}
            value={draft.code}
            spellCheck={false}
            onChange={(e) => setDraft({ ...draft, code: e.target.value })}
          />
        </Field>
        {choice && <OptionsEditor draft={draft} setDraft={setDraft} />}
        {draft.type === "true_false" && (
          <fieldset className="flex gap-4 text-sm">
            <legend className="mb-1 font-medium">Correct answer</legend>
            {[true, false].map((v) => (
              <label key={String(v)} className="flex items-center gap-2">
                <input
                  type="radio"
                  name="tf-answer"
                  checked={draft.answer === v}
                  onChange={() => setDraft({ ...draft, answer: v })}
                  className="size-4 accent-[var(--primary)]"
                />
                {v ? "True" : "False"}
              </label>
            ))}
          </fieldset>
        )}
        {(draft.type === "code_output" || draft.type === "short_answer") && (
          <Field
            label={draft.type === "code_output" ? "Expected output (exact)" : "Reference answer"}
            htmlFor="q-answer"
          >
            <textarea
              id="q-answer"
              className={cn(fieldClass, "min-h-16", draft.type === "code_output" && "font-mono")}
              value={typeof draft.answer === "string" ? draft.answer : ""}
              onChange={(e) => setDraft({ ...draft, answer: e.target.value })}
            />
          </Field>
        )}
        {draft.type === "short_answer" && (
          <Field
            label="Rubric key points"
            htmlFor="q-rubric"
            hint="One per line. The grader checks the answer against each point."
          >
            <textarea
              id="q-rubric"
              className={cn(fieldClass, "min-h-20")}
              value={draft.keyPoints}
              onChange={(e) => setDraft({ ...draft, keyPoints: e.target.value })}
            />
          </Field>
        )}
        <Field
          label="Explanation (shown after answering)"
          htmlFor="q-explanation"
          hint={`${draft.explanation.length} / 1500`}
        >
          <textarea
            id="q-explanation"
            className={cn(fieldClass, "min-h-20")}
            value={draft.explanation}
            maxLength={1500}
            onChange={(e) => setDraft({ ...draft, explanation: e.target.value })}
          />
        </Field>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Misconception tag" htmlFor="q-misconception">
            <input
              id="q-misconception"
              className={fieldClass}
              value={draft.misconception_tag}
              maxLength={100}
              onChange={(e) => setDraft({ ...draft, misconception_tag: e.target.value })}
            />
          </Field>
          <Field
            label="Diagnoses prerequisite"
            htmlFor="q-diagnoses"
            hint="A wrong answer points at this concept."
          >
            <select
              id="q-diagnoses"
              className={fieldClass}
              value={draft.diagnoses_prereq}
              onChange={(e) => setDraft({ ...draft, diagnoses_prereq: e.target.value })}
            >
              <option value="">none</option>
              {concepts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={reviewed}
            onChange={(e) => setReviewed(e.target.checked)}
            className="size-4 accent-[var(--primary)]"
          />
          Reviewed by a human
        </label>
        {(submitted && errors.length > 0) || serverError ? (
          <div role="alert" className="rounded-lg border border-danger bg-danger/10 p-3 text-sm">
            <p className="font-medium text-danger">Fix these before saving:</p>
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              {serverError && <li>{serverError}</li>}
              {submitted && errors.map((er) => <li key={er}>{er}</li>)}
            </ul>
          </div>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={onDone}>
            Cancel
          </Button>
          <Button type="submit" disabled={editQuestion.isPending}>
            {editQuestion.isPending ? "Saving…" : "Save question"}
          </Button>
        </div>
      </div>
      <QuestionPreview draft={draft} conceptName={conceptName} />
    </form>
  );
}

function QuestionRow({
  q,
  conceptId,
  onEdit,
}: {
  q: AdminQuestion;
  conceptId: string;
  onEdit: () => void;
}) {
  const { flagQuestion } = useContentMutations(conceptId);
  const s = q.stats;
  const run = (body: { reviewed?: boolean; status?: "active" | "inactive" }, ok: string) =>
    flagQuestion.mutate(
      { id: q.id, ...body },
      {
        onSuccess: () => toast.success(ok),
        onError: (e) => toast.error(errorText(e, "Could not update it.")),
      },
    );
  return (
    <li
      className={cn(
        "rounded-xl border border-border bg-surface p-4",
        q.status !== "active" && "opacity-70",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="font-mono text-muted">{q.id}</span>
            <Badge variant="outline">{TYPE_LABEL[q.type]}</Badge>
            <Badge variant="outline">difficulty {q.difficulty}</Badge>
            {q.status !== "active" && (
              <Badge variant="outline" className="border-danger text-danger">
                {q.status}
              </Badge>
            )}
            {q.reviewed ? (
              <Badge variant="outline" className="border-success text-success">
                reviewed
              </Badge>
            ) : (
              <Badge variant="outline" className="border-warning text-warning">
                not reviewed
              </Badge>
            )}
          </div>
          <p className="line-clamp-2 text-sm text-text">{q.prompt}</p>
          <p className="text-xs text-muted">
            {s.attempts} attempt{s.attempts === 1 ? "" : "s"}
            {s.pct_correct !== null && ` · ${Math.round(s.pct_correct * 100)}% correct`}
            {s.discrimination !== null && ` · discrimination ${s.discrimination.toFixed(2)}`}
          </p>
          {s.flags.length > 0 && (
            <ul className="flex flex-wrap gap-1.5">
              {s.flags.map((f) => (
                <li
                  key={f}
                  className="inline-flex items-center gap-1 rounded-md bg-warning/15 px-2 py-0.5 text-xs text-warning"
                >
                  <AlertTriangle aria-hidden className="size-3" /> {FLAG_LABEL[f] ?? f}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={flagQuestion.isPending}
            onClick={() =>
              run(
                { reviewed: !q.reviewed },
                q.reviewed ? "Marked not reviewed." : "Marked reviewed.",
              )
            }
          >
            <Check aria-hidden className="size-4" /> {q.reviewed ? "Unreview" : "Mark reviewed"}
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={flagQuestion.isPending}
            onClick={() =>
              q.status === "active"
                ? run({ status: "inactive" }, "Question deactivated: quizzes skip it.")
                : run({ status: "active" }, "Question re-activated.")
            }
          >
            {q.status === "active" ? "Deactivate" : "Activate"}
          </Button>
          <Button size="sm" onClick={onEdit}>
            <Pencil aria-hidden className="size-4" /> Edit
          </Button>
        </div>
      </div>
    </li>
  );
}

// ---------------------------------------------------------------- page
export function ContentEditor() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const conceptId = params.get("concept");
  const focusChunk = params.get("chunk");
  const graph = useAdminGraph();
  const content = useConceptContent(conceptId);
  const [openChunk, setOpenChunk] = useState<string | null>(focusChunk);
  const [editing, setEditing] = useState<AdminQuestion | null>(null);
  const [tab, setTab] = useState<string>("notes");
  const [onlyFlagged, setOnlyFlagged] = useState(false);

  const concepts = useMemo(
    () => [...(graph.data?.concepts ?? [])].sort((a, b) => a.order_index - b.order_index),
    [graph.data],
  );
  const clusters = useMemo(() => [...new Set(concepts.map((c) => c.cluster))], [concepts]);

  const select = (id: string) => {
    setOpenChunk(null);
    router.replace(id ? `${pathname}?concept=${encodeURIComponent(id)}` : pathname);
  };

  if (graph.isPending)
    return <Skeleton className="h-[60vh] w-full" aria-label="Loading concepts" />;
  if (graph.error)
    return <ErrorState message={graph.error.message} onRetry={() => void graph.refetch()} />;

  const data = content.data;
  const questions = (data?.questions ?? []).filter((q) => !onlyFlagged || q.stats.flags.length);
  const unreviewed = data
    ? data.chunks.filter((c) => !c.reviewed).length +
      data.questions.filter((q) => !q.reviewed).length
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Reviewer"
        title="Content & questions"
        description="Edit concept notes (re-embedded on save) and quiz questions. Edits here win over the files until they are copied back into data/subjects/."
      />
      <div className="max-w-md">
        <Field label="Concept" htmlFor="content-concept">
          <select
            id="content-concept"
            className={fieldClass}
            value={conceptId ?? ""}
            onChange={(e) => select(e.target.value)}
          >
            <option value="">Choose a concept…</option>
            {clusters.map((cl) => (
              <optgroup key={cl} label={cl}>
                {concepts
                  .filter((c) => c.cluster === cl)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </Field>
      </div>

      {!conceptId ? (
        <EmptyState
          icon={<FileText />}
          title="Pick a concept"
          description="Its note sections and quiz questions appear here, with answer statistics."
        />
      ) : content.isPending ? (
        <Skeleton className="h-96 w-full" aria-label="Loading content" />
      ) : content.error || !data ? (
        <ErrorState
          message={content.error?.message}
          requestId={content.error instanceof ApiError ? content.error.requestId : undefined}
          onRetry={() => void content.refetch()}
        />
      ) : (
        <Tabs value={tab} onValueChange={(v) => setTab(String(v))}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <TabsList>
              <TabsTrigger value="notes">Notes ({data.chunks.length})</TabsTrigger>
              <TabsTrigger value="questions">Questions ({data.questions.length})</TabsTrigger>
            </TabsList>
            <p className="text-sm text-muted">
              {unreviewed === 0 ? (
                <span className="inline-flex items-center gap-1 text-success">
                  <BookOpenCheck aria-hidden className="size-4" /> Everything reviewed
                </span>
              ) : (
                `${unreviewed} item${unreviewed === 1 ? "" : "s"} not yet reviewed`
              )}
            </p>
          </div>
          <TabsContent value="notes" className="mt-4 space-y-3">
            {data.chunks.length === 0 ? (
              <EmptyState
                icon={<FileText />}
                title="No note sections"
                description="Approve tagged chunks from an ingested document, or add a notes file and re-seed."
              />
            ) : (
              data.chunks.map((c) => (
                <ChunkCard
                  key={`${c.id}-${c.heading}-${c.reviewed}`}
                  chunk={c}
                  kinds={data.chunk_kinds}
                  conceptId={data.concept.id}
                  open={openChunk === c.id}
                  onOpen={setOpenChunk}
                />
              ))
            )}
          </TabsContent>
          <TabsContent value="questions" className="mt-4 space-y-3">
            <label className="flex items-center gap-2 text-sm text-muted">
              <input
                type="checkbox"
                checked={onlyFlagged}
                onChange={(e) => setOnlyFlagged(e.target.checked)}
                className="size-4 accent-[var(--primary)]"
              />
              Only questions with statistical flags
            </label>
            {questions.length === 0 ? (
              <EmptyState
                icon={<FileText />}
                title={onlyFlagged ? "No flagged questions" : "No questions"}
                description={
                  onlyFlagged
                    ? "Flags appear after 10+ attempts (too easy / too hard) or 20+ (discrimination)."
                    : "This concept has no questions yet."
                }
              />
            ) : (
              <ul className="space-y-3">
                {questions.map((q) => (
                  <QuestionRow
                    key={q.id}
                    q={q}
                    conceptId={data.concept.id}
                    onEdit={() => setEditing(q)}
                  />
                ))}
              </ul>
            )}
          </TabsContent>
        </Tabs>
      )}

      <Dialog open={editing !== null} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle>Edit question</DialogTitle>
            <DialogDescription>
              {editing?.id} · validated with the same rules as the question files.
            </DialogDescription>
          </DialogHeader>
          {editing && data && (
            <QuestionForm
              key={editing.id}
              question={editing}
              concepts={concepts}
              conceptName={data.concept.name}
              onDone={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
