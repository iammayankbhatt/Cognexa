"""Evaluation metrics and statistics with hand-computed fixtures (pure Python, runs in CI)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation import metrics, stats  # noqa: E402


def rec(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "item_id": "x", "category": "unnamed_prerequisite", "mode": "graphrag",
        "gold_concepts": ["recursion"], "gold_prerequisites": ["call_stack"],
        "contexts": [], "matched": [], "is_on_topic": True, "latency_ms": 100,
        "tokens_in": 10, "tokens_out": 5,
    }  # fmt: skip
    base.update(kw)
    return base


def ctx(*ids: str) -> list[dict[str, str]]:
    return [{"concept_id": i, "kind": "overview", "text": "t"} for i in ids]


def test_prerequisite_hit_rate() -> None:
    assert metrics.prerequisite_hit(rec(contexts=ctx("recursion", "call_stack"))) == 1.0
    assert metrics.prerequisite_hit(rec(contexts=ctx("recursion"))) == 0.0
    both = rec(gold_prerequisites=["call_stack", "functions"], contexts=ctx("call_stack"))
    assert metrics.prerequisite_hit(both) == 0.0  # every gold prerequisite is required
    assert metrics.prerequisite_hit(rec(gold_prerequisites=[])) is None
    records = [
        rec(contexts=ctx("call_stack")),
        rec(contexts=ctx("recursion")),
        rec(contexts=ctx("call_stack", "x")),
        rec(gold_prerequisites=[]),
    ]
    assert metrics.summarise(records)["prerequisite_hit_rate"] == pytest.approx(2 / 3)


def test_concept_accuracy_at_k_and_off_topic() -> None:
    r = rec(matched=["call_stack", "recursion"])
    assert metrics.concept_hit_at_k(r, 1) == 0.0 and metrics.concept_hit_at_k(r, 3) == 1.0
    plain = rec(mode="plain_rag", contexts=ctx("stack", "stack", "recursion"))
    assert metrics.concept_hit_at_k(plain, 1) == 0.0 and metrics.concept_hit_at_k(plain, 2) == 1.0
    off = rec(category="off_topic", gold_concepts=[], is_on_topic=False)
    assert metrics.off_topic_correct(off) == 1.0
    assert metrics.off_topic_correct(rec(category="off_topic", contexts=ctx("a"))) == 0.0
    assert metrics.off_topic_correct(rec()) is None


def test_summary_tables_by_mode_and_category() -> None:
    records = [
        rec(
            mode="graphrag", contexts=ctx("call_stack"), latency_ms=200, tokens_in=30, tokens_out=10
        ),
        rec(mode="plain_rag", contexts=ctx("recursion"), latency_ms=100),
        rec(mode="graphrag", category="direct", gold_prerequisites=[], matched=["recursion"]),
    ]
    t = metrics.by_mode_and_category(records)
    assert set(t) == {"graphrag", "plain_rag"}
    assert t["graphrag"]["unnamed_prerequisite"]["prerequisite_hit_rate"] == 1.0
    assert t["plain_rag"]["all"]["prerequisite_hit_rate"] == 0.0
    assert t["graphrag"]["all"]["avg_latency_ms"] == 150
    assert t["graphrag"]["all"]["avg_tokens"] == pytest.approx((40 + 15) / 2)
    assert t["plain_rag"]["direct"]["n"] == 0


def test_normalized_gain() -> None:
    assert metrics.normalized_gain(8, 14, 20) == 0.5  # (14 - 8) / (20 - 8)
    assert metrics.normalized_gain(10, 8, 20) == -0.2
    assert metrics.normalized_gain(20, 20, 20) is None


def test_wilcoxon_hand_computed() -> None:
    # differences b - a: [1, 2, -1, 3, 0] -> zero dropped; |d| ranks: 1 -> 1.5, 1 -> 1.5, 2 -> 3, 3 -> 4
    a = [0, 0, 1, 0, 2]
    b = [1, 2, 0, 3, 2]
    w_plus, w_minus, z, p, n = stats.wilcoxon(a, b)
    assert (w_plus, w_minus, n) == (8.5, 1.5, 4)
    # var = 4*5*9/24 - (2^3 - 2)/48 = 7.5 - 0.125; z = (1.5 - 5) / sqrt(7.375)
    assert z == pytest.approx((1.5 - 5) / 7.375**0.5)
    assert 0 < p < 1
    assert stats.wilcoxon([1, 2], [1, 2])[3] == 1.0
    with pytest.raises(ValueError):
        stats.wilcoxon([1], [1, 2])


def test_paired_effect_size_and_bootstrap() -> None:
    a = [0.0] * 10
    b = [1.0] * 8 + [0.0] * 2
    r = stats.paired(a, b, iterations=500)
    assert r.rank_biserial == 1.0 and r.mean_diff == 0.8
    assert 0.5 <= r.ci_low <= 0.8 <= r.ci_high <= 1.0
    assert r.p_value < 0.05
    assert stats.bootstrap_ci([]) == (0.0, 0.0)


@pytest.mark.skipif(
    importlib.util.find_spec("scipy") is None, reason="needs the optional eval group"
)
def test_wilcoxon_matches_scipy() -> None:
    from scipy.stats import wilcoxon as sp_wilcoxon

    a = [0.1, 0.4, 0.35, 0.8, 0.5, 0.2, 0.9, 0.3, 0.6, 0.45, 0.7, 0.25]
    b = [0.3, 0.5, 0.30, 0.9, 0.7, 0.4, 0.95, 0.2, 0.8, 0.65, 0.75, 0.5]
    ours = stats.wilcoxon(a, b)
    ref = sp_wilcoxon(b, a, zero_method="wilcox", correction=False, method="approx")
    assert ours[3] == pytest.approx(ref.pvalue, rel=1e-6)


def test_study_notebook_is_valid_and_its_code_parses() -> None:
    import ast
    import json

    nb = json.loads((REPO / "evaluation" / "study_analysis.ipynb").read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 6
    for cell in code:
        ast.parse("".join(cell["source"]))
    text = json.dumps(nb)
    for needle in ("ttest_ind", "mannwhitneyu", "Cohen", "n_per_group", "normalized_gain"):
        assert needle in text
