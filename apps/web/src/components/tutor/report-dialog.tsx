"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import type { ReportReason } from "@/lib/tutor/types";

const REASONS: { value: ReportReason; label: string }[] = [
  { value: "incorrect", label: "It is wrong" },
  { value: "incomplete", label: "It is incomplete" },
  { value: "off_topic", label: "It does not answer my question" },
  { value: "harmful", label: "It is harmful or inappropriate" },
  { value: "other", label: "Something else" },
];
export const MAX_COMMENT = 2000;

interface ReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (reason: ReportReason, comment: string) => Promise<void>;
}

export function ReportDialog({ open, onOpenChange, onSubmit }: ReportDialogProps) {
  const [reason, setReason] = useState<ReportReason>("incorrect");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await onSubmit(reason, comment.trim());
      setComment("");
      onOpenChange(false);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Report this answer</DialogTitle>
          <DialogDescription>
            A reviewer will check it. Reported answers are never reused from the cache.
          </DialogDescription>
        </DialogHeader>
        <fieldset className="space-y-2">
          <legend className="mb-1 text-sm font-medium">What is wrong?</legend>
          {REASONS.map((r) => (
            <label key={r.value} className="flex cursor-pointer items-center gap-2 text-sm">
              <input
                type="radio"
                name="report-reason"
                value={r.value}
                checked={reason === r.value}
                onChange={() => setReason(r.value)}
                className="size-4 accent-[var(--primary)]"
              />
              {r.label}
            </label>
          ))}
        </fieldset>
        <div className="space-y-1.5">
          <Label htmlFor="report-comment">Details (optional)</Label>
          <textarea
            id="report-comment"
            value={comment}
            maxLength={MAX_COMMENT}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            className="w-full resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="What should the answer have said?"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => void submit()} disabled={busy}>
            {busy ? "Sending…" : "Send report"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
