"use client";

import { GitCompareArrows, MessagesSquare, PanelRight } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { useMe } from "@/components/app/me-provider";
import { ErrorState } from "@/components/shared/error-state";
import { ChatEmpty } from "@/components/tutor/chat-empty";
import { ChatError } from "@/components/tutor/chat-error";
import { CompareView } from "@/components/tutor/compare-view";
import { Composer, type ComposerHandle } from "@/components/tutor/composer";
import { AssistantMessage, UserMessage } from "@/components/tutor/message-item";
import { ReportDialog } from "@/components/tutor/report-dialog";
import { ThreadList } from "@/components/tutor/thread-list";
import { WhyPanel } from "@/components/tutor/why-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import type { CompareResult } from "@/lib/tutor/types";
import { useCompare, useFeedback, useTutorChat } from "@/lib/tutor/use-tutor";
import { cn } from "@/lib/utils";

const STICK_PX = 80;

interface CompareEntry {
  id: number;
  question: string;
  result?: CompareResult;
  pending: boolean;
}

export function TutorWorkspace() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const urlThread = params.get("thread");
  // The active thread lives in state so a selection takes effect immediately; the URL mirrors it
  // (router.replace commits later, and a fast "New chat" + send must not reach the old thread:
  // BUG-027). Back/forward changes to the URL are adopted here.
  const [threadId, setThreadId] = useState<string | null>(urlThread);
  const [seenUrl, setSeenUrl] = useState<string | null>(urlThread);
  if (urlThread !== seenUrl) {
    setSeenUrl(urlThread);
    setThreadId(urlThread);
  }
  const me = useMe();
  const canCompare = me.data?.role === "admin" || me.data?.role === "reviewer";

  const select = useCallback(
    (id: string | null) => {
      // seenUrl is left alone: the URL still shows the old thread until the replace commits,
      // and that stale value must not be "adopted" back.
      setThreadId(id);
      router.replace(id ? `${pathname}?thread=${id}` : pathname, { scroll: false });
    },
    [router, pathname],
  );
  const chat = useTutorChat({ threadId, onThreadCreated: select });
  const feedback = useFeedback(threadId);
  const compare = useCompare();

  const [threadsOpen, setThreadsOpen] = useState(false);
  const [whyOpen, setWhyOpen] = useState(true);
  const [whyMobile, setWhyMobile] = useState(false);
  const [whyId, setWhyId] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [compareMode, setCompareMode] = useState(false);
  const [compares, setCompares] = useState<CompareEntry[]>([]);
  const [compareFor, setCompareFor] = useState<string | null>(threadId);
  if (compareFor !== threadId) {
    // Comparisons are not saved: they belong to the chat they were run in.
    setCompareFor(threadId);
    setCompares([]);
  }

  const composer = useRef<ComposerHandle>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  const { messages, streaming, busy } = chat;
  const names = useMemo(() => {
    const out: Record<string, string> = {};
    for (const m of messages) {
      for (const c of m.trace?.concepts ?? []) out[c.id] = c.name;
      for (const c of m.trace?.matched ?? []) out[c.id] = c.name;
    }
    return out;
  }, [messages]);
  const assistants = messages.filter((m) => m.role === "assistant");
  const latestAssistant = assistants[assistants.length - 1];
  const whyMessage =
    messages.find((m) => m.id === whyId && m.trace) ??
    [...assistants].reverse().find((m) => m.trace) ??
    null;
  const lastUserIndex = messages.map((m) => m.role).lastIndexOf("user");

  // Auto-scroll while the answer streams, unless the student scrolled up to read.
  const contentSize = messages.reduce((n, m) => n + m.content.length, 0) + compares.length;
  useEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [contentSize, messages.length]);

  useEffect(() => {
    if (!streaming) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") chat.stop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [streaming, chat]);

  useEffect(() => {
    composer.current?.focus();
  }, [threadId]);

  // "Ask the tutor about it" links (quiz results, concept pages) open /app/tutor?ask=<text>:
  // the question is put in the composer for the student to send or edit, once.
  const ask = params.get("ask");
  useEffect(() => {
    if (!ask) return;
    composer.current?.setText(ask.slice(0, 2000));
    router.replace(urlThread ? `${pathname}?thread=${urlThread}` : pathname, { scroll: false });
  }, [ask, router, pathname, urlThread]);

  const send = async (text: string) => {
    stick.current = true;
    if (compareMode && canCompare) {
      const id = Date.now();
      setCompares((c) => [...c, { id, question: text, pending: true }]);
      compare.mutate(text, {
        onSuccess: (result) =>
          setCompares((c) => c.map((e) => (e.id === id ? { ...e, result, pending: false } : e))),
        onError: (err) => {
          setCompares((c) => c.filter((e) => e.id !== id));
          toast.error(err instanceof ApiError ? err.message : "The comparison failed.");
        },
      });
      return true;
    }
    return chat.send(text);
  };

  const rate = (id: string, rating: -1 | 0 | 1) =>
    feedback.mutate(
      { messageId: id, rating },
      { onError: () => toast.error("Could not save your feedback.") },
    );

  const loadingThread = Boolean(threadId) && chat.thread.isPending && !busy;
  const threadError = chat.thread.error;

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] min-h-0">
      {/* thread list: side panel on desktop, drawer on mobile */}
      <aside className="hidden w-64 shrink-0 border-r border-border bg-surface md:block">
        <ThreadList activeId={threadId} onSelect={select} />
      </aside>
      {threadsOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            aria-label="Close chat history"
            className="absolute inset-0 bg-bg/70"
            onClick={() => setThreadsOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-72 border-r border-border bg-surface">
            <ThreadList
              activeId={threadId}
              onSelect={(id) => {
                setThreadsOpen(false);
                select(id);
              }}
            />
          </div>
        </div>
      )}

      <section className="flex min-w-0 flex-1 flex-col" aria-label="Tutor chat">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3">
          <button
            type="button"
            className="rounded p-1.5 text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring md:hidden"
            aria-label="Open chat history"
            onClick={() => setThreadsOpen(true)}
          >
            <MessagesSquare className="size-4" />
          </button>
          <h1 className="min-w-0 truncate text-sm font-semibold">
            {chat.thread.data?.thread.title ?? (threadId ? "" : "New chat")}
          </h1>
          <button
            type="button"
            onClick={() =>
              window.matchMedia("(min-width: 1024px)").matches
                ? setWhyOpen((o) => !o)
                : setWhyMobile(true)
            }
            aria-pressed={whyOpen}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring"
          >
            <PanelRight aria-hidden className="size-4" />
            Why this answer?
          </button>
        </div>

        <div
          ref={scroller}
          onScroll={(e) => {
            const el = e.currentTarget;
            stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_PX;
          }}
          className="flex-1 overflow-y-auto"
        >
          <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6">
            {threadError ? (
              <ErrorState
                title="Couldn't open this chat"
                message={threadError.message}
                requestId={threadError instanceof ApiError ? threadError.requestId : undefined}
                onRetry={() => void chat.thread.refetch()}
              />
            ) : loadingThread ? (
              <div className="space-y-4" aria-label="Loading chat">
                <Skeleton className="ml-auto h-10 w-2/3" />
                <Skeleton className="h-32 w-full" />
              </div>
            ) : messages.length === 0 && compares.length === 0 ? (
              <ChatEmpty onPick={(p) => void send(p)} />
            ) : (
              messages.map((m, i) =>
                m.role === "user" ? (
                  <UserMessage
                    key={m.id}
                    message={m}
                    canEdit={!busy && !m.local && i === lastUserIndex}
                    onEdit={(text) => void chat.edit(m.id, text)}
                  />
                ) : (
                  <div key={m.id} aria-live={m === latestAssistant ? "polite" : undefined}>
                    <AssistantMessage
                      message={m}
                      names={names}
                      isLatest={m === latestAssistant}
                      busy={busy}
                      quickCheckActive={
                        m === latestAssistant && m.diagnostic && i === messages.length - 1
                      }
                      onFollowup={(f) => void send(f)}
                      onRegenerate={() => void chat.regenerate(m.id)}
                      onRate={(r) => rate(m.id, r)}
                      onReport={() => setReportId(m.id)}
                      onWhy={() => {
                        setWhyId(m.id);
                        setWhyOpen(true);
                        if (!window.matchMedia("(min-width: 1024px)").matches) setWhyMobile(true);
                      }}
                      onQuickCheckAnswer={(t) => void send(t)}
                    />
                  </div>
                ),
              )
            )}
            {compares.map((c) => (
              <CompareView key={c.id} question={c.question} result={c.result} pending={c.pending} />
            ))}
            {chat.turnError && (
              <ChatError
                error={chat.turnError}
                onRetry={() => void chat.retry()}
                onDismiss={chat.dismissError}
              />
            )}
          </div>
        </div>

        <div className="mx-auto w-full max-w-3xl shrink-0 px-4 pb-4">
          <Composer
            ref={composer}
            streaming={streaming}
            disabled={busy && !streaming}
            onSend={send}
            onStop={chat.stop}
            placeholder={
              compareMode ? "Ask a question to compare GraphRAG with plain RAG…" : undefined
            }
          >
            {canCompare && (
              <button
                type="button"
                aria-pressed={compareMode}
                onClick={() => setCompareMode((v) => !v)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  compareMode ? "bg-surface-2 text-accent" : "text-muted hover:text-text",
                )}
              >
                <GitCompareArrows aria-hidden className="size-3.5" />
                Compare with plain RAG
              </button>
            )}
          </Composer>
          <p className="mt-1.5 text-center text-[11px] text-muted">
            Answers come only from the course notes and can still be wrong. Report anything that
            looks off.
          </p>
        </div>
      </section>

      {whyOpen && (
        <div className="hidden w-80 shrink-0 border-l border-border bg-surface lg:block">
          <WhyPanel message={whyMessage} onClose={() => setWhyOpen(false)} />
        </div>
      )}
      {whyMobile && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close panel"
            className="absolute inset-0 bg-bg/70"
            onClick={() => setWhyMobile(false)}
          />
          <div className="absolute inset-y-0 right-0 w-[min(22rem,100%)] border-l border-border bg-surface">
            <WhyPanel message={whyMessage} onClose={() => setWhyMobile(false)} />
          </div>
        </div>
      )}

      <ReportDialog
        open={reportId !== null}
        onOpenChange={(open) => !open && setReportId(null)}
        onSubmit={async (reason, comment) => {
          if (!reportId) return;
          await feedback.mutateAsync({
            messageId: reportId,
            report: { reason, comment: comment || undefined },
          });
          toast.success("Thanks — a reviewer will check this.");
        }}
      />
      <span className="sr-only" role="status" aria-live="polite">
        {streaming ? "Cognexa is answering." : ""}
      </span>
    </div>
  );
}
