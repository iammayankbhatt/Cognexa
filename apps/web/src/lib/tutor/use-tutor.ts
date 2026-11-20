"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, useState } from "react";

import { api, apiStream, ApiError } from "@/lib/api";
import { readSSE } from "@/lib/tutor/sse";
import { stripTrailer } from "@/lib/tutor/text";
import { toChatMessages } from "@/lib/tutor/threads";
import type {
  ChatMessage,
  CompareResult,
  DoneData,
  Mode,
  RetrievalTrace,
  StreamErrorData,
  Suggestions,
  Thread,
  ThreadDetail,
  ThreadPage,
} from "@/lib/tutor/types";

export const THREADS_KEY = ["tutor", "threads"] as const;
export const threadKey = (id: string) => ["tutor", "thread", id] as const;

export function useThreads(q: string, archived = false) {
  return useQuery({
    queryKey: [...THREADS_KEY, { q, archived }],
    queryFn: () => {
      const params = new URLSearchParams({ page_size: "100", archived: String(archived) });
      if (q.trim()) params.set("q", q.trim());
      return api<ThreadPage>(`/tutor/threads?${params}`);
    },
    placeholderData: keepPreviousData,
  });
}

export function useThread(id: string | null) {
  return useQuery({
    queryKey: threadKey(id ?? "none"),
    queryFn: () => api<ThreadDetail>(`/tutor/threads/${id}`),
    enabled: Boolean(id),
  });
}

export function useSuggestions() {
  return useQuery({
    queryKey: ["tutor", "suggestions"],
    queryFn: () => api<Suggestions>("/tutor/suggestions"),
    staleTime: 5 * 60_000,
  });
}

export function useThreadMutations() {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: THREADS_KEY });
  const patch = useMutation({
    mutationFn: ({ id, ...body }: { id: string; title?: string; archived?: boolean }) =>
      api<Thread>(`/tutor/threads/${id}`, { method: "PATCH", body }),
    onSuccess: (t) => {
      void refresh();
      void qc.invalidateQueries({ queryKey: threadKey(t.id) });
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api<void>(`/tutor/threads/${id}`, { method: "DELETE" }),
    onSuccess: () => void refresh(),
  });
  return { patch, remove };
}

export function useFeedback(threadId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      messageId,
      ...body
    }: {
      messageId: string;
      rating?: -1 | 0 | 1;
      report?: { reason: string; comment?: string };
    }) =>
      api<{ message_id: string; rating: -1 | 1 | null; reported: boolean }>(
        `/tutor/messages/${messageId}/feedback`,
        { method: "POST", body },
      ),
    onSuccess: () => {
      if (threadId) void qc.invalidateQueries({ queryKey: threadKey(threadId) });
    },
  });
}

export function useCompare() {
  return useMutation({
    mutationFn: (question: string) =>
      api<CompareResult>("/tutor/compare", { method: "POST", body: { question } }),
  });
}

// ---------------------------------------------------------------- the streaming chat

interface Pending {
  /** Each turn has an id; a turn that finishes after a newer one started never touches it. */
  runId: number;
  /** The thread the turn belongs to: it is only shown while that thread is open. */
  threadId: string;
  /** Messages shown before the in-flight turn (snapshot taken when it started). */
  base: ChatMessage[];
  items: ChatMessage[];
}

export interface TurnError {
  /** The assistant message the error belongs to, if any part of it was saved. */
  messageId: string | null;
  error: ApiError | StreamErrorData;
  /** What "Try again" does. */
  retry:
    { kind: "regenerate"; messageId: string } | { kind: "resend"; text: string; replaces?: string };
}

let localSeq = 0;
const localId = (p: string) => `local-${p}-${Date.now()}-${++localSeq}`;

function blankAssistant(mode: Mode): ChatMessage {
  return {
    id: localId("a"),
    role: "assistant",
    content: "",
    mode,
    status: "streaming",
    trace: null,
    followups: [],
    feedback: null,
    diagnostic: false,
    truncated: false,
    cached: false,
    local: true,
  };
}

function userMessage(text: string, mode: Mode): ChatMessage {
  return { ...blankAssistant(mode), id: localId("u"), role: "user", content: text, status: "done" };
}

interface Options {
  threadId: string | null;
  /** Called when the first message creates a thread. */
  onThreadCreated: (id: string) => void;
}

export function useTutorChat({ threadId, onThreadCreated }: Options) {
  const qc = useQueryClient();
  const thread = useThread(threadId);
  const [pending, setPending] = useState<Pending | null>(null);
  const [turnError, setTurnError] = useState<TurnError | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const runRef = useRef(0);

  const serverMessages = useMemo(
    () => (thread.data ? toChatMessages(thread.data.messages) : []),
    [thread.data],
  );
  const active = pending && pending.threadId === threadId ? pending : null;
  const messages = useMemo(
    () => (active ? [...active.base, ...active.items] : serverMessages),
    [active, serverMessages],
  );
  const streaming = active?.items.some((m) => m.status === "streaming") ?? false;

  const updateAssistant = useCallback((runId: number, fn: (m: ChatMessage) => ChatMessage) => {
    setPending((p) =>
      p && p.runId === runId
        ? { ...p, items: p.items.map((m) => (m.role === "assistant" ? fn(m) : m)) }
        : p,
    );
  }, []);

  const settle = useCallback(
    async (id: string, runId: number) => {
      await Promise.all([
        qc.refetchQueries({ queryKey: threadKey(id) }),
        qc.invalidateQueries({ queryKey: THREADS_KEY }),
        qc.invalidateQueries({ queryKey: ["me"] }),
      ]);
      setPending((p) => (p && p.runId === runId ? null : p));
    },
    [qc],
  );

  /**
   * Run one streamed turn. Returns false when the request was rejected before streaming (quota,
   * validation, network), so the caller can put the text back in the composer.
   */
  const run = useCallback(
    async (
      id: string,
      path: string,
      body: unknown,
      next: Omit<Pending, "threadId" | "runId">,
      retry: TurnError["retry"],
    ): Promise<boolean> => {
      const runId = ++runRef.current;
      const update = (fn: (m: ChatMessage) => ChatMessage) => updateAssistant(runId, fn);
      const fail = (e: TurnError) => {
        if (runRef.current === runId) setTurnError(e);
      };
      setTurnError(null);
      setPending({ ...next, threadId: id, runId });
      const controller = new AbortController();
      abortRef.current = controller;
      let started = false;
      let doneId: string | null = null;
      try {
        const res = await apiStream(path, body, controller.signal);
        started = true;
        for await (const msg of readSSE(res.body!)) {
          const data: unknown = JSON.parse(msg.data);
          if (msg.event === "trace") {
            update((m) => ({ ...m, trace: data as RetrievalTrace }));
          } else if (msg.event === "token") {
            const text = (data as { text: string }).text;
            update((m) => ({ ...m, content: m.content + text }));
          } else if (msg.event === "followups") {
            update((m) => ({ ...m, followups: (data as { items: string[] }).items }));
          } else if (msg.event === "done") {
            const d = data as DoneData;
            doneId = d.message_id;
            update((m) => ({
              ...m,
              id: d.message_id,
              content: d.content,
              status: "done",
              diagnostic: d.diagnostic,
              cached: d.cached,
              moderated: d.moderated,
              provider: d.usage.provider,
              model: d.usage.model,
              tokensIn: d.usage.tokens_in,
              tokensOut: d.usage.tokens_out,
              latencyMs: d.usage.latency_ms,
            }));
          } else if (msg.event === "error") {
            const e = data as StreamErrorData;
            update((m) => ({ ...m, status: "error", error: e }));
            fail({
              messageId: e.message_id,
              error: e,
              retry: e.message_id ? { kind: "regenerate", messageId: e.message_id } : retry,
            });
          }
        }
        if (!doneId) {
          // The stream ended without `done`/`error` (connection dropped): the server keeps what
          // it had; show the saved state.
          update((m) => (m.status === "streaming" ? { ...m, status: "stopped" } : m));
        }
        await settle(id, runId);
        return true;
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          update((m) => ({ ...m, status: "stopped" }));
          // Give the server a moment to save the partial answer, then show the saved thread.
          await new Promise((r) => setTimeout(r, 400));
          await settle(id, runId);
          return true;
        }
        const apiErr =
          err instanceof ApiError
            ? err
            : new ApiError(0, "network_error", "The connection was lost while answering.");
        if (!started) {
          setPending((p) => (p && p.runId === runId ? null : p));
          fail({ messageId: null, error: apiErr, retry });
          return false;
        }
        update((m) => ({ ...m, status: "error" }));
        fail({ messageId: null, error: apiErr, retry });
        await settle(id, runId).catch(() => undefined);
        return true;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [settle, updateAssistant],
  );

  const send = useCallback(
    async (text: string, mode: Mode = "graphrag"): Promise<boolean> => {
      let id = threadId;
      if (!id) {
        try {
          const created = await api<Thread>("/tutor/threads", { method: "POST", body: {} });
          id = created.id;
          qc.setQueryData(threadKey(id), { thread: created, messages: [] } satisfies ThreadDetail);
          onThreadCreated(id);
        } catch (err) {
          setTurnError({
            messageId: null,
            error: err instanceof ApiError ? err : new ApiError(0, "network_error", String(err)),
            retry: { kind: "resend", text },
          });
          return false;
        }
      }
      return run(
        id,
        `/tutor/threads/${id}/messages`,
        { content: text, mode },
        { base: messages, items: [userMessage(text, mode), blankAssistant(mode)] },
        { kind: "resend", text },
      );
    },
    [threadId, run, messages, qc, onThreadCreated],
  );

  const regenerate = useCallback(
    (messageId: string) => {
      if (!threadId) return Promise.resolve(false);
      const at = messages.findIndex((m) => m.id === messageId);
      const mode = messages[at]?.mode ?? "graphrag";
      return run(
        threadId,
        `/tutor/messages/${messageId}/regenerate`,
        undefined,
        { base: messages.slice(0, at < 0 ? messages.length : at), items: [blankAssistant(mode)] },
        { kind: "regenerate", messageId },
      );
    },
    [threadId, messages, run],
  );

  const edit = useCallback(
    (messageId: string, text: string) => {
      if (!threadId) return Promise.resolve(false);
      const at = messages.findIndex((m) => m.id === messageId);
      const mode = messages[at]?.mode ?? "graphrag";
      return run(
        threadId,
        `/tutor/messages/${messageId}/edit`,
        { content: text },
        {
          base: messages.slice(0, at < 0 ? messages.length : at),
          items: [userMessage(text, mode), blankAssistant(mode)],
        },
        { kind: "resend", text, replaces: messageId },
      );
    },
    [threadId, messages, run],
  );

  const retry = useCallback(async () => {
    const r = turnError?.retry;
    if (!r) return;
    if (r.kind === "regenerate") await regenerate(r.messageId);
    else if (r.replaces) await edit(r.replaces, r.text);
    else {
      // The question may already be saved without an answer: resend replaces it if so.
      const lastUser = [...serverMessages].reverse().find((m) => m.role === "user");
      const unanswered = lastUser && serverMessages[serverMessages.length - 1]?.id === lastUser.id;
      if (unanswered && lastUser.content === r.text) await edit(lastUser.id, r.text);
      else await send(r.text);
    }
  }, [turnError, regenerate, edit, send, serverMessages]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  return {
    thread,
    messages,
    streaming,
    /** A turn is in flight in the open thread (another thread's turn may finish meanwhile). */
    busy: active !== null,
    turnError,
    dismissError: () => setTurnError(null),
    send,
    regenerate,
    edit,
    retry,
    stop,
  };
}

/** Text to display for an assistant message while it streams (never shows trailer text). */
export function visibleText(m: ChatMessage): string {
  return m.status === "streaming" ? stripTrailer(m.content) : m.content;
}
