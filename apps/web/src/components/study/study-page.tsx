"use client";

import { ClipboardList, FlaskConical, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { EmptyState } from "@/components/shared/empty-state";
import { ErrorState } from "@/components/shared/error-state";
import { PageHeader } from "@/components/shared/page-header";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useCreateQuiz } from "@/lib/quiz/use-quiz";
import { stepText, useStudy, useStudyActions, type StudyState } from "@/lib/study";
import { cn } from "@/lib/utils";

const STEPS: { step: StudyState["step"]; label: string }[] = [
  { step: "consent", label: "Consent" },
  { step: "pretest", label: "Pre-test" },
  { step: "learning", label: "Learning" },
  { step: "posttest", label: "Post-test" },
  { step: "complete", label: "Done" },
];

function Progress({ step }: { step: StudyState["step"] }) {
  const at = STEPS.findIndex((s) => s.step === step);
  return (
    <ol className="flex flex-wrap items-center gap-2 text-xs" aria-label="Study progress">
      {STEPS.map((s, i) => (
        <li
          key={s.step}
          aria-current={i === at ? "step" : undefined}
          className={cn(
            "rounded-full border px-2.5 py-1",
            i < at
              ? "border-success text-success"
              : i === at
                ? "border-accent text-text"
                : "border-border text-muted",
          )}
        >
          {s.label}
        </li>
      ))}
    </ol>
  );
}

function StartTest({ mode }: { mode: "pretest" | "posttest" }) {
  const router = useRouter();
  const create = useCreateQuiz();
  return (
    <Button
      size="lg"
      disabled={create.isPending}
      onClick={async () => {
        try {
          const s = await create.mutateAsync({ mode });
          router.push(`/app/quizzes/${s.id}`);
        } catch (err) {
          toast.error(err instanceof ApiError ? err.message : "Could not start the test.");
        }
      }}
    >
      <ClipboardList aria-hidden className="size-4" />
      {mode === "pretest" ? "Start the pre-test" : "Start the post-test"}
    </Button>
  );
}

/** The student's side of the user study: consent, tests, status, withdrawal. */
export function StudyPage() {
  const { data, isPending, error, refetch } = useStudy();
  const { consent, withdraw } = useStudyActions();
  if (isPending) return <Skeleton className="h-64 w-full" aria-label="Loading study" />;
  if (error || !data) return <ErrorState message={error?.message} onRetry={() => void refetch()} />;
  if (data.step === "off") {
    return (
      <div className="space-y-6">
        <PageHeader title="Study" />
        <EmptyState
          icon={<FlaskConical />}
          title="No study is running"
          description="When the team runs a study, you will be invited here."
        />
      </div>
    );
  }
  const text = stepText(data);
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader
        title="Cognexa study"
        description="Comparing two ways of recommending what to learn next."
      />
      {data.step !== "withdrawn" && <Progress step={data.step} />}

      {data.step === "consent" && (
        <section
          className="space-y-4 rounded-2xl border border-border bg-surface p-6"
          aria-labelledby="consent-title"
        >
          <h2 id="consent-title" className="flex items-center gap-2 text-lg font-semibold">
            <ShieldCheck aria-hidden className="size-5 text-accent" /> What taking part means
          </h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-text">
            <li>
              A 20-minute pre-test now, then use Cognexa as usual for about two weeks, then a
              20-minute post-test.
            </li>
            <li>
              You are placed in one of two groups at random. Both groups use the full app; only the
              &quot;next best step&quot; suggestions differ.
            </li>
            <li>
              We collect your test scores and counts of activity (quizzes taken, tutor questions,
              which suggestions you saw and followed, active days).
            </li>
            <li>
              The research export is anonymised: no name, no email, only a random participant code.
            </li>
            <li>You can withdraw at any time on this page; your data then leaves the study.</li>
          </ul>
          <div className="flex flex-wrap gap-2">
            <Button
              size="lg"
              disabled={consent.isPending}
              onClick={() =>
                consent.mutate(undefined, {
                  onError: (e) =>
                    toast.error(e instanceof ApiError ? e.message : "Could not join."),
                })
              }
            >
              I agree to take part
            </Button>
            <Link href="/app" className={buttonVariants({ variant: "outline", size: "lg" })}>
              Not now
            </Link>
          </div>
        </section>
      )}

      {data.step !== "consent" && data.step !== "withdrawn" && (
        <section className="space-y-3 rounded-2xl border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold">{text.title}</h2>
          <p className="text-sm text-muted">{text.body}</p>
          {data.step === "pretest" && <StartTest mode="pretest" />}
          {data.step === "posttest" && <StartTest mode="posttest" />}
          {data.pretest?.submitted && (
            <p className="text-sm text-muted">
              Pre-test: {data.pretest.score}/{data.pretest.max_score}
              {data.posttest?.submitted
                ? ` · Post-test: ${data.posttest.score}/${data.posttest.max_score}`
                : ""}
            </p>
          )}
        </section>
      )}

      {data.step === "withdrawn" ? (
        <EmptyState
          icon={<ShieldCheck />}
          title="You have left the study"
          description="Your data is no longer part of the study. Cognexa works as normal."
        />
      ) : (
        data.step !== "consent" && (
          <div className="border-t border-border pt-4">
            <Button
              variant="ghost"
              disabled={withdraw.isPending}
              onClick={() => {
                if (
                  window.confirm(
                    "Leave the study? Your data will be removed from the research export.",
                  )
                )
                  withdraw.mutate();
              }}
            >
              Withdraw from the study
            </Button>
          </div>
        )
      )}
    </div>
  );
}

/** A small card on the dashboard while the student has a study step to do. */
export function StudyBanner() {
  const { data } = useStudy();
  if (!data || ["off", "withdrawn", "complete"].includes(data.step)) return null;
  const text = stepText(data);
  return (
    <section
      aria-label="Study"
      className="flex flex-wrap items-center gap-3 rounded-2xl border border-accent/50 bg-surface-2 p-4"
    >
      <FlaskConical aria-hidden className="size-5 text-accent" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold">{text.title}</p>
        <p className="text-sm text-muted">{text.body}</p>
      </div>
      {data.step !== "learning" && (
        <Link href="/app/study" className={buttonVariants({ variant: "default" })}>
          {data.step === "consent" ? "Read more" : "Open"}
        </Link>
      )}
    </section>
  );
}
