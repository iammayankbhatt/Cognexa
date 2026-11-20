"""Rule-based mastery model (Report Objective 3; documented in docs/ARCHITECTURE.md).

For each graded answer on concept c (result in [0, 1], question difficulty d):
    w = {1: 0.8, 2: 1.0, 3: 1.2}[d]
    score_c <- clamp(score_c + 0.3 * w * (result - score_c), 0, 1)
If result < 0.5 and the question diagnoses prerequisite p: score_p <- max(0, score_p - 0.05).
Time decay is applied when mastery is read, never stored:
    effective = score * 0.98 ** (days since last practised / 7)
Bands: effective < 0.4 weak, 0.4 to 0.75 developing, > 0.75 strong.
All constants come from Settings (MASTERY_*).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

from app.core.config import Settings

Band = Literal["weak", "developing", "strong"]


@dataclass(frozen=True)
class MasteryParams:
    learning_rate: float = 0.3
    weights: tuple[float, float, float] = (0.8, 1.0, 1.2)
    prereq_penalty: float = 0.05
    decay_base: float = 0.98
    decay_period_days: float = 7.0
    weak_below: float = 0.4
    strong_above: float = 0.75

    @classmethod
    def from_settings(cls, s: Settings) -> MasteryParams:
        return cls(
            learning_rate=s.mastery_learning_rate,
            weights=(s.mastery_weight_easy, s.mastery_weight_medium, s.mastery_weight_hard),
            prereq_penalty=s.mastery_prereq_penalty,
            decay_base=s.mastery_decay_base,
            decay_period_days=s.mastery_decay_period_days,
            weak_below=s.mastery_weak_below,
            strong_above=s.mastery_strong_above,
        )


DEFAULT_PARAMS = MasteryParams()


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def weight(difficulty: int, p: MasteryParams = DEFAULT_PARAMS) -> float:
    return p.weights[max(1, min(3, int(difficulty))) - 1]


def updated_score(
    score: float, result: float, difficulty: int, p: MasteryParams = DEFAULT_PARAMS
) -> float:
    r = clamp(result)
    return round(clamp(score + p.learning_rate * weight(difficulty, p) * (r - score)), 3)


def penalised_prereq(score: float, p: MasteryParams = DEFAULT_PARAMS) -> float:
    return round(max(0.0, score - p.prereq_penalty), 3)


def effective_score(
    score: float,
    last_practiced_at: dt.datetime | None,
    now: dt.datetime,
    p: MasteryParams = DEFAULT_PARAMS,
) -> float:
    if last_practiced_at is None:
        return round(score, 3)
    days = max(0.0, (now - last_practiced_at).total_seconds() / 86_400)
    decayed: float = score * p.decay_base ** (days / p.decay_period_days)
    return round(decayed, 3)


def band(effective: float, p: MasteryParams = DEFAULT_PARAMS) -> Band:
    if effective < p.weak_below:
        return "weak"
    if effective > p.strong_above:
        return "strong"
    return "developing"


def target_difficulty(effective: float | None, p: MasteryParams = DEFAULT_PARAMS) -> int:
    """Adaptive quizzes: < 0.4 -> 1, 0.4 to 0.75 -> 2, > 0.75 -> 3 (never practised -> 1)."""
    if effective is None or effective < p.weak_below:
        return 1
    return 3 if effective > p.strong_above else 2
