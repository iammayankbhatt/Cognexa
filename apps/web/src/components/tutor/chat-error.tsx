"use client";

import { Clock, RefreshCw, TriangleAlert, WifiOff, X } from "lucide-react";
import Link from "next/link";

import { Button, buttonVariants } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { friendlyError } from "@/lib/errors";
import type { TurnError } from "@/lib/tutor/use-tutor";

const QUOTA_CODES = new Set(["QUOTA_EXCEEDED", "GLOBAL_CAP", "RATE_LIMITED"]);

/** Error card under the conversation: quota (no retry, links to non-AI features), model down
 * (retry), network loss (retry). */
export function ChatError({
  error,
  onRetry,
  onDismiss,
}: {
  error: TurnError;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  const e = error.error;
  const apiErr = e instanceof ApiError ? e : new ApiError(503, e.code, e.message);
  const friendly =
    apiErr.code === "internal_error"
      ? { title: "Something went wrong", description: apiErr.message }
      : friendlyError(apiErr);
  const quota = QUOTA_CODES.has(apiErr.code);
  const offline = apiErr.code === "network_error";
  const Icon = quota ? Clock : offline ? WifiOff : TriangleAlert;
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-xl border border-danger/40 bg-danger/5 p-4"
    >
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0 text-danger" />
      <div className="min-w-0 flex-1 space-y-2">
        <p className="text-sm font-semibold text-text">{friendly.title}</p>
        <p className="text-sm text-muted">{friendly.description}</p>
        <div className="flex flex-wrap gap-2">
          {quota ? (
            <>
              <Link
                href="/app/review"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Go to Review
              </Link>
              <Link
                href="/app/quizzes"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Take a quiz
              </Link>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <RefreshCw aria-hidden className="size-3.5" />
              Try again
            </Button>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        className="rounded p-1 text-muted outline-none hover:bg-surface-2 hover:text-text focus-visible:ring-2 focus-visible:ring-ring"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}
