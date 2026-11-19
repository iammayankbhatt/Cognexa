"use client";

import { useId } from "react";
import type { FieldError } from "react-hook-form";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface FormFieldProps extends Omit<React.ComponentProps<typeof Input>, "id"> {
  label: string;
  error?: FieldError;
  hint?: string;
  /** Rendered on the label row, right-aligned (e.g. a "Forgot password?" link). */
  labelAction?: React.ReactNode;
}

/** Label + input + accessible error message wired together with aria attributes. */
export function FormField({ label, error, hint, labelAction, ...inputProps }: FormFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        {labelAction}
      </div>
      <Input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={
          [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ") || undefined
        }
        {...inputProps}
      />
      {hint && !error && (
        <p id={hintId} className="text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="text-xs text-danger">
          {error.message}
        </p>
      )}
    </div>
  );
}
