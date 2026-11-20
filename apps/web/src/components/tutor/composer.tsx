"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUp, Square } from "lucide-react";
import { forwardRef, useImperativeHandle, useRef, useState } from "react";

import { USAGE_KEY } from "@/components/app/usage-card";
import { Button } from "@/components/ui/button";
import { api, type UsageSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

export const DEFAULT_MAX_INPUT = 2000;

export interface ComposerHandle {
  focus: () => void;
  setText: (text: string) => void;
}

interface ComposerProps {
  streaming: boolean;
  disabled?: boolean;
  onSend: (text: string) => Promise<boolean> | boolean;
  onStop: () => void;
  placeholder?: string;
  children?: React.ReactNode;
}

/**
 * Message box: Enter sends, Shift+Enter adds a line, Esc stops a streaming answer. The counter
 * follows the student's real input limit from GET /me/usage.
 */
export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { streaming, disabled, onSend, onStop, placeholder = "Ask about any DSA topic…", children },
  ref,
) {
  const [text, setText] = useState("");
  const area = useRef<HTMLTextAreaElement>(null);
  const usage = useQuery({
    queryKey: USAGE_KEY,
    queryFn: () => api<UsageSummary>("/me/usage"),
    staleTime: 60_000,
  });
  const max = usage.data?.limits.max_input_chars ?? DEFAULT_MAX_INPUT;
  const over = text.length > max;
  useImperativeHandle(ref, () => ({
    focus: () => area.current?.focus(),
    setText: (t: string) => {
      setText(t);
      requestAnimationFrame(() => area.current?.focus());
    },
  }));

  const submit = async () => {
    const t = text.trim();
    if (!t || over || streaming || disabled) return;
    setText("");
    const ok = await onSend(t);
    if (!ok) setText(t); // rejected before streaming: keep the question
  };

  return (
    <form
      className="rounded-2xl border border-border bg-surface p-2 shadow-sm focus-within:ring-2 focus-within:ring-ring"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
      <label htmlFor="tutor-input" className="sr-only">
        Your question
      </label>
      <textarea
        id="tutor-input"
        ref={area}
        value={text}
        rows={1}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            void submit();
          } else if (e.key === "Escape" && streaming) {
            e.preventDefault();
            onStop();
          }
        }}
        placeholder={placeholder}
        aria-describedby="tutor-input-help"
        className="field-sizing-content max-h-48 min-h-10 w-full resize-none bg-transparent px-2 py-2 text-sm text-text outline-none placeholder:text-muted"
      />
      <div className="flex items-center gap-2 px-1">
        {children}
        <span
          id="tutor-input-help"
          className={cn("ml-auto text-xs tabular-nums", over ? "text-danger" : "text-muted")}
          aria-live={over ? "polite" : undefined}
        >
          <span className="sr-only">Enter to send, Shift+Enter for a new line. </span>
          {text.length}/{max}
        </span>
        {streaming ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={onStop}
            aria-label="Stop generating"
          >
            <Square className="size-3.5 fill-current" />
          </Button>
        ) : (
          <Button
            type="submit"
            size="icon"
            disabled={!text.trim() || over || disabled}
            aria-label="Send"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
    </form>
  );
});
