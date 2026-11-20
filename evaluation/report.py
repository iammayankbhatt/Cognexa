"""Evaluation report: Markdown tables by mode and category, paired statistics, PNG charts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation import metrics, stats

HEADLINE = "unnamed_prerequisite"
PAIRED_METRICS = {
    "prerequisite_hit": metrics.prerequisite_hit,
    "concept_hit_at_3": lambda r: metrics.concept_hit_at_k(r, 3),
}
TABLE_COLUMNS = [
    ("n", "n"),
    ("prerequisite_hit_rate", "Prereq hit"),
    ("concept_accuracy@1", "Concept@1"),
    ("concept_accuracy@3", "Concept@3"),
    ("off_topic_decline_accuracy", "Off-topic decline"),
    ("faithfulness", "Faithfulness"),
    ("answer_relevancy", "Answer rel."),
    ("context_precision", "Ctx precision"),
    ("context_recall", "Ctx recall"),
    ("avg_latency_ms", "Latency ms"),
    ("avg_tokens", "Tokens"),
]


def fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.0f}" if v >= 10 else f"{v:.2f}"
    return str(v)


def paired_rows(records: list[dict[str, Any]], category: str | None) -> list[dict[str, Any]]:
    """Per metric: GraphRAG vs plain RAG on the same items (Wilcoxon, rank-biserial, bootstrap)."""
    by_item: dict[str, dict[str, dict[str, Any]]] = {}
    for r in records:
        if category is None or r["category"] == category:
            by_item.setdefault(r["item_id"], {})[r["mode"]] = r
    rows = []
    metric_fns = dict(PAIRED_METRICS)
    for name in ("faithfulness", "answer_relevancy", "context_precision", "context_recall"):
        metric_fns[name] = lambda r, n=name: (r.get("ragas") or {}).get(n)
    for name, fn in metric_fns.items():
        a, b = [], []
        for pair in by_item.values():
            if "graphrag" in pair and "plain_rag" in pair:
                va, vb = fn(pair["plain_rag"]), fn(pair["graphrag"])
                if va is not None and vb is not None:
                    a.append(float(va))
                    b.append(float(vb))
        if len(a) < 2:
            continue
        res = stats.paired(a, b)
        rows.append({"metric": name, "pairs": len(a), **res.__dict__})
    return rows


def charts(run_dir: Path, table: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    files = []
    cats = [c for c in next(iter(table.values())) if c != "all"]
    for key, label in (
        ("prerequisite_hit_rate", "Prerequisite hit rate"),
        ("concept_accuracy@3", "Concept accuracy@3"),
    ):
        fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
        width = 0.38
        xs = range(len(cats))
        for i, (mode, color) in enumerate((("plain_rag", "#7a8597"), ("graphrag", "#7c3aed"))):
            if mode not in table:
                continue
            vals = [table[mode][c].get(key) or 0 for c in cats]
            ax.bar([x + (i - 0.5) * width for x in xs], vals, width, label=mode, color=color)
        ax.set_xticks(list(xs), [c.replace("_", " ") for c in cats], fontsize=8)
        ax.set_ylim(0, 1)
        ax.set_ylabel(label)
        ax.legend(frameon=False, fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        fig.tight_layout()
        name = f"{key.replace('@', '_at_')}.png"
        fig.savefig(run_dir / name)
        plt.close(fig)
        files.append(name)
    return files


def write_report(
    run_dir: Path, records: list[dict[str, Any]], meta: dict[str, Any]
) -> dict[str, Any]:
    table = metrics.by_mode_and_category(records)
    headline_pairs = paired_rows(records, HEADLINE)
    overall_pairs = paired_rows(records, None)
    pngs = charts(run_dir, table) if table else []
    lines = [
        f"# Evaluation run `{meta['run_id']}`",
        "",
        f"Generated {meta['generated']} by `evaluation/ragas_eval.py`.",
        "",
        f"- Retrieval source: {meta['source']}",
        f"- Answer model: {meta['providers']}; embeddings: {meta['embeddings']}",
        f"- Items: {meta['items']} (each through GraphRAG and plain RAG, "
        "response cache off, agentic step off)",
        f"- RAGAs: {meta['ragas']}",
        "",
    ]
    if meta.get("fake"):
        lines += [
            "> **Fake mode.** The answer model is the offline FakeProvider, so answer-quality "
            "numbers "
            "are not meaningful; retrieval metrics (prerequisite hit rate, concept accuracy) are. "
            "Re-run with real keys for the report's final numbers (Human Action Needed).",
            "",
        ]
    lines += [f"## Headline: `{HEADLINE}` items", ""]
    lines += _table({m: {HEADLINE: table[m].get(HEADLINE, {})} for m in table}, [HEADLINE])
    if headline_pairs:
        lines += ["", "Paired comparison on the same items (GraphRAG minus plain RAG):", ""]
        lines += _pairs(headline_pairs)
    lines += ["", "## All items by mode", ""]
    lines += _table({m: {"all": table[m]["all"]} for m in table}, ["all"])
    if overall_pairs:
        lines += ["", "Paired comparison, all items:", ""]
        lines += _pairs(overall_pairs)
    cats = sorted({r["category"] for r in records})
    lines += ["", "## By category", ""]
    lines += _table(table, cats)
    for png in pngs:
        lines += ["", f"![{png}]({png})"]
    lines += [
        "",
        "## How to read this",
        "",
        "- **Prereq hit** = share of items whose retrieved context contains at least one chunk "
        "from every gold prerequisite (the project's central claim; only items with gold "
        "prerequisites).",
        "- **Concept@k** = a gold concept is among the first k classified concepts (GraphRAG) "
        "or the "
        "concepts of the first k chunks (plain RAG).",
        "- Wilcoxon signed-rank (two-sided, normal approximation), effect size = matched-pairs "
        "rank-biserial r, 95 % CI = percentile bootstrap of the mean paired difference.",
        "- The numbers are reported as they came out; nothing is filtered.",
    ]
    (run_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    summary = {
        "table": table,
        "headline_pairs": headline_pairs,
        "overall_pairs": overall_pairs,
        "meta": meta,
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    return summary


def _table(table: dict[str, dict[str, dict[str, Any]]], cats: list[str]) -> list[str]:
    cols = [
        c
        for c in TABLE_COLUMNS
        if any(table[m].get(cat, {}).get(c[0]) is not None for m in table for cat in cats)
    ]
    header = "| Category | Mode | " + " | ".join(label for _, label in cols) + " |"
    sep = "|---|---|" + "---|" * len(cols)
    rows = [header, sep]
    for cat in cats:
        for mode in sorted(table):
            s = table[mode].get(cat, {})
            if not s.get("n"):
                continue
            rows.append(f"| {cat} | {mode} | " + " | ".join(fmt(s.get(k)) for k, _ in cols) + " |")
    return rows


def _pairs(rows: list[dict[str, Any]]) -> list[str]:
    out = [
        "| Metric | Pairs | Plain RAG | GraphRAG | Δ mean | 95 % CI | Wilcoxon p "
        "| Rank-biserial r |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| {r['metric']} | {r['pairs']} | {r['mean_a']:.2f} | {r['mean_b']:.2f} | "
            f"{r['mean_diff']:+.2f} | [{r['ci_low']:+.2f}, {r['ci_high']:+.2f}] | "
            f"{r['p_value']:.3g} | {r['rank_biserial']:+.2f} |"
        )
    return out
