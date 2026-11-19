export type MasteryLevel = "low" | "mid" | "high";

/** Mastery is a 0..1 score. Thresholds match the adaptive quiz bands (<0.4, 0.4-0.75, >0.75). */
export const MASTERY_LOW_MAX = 0.4;
export const MASTERY_MID_MAX = 0.75;

export function masteryLevel(value: number): MasteryLevel {
  if (value < MASTERY_LOW_MAX) return "low";
  if (value < MASTERY_MID_MAX) return "mid";
  return "high";
}
