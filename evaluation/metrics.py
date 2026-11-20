"""Custom evaluation metrics (the project's central claim) and the user-study gain formula.

Pure functions over plain dicts so they can be unit-tested with hand-computed fixtures.
An evaluation record (one row of raw.jsonl) looks like:
    {"item_id", "category", "mode", "question", "gold_concepts", "gold_prerequisites",
     "answer", "contexts": [{"concept_id", "kind", "text"}], "matched": [concept ids],
     "is_on_topic": bool, "latency_ms": int, "tokens_in": int, "tokens_out": int}
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

Record = Mapping[str, Any]


def context_concepts(record: Record) -> set[str]:
    return {str(c["concept_id"]) for c in record.get("contexts") or []}


def prerequisite_hit(record: Record) -> float | None:
    """1.0 when the retrieved contexts include at least one chunk from EVERY gold prerequisite,
    0.0 otherwise; None when the item has no gold prerequisites (not applicable)."""
    gold = record.get("gold_prerequisites") or []
    if not gold:
        return None
    got = context_concepts(record)
    return 1.0 if all(g in got for g in gold) else 0.0


def concept_hit_at_k(record: Record, k: int) -> float | None:
    """1.0 when any gold concept is among the first k classified concepts (graphrag) or, for a
    mode without classification, among the concepts of the first k context chunks."""
    gold = record.get("gold_concepts") or []
    if not gold:
        return None
    ranked = list(record.get("matched") or [])
    if not ranked:
        ranked = list(dict.fromkeys(str(c["concept_id"]) for c in record.get("contexts") or []))
    return 1.0 if any(g in ranked[:k] for g in gold) else 0.0


def off_topic_correct(record: Record) -> float | None:
    """For off-topic items: 1.0 when the system declined (no context, not on topic)."""
    if record.get("category") != "off_topic":
        return None
    declined = record.get("is_on_topic") is False or not record.get("contexts")
    return 1.0 if declined else 0.0


def mean(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def summarise(records: Sequence[Record], ks: Sequence[int] = (1, 3)) -> dict[str, Any]:
    """Aggregate metrics for one group of records (one mode, optionally one category)."""
    out: dict[str, Any] = {
        "n": len(records),
        "prerequisite_hit_rate": mean(prerequisite_hit(r) for r in records),
        "off_topic_decline_accuracy": mean(off_topic_correct(r) for r in records),
        "avg_latency_ms": mean(float(r.get("latency_ms") or 0) for r in records),
        "avg_tokens": mean(
            float((r.get("tokens_in") or 0) + (r.get("tokens_out") or 0)) for r in records
        ),
    }
    for k in ks:
        out[f"concept_accuracy@{k}"] = mean(concept_hit_at_k(r, k) for r in records)
    for name in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
        vals = [r.get("ragas", {}).get(name) for r in records]
        if any(v is not None for v in vals):
            out[name] = mean(vals)
    return out


def by_mode_and_category(records: Sequence[Record]) -> dict[str, dict[str, dict[str, Any]]]:
    """{mode: {"all" | category: summary}}."""
    modes = sorted({str(r["mode"]) for r in records})
    cats = sorted({str(r["category"]) for r in records})
    table: dict[str, dict[str, dict[str, Any]]] = {}
    for m in modes:
        rows = [r for r in records if r["mode"] == m]
        table[m] = {"all": summarise(rows)}
        for c in cats:
            table[m][c] = summarise([r for r in rows if r["category"] == c])
    return table


def normalized_gain(pre: float, post: float, maximum: float) -> float | None:
    """Hake's normalized gain g = (post - pre) / (max - pre); None when pre is already max."""
    if maximum <= pre:
        return None
    return (post - pre) / (maximum - pre)
