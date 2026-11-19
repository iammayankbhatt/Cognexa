import { TriangleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  message?: string;
  /** Request ID from the API error envelope, shown so users can report it. */
  requestId?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Something went wrong",
  message = "We couldn't load this. Please try again.",
  requestId,
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-danger/40 bg-danger/5 px-6 py-12 text-center",
        className,
      )}
    >
      <span
        aria-hidden
        className="flex size-12 items-center justify-center rounded-full bg-danger/10 text-danger"
      >
        <TriangleAlert className="size-6" />
      </span>
      <h3 className="text-lg font-semibold text-text">{title}</h3>
      <p className="max-w-md text-sm text-muted">{message}</p>
      {requestId && (
        <p className="font-mono text-xs text-muted">
          Request ID: <span className="text-text">{requestId}</span>
        </p>
      )}
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-2">
          Try again
        </Button>
      )}
    </div>
  );
}
