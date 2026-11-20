"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ME_KEY, useMe } from "@/components/app/me-provider";
import { FormMessage } from "@/components/auth/auth-shell";
import { QuizPlayer } from "@/components/quiz/quiz-player";
import { ScoreRing } from "@/components/quiz/quiz-results";
import { MasteryBadge } from "@/components/shared/mastery-badge";
import { Button } from "@/components/ui/button";
import { api, ApiError, type Me } from "@/lib/api";
import type { QuizSession } from "@/lib/quiz/types";
import { useCreateQuiz } from "@/lib/quiz/use-quiz";
import { cn } from "@/lib/utils";

type Level = "beginner" | "intermediate" | "advanced";

const LEVELS: { id: Level; title: string; blurb: string }[] = [
  { id: "beginner", title: "Beginner", blurb: "New to DSA. Start from the foundations." },
  { id: "intermediate", title: "Intermediate", blurb: "Comfortable with arrays and recursion." },
  { id: "advanced", title: "Advanced", blurb: "Know the classics, want depth and gaps filled." },
];

function DiagnosticStep({
  busy,
  error,
  onBack,
  onDone,
}: {
  busy: boolean;
  error: Error | null;
  onBack: () => void;
  onDone: () => void;
}) {
  const create = useCreateQuiz();
  const [session, setSession] = useState<QuizSession | null>(null);
  const [result, setResult] = useState<QuizSession | null>(null);

  if (result) {
    const max = result.max_score ?? result.questions.length;
    const ratio = max ? (result.score ?? 0) / max : 0;
    return (
      <section className="space-y-4 rounded-2xl border border-border bg-surface p-6">
        <div className="flex items-center gap-4">
          <ScoreRing ratio={ratio} label={`Diagnostic score ${Math.round(ratio * 100)} percent`} />
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">Your starting point</h1>
            <p className="text-sm text-muted">
              Cognexa now knows where you stand on {result.per_concept.length} concepts across the
              syllabus, and will start from there.
            </p>
          </div>
        </div>
        <ul className="grid gap-1.5 sm:grid-cols-2">
          {result.per_concept.map((c) => (
            <li key={c.concept_id} className="flex items-center justify-between gap-2 text-sm">
              <span className="truncate">{c.name}</span>
              <MasteryBadge value={c.max ? c.score / c.max : 0} showValue={false} />
            </li>
          ))}
        </ul>
        {error && (
          <FormMessage tone="error">
            {error instanceof ApiError ? error.message : "Something went wrong."}
          </FormMessage>
        )}
        <Button className="h-9" disabled={busy} onClick={onDone}>
          {busy && <Loader2 aria-hidden className="animate-spin" />}
          {busy ? "Saving…" : "Go to my dashboard"}
        </Button>
      </section>
    );
  }

  if (session) {
    return <QuizPlayer session={session} onFinished={setResult} />;
  }

  return (
    <section className="space-y-4 rounded-2xl border border-border bg-surface p-6">
      <h1 className="text-2xl font-semibold tracking-tight">Diagnostic quiz</h1>
      <p className="text-muted">
        10 short questions across the syllabus, about 5 minutes. There is no pass mark: your answers
        set your starting mastery so the tutor and Smart quizzes begin at the right level.
      </p>
      {(error || create.error) && (
        <FormMessage tone="error">
          {(error ?? create.error) instanceof ApiError
            ? (error ?? create.error)!.message
            : "Something went wrong."}
        </FormMessage>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant="ghost" className="h-9" onClick={onBack}>
          Back
        </Button>
        <Button
          className="h-9"
          disabled={create.isPending}
          onClick={() => create.mutate({ mode: "diagnostic" }, { onSuccess: setSession })}
        >
          {create.isPending && <Loader2 aria-hidden className="animate-spin" />}
          Start the diagnostic <ArrowRight aria-hidden />
        </Button>
        <Button variant="outline" className="h-9" disabled={busy} onClick={onDone}>
          Skip for now
        </Button>
      </div>
    </section>
  );
}

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
            prerequisite you are missing, not just the topic you named. One question about your
            level and a short diagnostic, and you are in.
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
        <DiagnosticStep
          busy={finish.isPending}
          error={finish.error}
          onBack={() => setStep(1)}
          onDone={() => finish.mutate()}
        />
      )}
    </div>
  );
}
