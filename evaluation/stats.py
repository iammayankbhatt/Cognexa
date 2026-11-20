"""Paired statistics in pure Python (no scipy needed, so the unit tests run in CI).

- Wilcoxon signed-rank test (two-sided, normal approximation with tie and zero handling as in
  the "wilcox" zero method: zero differences are dropped), with the matched-pairs rank-biserial
  correlation as effect size.
- Percentile bootstrap 95 % CI of the mean paired difference (seeded, reproducible).
scipy is used only in a cross-check test when the optional `eval` group is installed.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PairedResult:
    n: int  # pairs with a non-zero difference
    mean_a: float
    mean_b: float
    mean_diff: float  # mean of (b - a) over all pairs
    w_plus: float
    w_minus: float
    z: float
    p_value: float
    rank_biserial: float  # (W+ - W-) / (W+ + W-), in [-1, 1]
    ci_low: float
    ci_high: float


def _ranks(values: Sequence[float]) -> list[float]:
    """Average ranks (1-based) with ties sharing the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def wilcoxon(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float, float, int]:
    """Returns (W+, W-, z, two-sided p, n_nonzero) for differences b - a."""
    if len(a) != len(b):
        raise ValueError("paired samples must have the same length")
    diffs = [y - x for x, y in zip(a, b, strict=True) if y != x]
    n = len(diffs)
    if n == 0:
        return 0.0, 0.0, 0.0, 1.0, 0
    ranks = _ranks([abs(d) for d in diffs])
    w_plus = sum(r for r, d in zip(ranks, diffs, strict=True) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, diffs, strict=True) if d < 0)
    mean_w = n * (n + 1) / 4
    # tie correction: subtract sum(t^3 - t)/48 for each group of tied |d|
    ties: dict[float, int] = {}
    for d in diffs:
        ties[abs(d)] = ties.get(abs(d), 0) + 1
    var_w = n * (n + 1) * (2 * n + 1) / 24 - sum(t**3 - t for t in ties.values()) / 48
    if var_w <= 0:
        return w_plus, w_minus, 0.0, 1.0, n
    z = (min(w_plus, w_minus) - mean_w) / math.sqrt(var_w)
    p = math.erfc(abs(z) / math.sqrt(2))
    return w_plus, w_minus, z, min(1.0, p), n


def bootstrap_ci(
    diffs: Sequence[float], iterations: int = 2000, alpha: float = 0.05, seed: int = 7
) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean of `diffs`."""
    if not diffs:
        return 0.0, 0.0
    rng = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(rng.choice(diffs) for _ in range(n)) / n for _ in range(iterations))
    lo = means[int(alpha / 2 * iterations)]
    hi = means[min(iterations - 1, int((1 - alpha / 2) * iterations))]
    return lo, hi


def paired(a: Sequence[float], b: Sequence[float], iterations: int = 2000) -> PairedResult:
    """Compare per-item scores of mode A (e.g. plain RAG) and mode B (GraphRAG)."""
    w_plus, w_minus, z, p, n = wilcoxon(a, b)
    diffs = [y - x for x, y in zip(a, b, strict=True)]
    total = w_plus + w_minus
    lo, hi = bootstrap_ci(diffs, iterations)
    return PairedResult(
        n=n,
        mean_a=sum(a) / len(a) if a else 0.0,
        mean_b=sum(b) / len(b) if b else 0.0,
        mean_diff=sum(diffs) / len(diffs) if diffs else 0.0,
        w_plus=w_plus,
        w_minus=w_minus,
        z=z,
        p_value=p,
        rank_biserial=(w_plus - w_minus) / total if total else 0.0,
        ci_low=lo,
        ci_high=hi,
    )
