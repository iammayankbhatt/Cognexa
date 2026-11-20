"use client";

import {
  Check,
  Copy,
  Flag,
  Loader2,
  Pencil,
  RefreshCw,
  ThumbsDown,
  ThumbsUp,
  TriangleAlert,
} from "lucide-react";
import { useState } from "react";

import { Markdown } from "@/components/tutor/markdown";
import { QuickCheck } from "@/components/tutor/quick-check";
import { TraceStrip } from "@/components/tutor/trace-strip";
import { Button } from "@/components/ui/button";
import { visibleText } from "@/lib/tutor/use-tutor";
import type { ChatMessage } from "@/lib/tutor/types";
import { cn } from "@/lib/utils";

function IconAction({
  label,
  onClick,
  pressed,
  disabled,
  children,
}: {
  label: string;
  onClick: () => void;
  pressed?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      aria-pressed={pressed}
      className={cn(
        "rounded-md p-1.5 text-muted transition-colors duration-150 outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40",
        pressed && "text-accent",
      )}
    >
      {children}
    </button>
  );
}

interface UserMessageProps {
  message: ChatMessage;
  canEdit: boolean;
  onEdit: (text: string) => void;
}

export function UserMessage({ message, canEdit, onEdit }: UserMessageProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.content);
  if (editing) {
    return (
      <form
        className="ml-auto w-full max-w-[85%] space-y-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (draft.trim()) {
            onEdit(draft.trim());
            setEditing(false);
          }
        }}
      >
        <label htmlFor={`edit-${message.id}`} className="sr-only">
          Edit your question
        </label>
        <textarea
          id={`edit-${message.id}`}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Escape") setEditing(false);
          }}
          className="w-full resize-none rounded-xl border border-border bg-surface px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" size="sm" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={!draft.trim()}>
            Save and resend
          </Button>
        </div>
      </form>
    );
  }
  return (
    <div className="group ml-auto flex max-w-[85%] items-start gap-1">
      {canEdit && (
        <span className="opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100">
          <IconAction
            label="Edit and resend"
            onClick={() => {
              setDraft(message.content);
              setEditing(true);
            }}
          >
            <Pencil className="size-3.5" />
          </IconAction>
        </span>
      )}
      <div className="rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm whitespace-pre-wrap text-primary-fg">
        {message.content}
      </div>
    </div>
  );
}

interface AssistantMessageProps {
  message: ChatMessage;
  names: Record<string, string>;
  isLatest: boolean;
  busy: boolean;
  quickCheckActive: boolean;
  onFollowup: (text: string) => void;
  onRegenerate: () => void;
  onRate: (rating: -1 | 0 | 1) => void;
  onReport: () => void;
  onWhy: () => void;
  onQuickCheckAnswer: (text: string) => void;
}

export function AssistantMessage({
  message,
  names,
  isLatest,
  busy,
  quickCheckActive,
  onFollowup,
  onRegenerate,
  onRate,
  onReport,
  onWhy,
  onQuickCheckAnswer,
}: AssistantMessageProps) {
  const [copied, setCopied] = useState(false);
  const text = visibleText(message);
  const streaming = message.status === "streaming";
  const saved = !message.local;
  const rating = message.feedback?.rating ?? null;
  const reported = message.feedback?.reported ?? false;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked
    }
  };

  return (
    <article className="group flex flex-col gap-2" aria-busy={streaming}>
      {message.trace ? (
        <TraceStrip trace={message.trace} onOpen={onWhy} />
      ) : (
        streaming && (
          <p className="flex items-center gap-2 text-xs text-muted">
            <Loader2 aria-hidden className="size-3.5 animate-spin text-accent" />
            Finding the concepts behind your question…
          </p>
        )
      )}

      {message.diagnostic ? (
        <QuickCheck
          question={text}
          active={quickCheckActive}
          disabled={busy}
          onAnswer={onQuickCheckAnswer}
        />
      ) : (
        <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3">
          {text ? (
            <Markdown text={text} conceptNames={names} />
          ) : streaming ? (
            <span className="inline-flex gap-1" aria-label="Writing">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="size-1.5 rounded-full bg-muted motion-safe:animate-pulse"
                  style={{ animationDelay: `${i * 150}ms` }}
                />
              ))}
            </span>
          ) : (
            <p className="text-sm text-muted">No answer was saved.</p>
          )}
          {streaming && text && (
            <span
              aria-hidden
              className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 bg-accent motion-safe:animate-pulse"
            />
          )}
          {message.status === "stopped" && (
            <p className="mt-2 text-xs text-muted">Stopped before the end.</p>
          )}
          {message.moderated && (
            <p className="mt-2 flex items-center gap-1 text-xs text-warning">
              <TriangleAlert aria-hidden className="size-3.5" />
              The original answer was withheld by a safety check.
            </p>
          )}
        </div>
      )}

      {!streaming && message.followups.length > 0 && isLatest && !message.diagnostic && (
        <div className="flex flex-wrap gap-2" aria-label="Suggested follow-up questions">
          {message.followups.map((f) => (
            <button
              key={f}
              type="button"
              disabled={busy}
              onClick={() => onFollowup(f)}
              className="rounded-full border border-border bg-surface px-3 py-1.5 text-left text-xs text-text transition-colors duration-150 outline-none hover:border-accent focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            >
              {f}
            </button>
          ))}
        </div>
      )}

      {!streaming && saved && !message.diagnostic && (
        <div className="-ml-1.5 flex items-center gap-0.5">
          <IconAction label={copied ? "Copied" : "Copy answer"} onClick={() => void copy()}>
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          </IconAction>
          <IconAction
            label="Helpful"
            pressed={rating === 1}
            onClick={() => onRate(rating === 1 ? 0 : 1)}
          >
            <ThumbsUp className="size-3.5" />
          </IconAction>
          <IconAction
            label="Not helpful"
            pressed={rating === -1}
            onClick={() => onRate(rating === -1 ? 0 : -1)}
          >
            <ThumbsDown className="size-3.5" />
          </IconAction>
          <IconAction
            label={reported ? "Reported" : "Report answer"}
            pressed={reported}
            onClick={onReport}
            disabled={reported}
          >
            <Flag className={cn("size-3.5", reported && "fill-current")} />
          </IconAction>
          {isLatest && (
            <IconAction label="Regenerate" onClick={onRegenerate} disabled={busy}>
              <RefreshCw className="size-3.5" />
            </IconAction>
          )}
          {reported && <span className="ml-1 text-xs text-muted">Reported for review</span>}
        </div>
      )}
    </article>
  );
}
