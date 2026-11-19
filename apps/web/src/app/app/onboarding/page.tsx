"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ME_KEY, useMe } from "@/components/app/me-provider";
import { FormMessage } from "@/components/auth/auth-shell";
import { Button } from "@/components/ui/button";
import { api, ApiError, type Me } from "@/lib/api";
import { cn } from "@/lib/utils";

type Level = "beginner" | "intermediate" | "advanced";

const LEVELS: { id: Level; title: string; blurb: string }[] = [
  { id: "beginner", title: "Beginner", blurb: "New to DSA. Start from the foundations." },
  { id: "intermediate", title: "Intermediate", blurb: "Comfortable with arrays and recursion." },
  { id: "advanced", title: "Advanced", blurb: "Know the classics, want depth and gaps filled." },
];

export default function OnboardingPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: me } = useMe();
  const [step, setStep] = useState(0);
  const [level, setLevel] = useState<Level | null>(null);

  const finish = useMutation({
    mutationFn: () =>
      api<Me>("/me/onboarding-complete", {
        method: "POST",
        body: { experience_level: level },
      }),
    onSuccess: (next) => {
      qc.setQueryData(ME_KEY, next);
      toast.success("You're all set.");
      router.replace("/app");
    },
  });

  const first = (me?.display_name ?? "").split(" ")[0];

  return (
    <div className="mx-auto max-w-xl space-y-6 py-6">
      <ol className="flex items-center gap-2" aria-label="Onboarding progress">
        {["Welcome", "Your level", "Diagnostic"].map((label, i) => (
          <li
            key={label}
            aria-current={i === step ? "step" : undefined}
            className={cn(
              "flex flex-1 items-center gap-2 text-xs",
              i <= step ? "text-text" : "text-muted",
            )}
          >
            <span
              className={cn(
                "flex size-6 items-center justify-center rounded-full border text-[11px]",
                i < step
                  ? "border-accent bg-accent text-bg"
                  : i === step
                    ? "border-accent text-accent"
                    : "border-border",
              )}
            >
              {i < step ? <Check aria-hidden className="size-3" /> : i + 1}
            </span>
            {label}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <section className="space-y-4 rounded-2xl border border-border bg-surface p-6">
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome{first ? `, ${first}` : ""}
          </h1>
          <p className="text-muted">
            Cognexa maps your questions onto a graph of 69 DSA concepts, so it can explain the
            prerequisite you are missing, not just the topic you named. Two quick questions and you
            are in.
          </p>
          <Button className="h-9" onClick={() => setStep(1)}>
            Get started <ArrowRight aria-hidden />
          </Button>
        </section>
      )}

      {step === 1 && (
        <section className="space-y-4 rounded-2xl border border-border bg-surface p-6">
          <h1 className="text-2xl font-semibold tracking-tight">How familiar are you with DSA?</h1>
          <div role="radiogroup" aria-label="Experience level" className="space-y-2">
            {LEVELS.map((l) => (
              <button
                key={l.id}
                type="button"
                role="radio"
                aria-checked={level === l.id}
                onClick={() => setLevel(l.id)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  level === l.id
                    ? "border-accent bg-surface-2"
                    : "border-border hover:bg-surface-2",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "mt-1 size-4 shrink-0 rounded-full border",
                    level === l.id ? "border-accent bg-accent" : "border-muted",
                  )}
                />
                <span>
                  <span className="block font-medium text-text">{l.title}</span>
                  <span className="block text-sm text-muted">{l.blurb}</span>
                </span>
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" className="h-9" onClick={() => setStep(0)}>
              Back
            </Button>
            <Button className="h-9" disabled={!level} onClick={() => setStep(2)}>
              Continue <ArrowRight aria-hidden />
            </Button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="space-y-4 rounded-2xl border border-border bg-surface p-6">
          <h1 className="text-2xl font-semibold tracking-tight">Diagnostic quiz</h1>
          <FormMessage tone="info">
            Placeholder: the 10-question diagnostic is built in Phase 8 and replaces this step. For
            now your answers about experience level are saved and you can start exploring.
          </FormMessage>
          {finish.error && (
            <FormMessage tone="error">
              {finish.error instanceof ApiError ? finish.error.message : "Something went wrong."}
            </FormMessage>
          )}
          <div className="flex gap-2">
            <Button variant="ghost" className="h-9" onClick={() => setStep(1)}>
              Back
            </Button>
            <Button className="h-9" disabled={finish.isPending} onClick={() => finish.mutate()}>
              {finish.isPending && <Loader2 aria-hidden className="animate-spin" />}
              {finish.isPending ? "Saving…" : "Go to my dashboard"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
