import { ApiError } from "@/lib/api";

export interface FriendlyError {
  title: string;
  description: string;
}

/** "in 45 s", "in 12 min", "in 2 h 5 min". */
export function formatWait(seconds: number): string {
  const s = Math.max(1, Math.ceil(seconds));
  if (s < 60) return `in ${s} s`;
  const minutes = Math.ceil(s / 60);
  if (minutes < 60) return `in ${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `in ${h} h ${m} min` : `in ${h} h`;
}

/** Local clock time of an ISO timestamp, e.g. "05:30". */
export function formatClock(iso: string, locale?: string): string {
  return new Date(iso).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" });
}

function resetText(err: ApiError, now: Date): string {
  const resetAt = typeof err.details?.reset_at === "string" ? err.details.reset_at : null;
  if (!resetAt) return "";
  const wait = (new Date(resetAt).getTime() - now.getTime()) / 1000;
  return ` It resets ${formatWait(wait)} (at ${formatClock(resetAt)}).`;
}

/**
 * Plain-language messages for errors a student can hit while using AI features. The backend's
 * message is the fallback, so new error codes still read sensibly.
 */
export function friendlyError(err: unknown, now: Date = new Date()): FriendlyError {
  if (!(err instanceof ApiError)) {
    return { title: "Something went wrong", description: "Please try again in a moment." };
  }
  switch (err.code) {
    case "QUOTA_EXCEEDED":
      return {
        title: "Daily AI limit reached",
        description: `You have used all of today's AI requests.${resetText(err, now)} Review mode and your notes still work.`,
      };
    case "RATE_LIMITED":
      return {
        title: "Slow down a little",
        description: `You are sending requests faster than the per-minute limit.${resetText(err, now)}`,
      };
    case "GLOBAL_CAP":
      return {
        title: "Cognexa is resting",
        description: `The AI tutor has reached today's limit for everyone.${resetText(err, now)} Quizzes and review still work.`,
      };
    case "INPUT_TOO_LONG":
      return { title: "That message is too long", description: err.message };
    case "llm_unavailable":
      return {
        title: "The AI model is unavailable",
        description:
          "Both AI providers failed to answer. You were not charged for this request; try again shortly.",
      };
    case "network_error":
      return { title: "You seem to be offline", description: err.message };
    default:
      return { title: "Something went wrong", description: err.message };
  }
}
