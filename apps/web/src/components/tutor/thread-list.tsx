"use client";

import {
  Archive,
  ArchiveRestore,
  MessageSquarePlus,
  MoreHorizontal,
  Pencil,
  Search,
  Trash2,
} from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { groupThreads } from "@/lib/tutor/threads";
import type { Thread } from "@/lib/tutor/types";
import { useThreadMutations, useThreads } from "@/lib/tutor/use-tutor";
import { cn } from "@/lib/utils";

const UNDO_MS = 5000;

interface ThreadListProps {
  activeId: string | null;
  onSelect: (id: string | null) => void;
}

export function ThreadList({ activeId, onSelect }: ThreadListProps) {
  const [q, setQ] = useState("");
  const [archived, setArchived] = useState(false);
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [renaming, setRenaming] = useState<string | null>(null);
  const { data, isPending, error, refetch } = useThreads(q, archived);
  const { patch, remove } = useThreadMutations();
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const threads = (data?.items ?? []).filter((t) => !hidden.has(t.id));
  const groups = groupThreads(threads);

  const hide = (id: string, on: boolean) =>
    setHidden((h) => {
      const next = new Set(h);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const deleteWithUndo = (t: Thread) => {
    hide(t.id, true);
    if (activeId === t.id) onSelect(null);
    const timer = setTimeout(() => {
      timers.current.delete(t.id);
      remove.mutate(t.id, {
        onError: () => {
          hide(t.id, false);
          toast.error("Could not delete the chat.");
        },
      });
    }, UNDO_MS);
    timers.current.set(t.id, timer);
    toast(`Deleted "${t.title}"`, {
      duration: UNDO_MS,
      action: {
        label: "Undo",
        onClick: () => {
          clearTimeout(timers.current.get(t.id));
          timers.current.delete(t.id);
          hide(t.id, false);
        },
      },
    });
  };

  const setArchivedFlag = (t: Thread, value: boolean) => {
    patch.mutate(
      { id: t.id, archived: value },
      {
        onSuccess: () => {
          if (value && activeId === t.id) onSelect(null);
          toast(value ? "Chat archived" : "Chat restored");
        },
        onError: () => toast.error("Could not update the chat."),
      },
    );
  };

  return (
    <nav aria-label="Chat history" className="flex h-full flex-col">
      <div className="space-y-2 border-b border-border p-3">
        <Button className="w-full justify-center" onClick={() => onSelect(null)}>
          <MessageSquarePlus aria-hidden className="size-4" />
          New chat
        </Button>
        <div className="relative">
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted"
          />
          <label htmlFor="thread-search" className="sr-only">
            Search chats
          </label>
          <input
            id="thread-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search chats"
            maxLength={100}
            className="h-8 w-full rounded-lg border border-border bg-bg pr-2 pl-8 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <div className="flex gap-1 text-xs" role="group" aria-label="Show">
          {[false, true].map((a) => (
            <button
              key={String(a)}
              type="button"
              aria-pressed={archived === a}
              onClick={() => setArchived(a)}
              className={cn(
                "rounded-md px-2 py-1 outline-none focus-visible:ring-2 focus-visible:ring-ring",
                archived === a ? "bg-surface-2 text-text" : "text-muted hover:text-text",
              )}
            >
              {a ? "Archived" : "Chats"}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2">
        {isPending ? (
          <div className="space-y-2 p-1">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        ) : error ? (
          <div className="p-3 text-sm text-muted">
            Could not load your chats.{" "}
            <button type="button" className="text-accent underline" onClick={() => void refetch()}>
              Retry
            </button>
          </div>
        ) : groups.length === 0 ? (
          <p className="p-3 text-sm text-muted">
            {q
              ? "No chats match your search."
              : archived
                ? "No archived chats."
                : "No chats yet. Ask your first question."}
          </p>
        ) : (
          groups.map(({ group, threads: items }) => (
            <div key={group} className="mb-3">
              <h3 className="px-2 py-1 text-[11px] font-semibold tracking-wide text-muted uppercase">
                {group}
              </h3>
              <ul className="space-y-0.5">
                {items.map((t) => (
                  <li key={t.id}>
                    {renaming === t.id ? (
                      <RenameField
                        initial={t.title}
                        onDone={(title) => {
                          setRenaming(null);
                          if (title && title !== t.title) {
                            patch.mutate(
                              { id: t.id, title },
                              { onError: () => toast.error("Could not rename the chat.") },
                            );
                          }
                        }}
                      />
                    ) : (
                      <div
                        className={cn(
                          "group flex items-center rounded-lg text-sm transition-colors duration-150",
                          activeId === t.id
                            ? "bg-surface-2 text-text"
                            : "text-muted hover:bg-surface-2/60 hover:text-text",
                        )}
                      >
                        <button
                          type="button"
                          onClick={() => onSelect(t.id)}
                          aria-current={activeId === t.id ? "true" : undefined}
                          className="min-w-0 flex-1 truncate rounded-lg px-2 py-1.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          title={t.title}
                        >
                          {t.title}
                        </button>
                        <DropdownMenu>
                          <DropdownMenuTrigger
                            aria-label={`Actions for ${t.title}`}
                            className="mr-1 rounded p-1 opacity-0 outline-none group-focus-within:opacity-100 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring aria-expanded:opacity-100"
                          >
                            <MoreHorizontal className="size-4" />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => setRenaming(t.id)}>
                              <Pencil aria-hidden className="size-3.5" /> Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => setArchivedFlag(t, !t.archived)}>
                              {t.archived ? (
                                <ArchiveRestore aria-hidden className="size-3.5" />
                              ) : (
                                <Archive aria-hidden className="size-3.5" />
                              )}
                              {t.archived ? "Restore" : "Archive"}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              variant="destructive"
                              onClick={() => deleteWithUndo(t)}
                            >
                              <Trash2 aria-hidden className="size-3.5" /> Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </div>
    </nav>
  );
}

function RenameField({
  initial,
  onDone,
}: {
  initial: string;
  onDone: (title: string | null) => void;
}) {
  const [value, setValue] = useState(initial);
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onDone(value.trim() || null);
      }}
    >
      <label className="sr-only" htmlFor="thread-rename">
        Chat title
      </label>
      <input
        id="thread-rename"
        autoFocus
        value={value}
        maxLength={200}
        onChange={(e) => setValue(e.target.value)}
        onBlur={() => onDone(value.trim() || null)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onDone(null);
        }}
        className="h-8 w-full rounded-lg border border-accent bg-bg px-2 text-sm outline-none"
      />
    </form>
  );
}
