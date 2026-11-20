export type MasteryLevel = "low" | "mid" | "high";

/** Mastery is a 0..1 score. Bands match the backend (app/mastery/model.py): < 0.4 weak,
 * 0.4 to 0.75 developing (inclusive), > 0.75 strong. */
export const MASTERY_LOW_MAX = 0.4;
export const MASTERY_MID_MAX = 0.75;

export function masteryLevel(value: number): MasteryLevel {
  if (value < MASTERY_LOW_MAX) return "low";
  if (value <= MASTERY_MID_MAX) return "mid"; // > 0.75 is strong, as in the backend bands
  return "high";
}
