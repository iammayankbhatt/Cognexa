"""Phase 6 smoke run: 10 eval test-set questions through GraphRAG and plain RAG.

Writes evaluation/reports/phase6_smoke.md with each answer and its retrieval trace, plus a summary
of how often each mode put the gold concepts and gold prerequisites into the context.

Uses the configured providers (apps/api/.env): with LLM_PRIMARY_PROVIDER=fake the answers are the
deterministic fake ones, so the report checks retrieval only. Run it again after adding real keys
(Human Action Needed) to review real answers.

    uv run --project apps/api python scripts/phase6_smoke.py               # Neo4j + pgvector (dev)
    uv run --project apps/api python scripts/phase6_smoke.py --offline     # in-memory, no services

This is an offline developer tool: it calls models directly through the router without the
per-user usage guard (it is never deployed). It never writes to the databases.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.db.session import Database
from app.graph.driver import create_driver
from app.graph.memory import InMemoryGraph
from app.graph.repository import GraphRepository
from app.llm.embeddings import get_embedding_provider
from app.llm.registry import build_router
from app.tutor.catalogue import CatalogueCache
from app.tutor.pipeline import DoneEvent, TurnInput, TutorPipeline
from app.tutor.plain_rag import InMemoryVectorSearch, PgVectorSearch
from app.tutor.trace import RetrievalTrace

REPO = Path(__file__).resolve().parents[1]
TESTSET = REPO / "data" / "subjects" / "dsa" / "eval" / "testset.jsonl"
OUT = REPO / "evaluation" / "reports" / "phase6_smoke.md"
# How many items of each category to take (first ones in file order): 10 in total.
PICK = {"direct": 2, "unnamed_prerequisite": 4, "multi_concept": 2, "misconception": 1,
        "off_topic": 1}  # fmt: skip
ANSWER_CHARS = 900


def pick_items(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    left = dict(PICK)
    out = []
    for r in rows:
        if left.get(r["category"], 0) > 0:
            out.append(r)
            left[r["category"]] -= 1
    return out


def context_concepts(trace: RetrievalTrace) -> list[str]:
    return list(dict.fromkeys(c.concept_id for c in trace.chunks))


def coverage(wanted: list[str], got: list[str]) -> str:
    if not wanted:
        return "n/a"
    hit = [w for w in wanted if w in got]
    return f"{len(hit)}/{len(wanted)}"


def fmt_trace(t: RetrievalTrace) -> list[str]:
    lines = [f"- mode: `{t.mode}`, intent: `{t.intent}`, on topic: {t.is_on_topic}"]
    if t.mode == "graphrag":
        lines.append(f"- classification path: `{t.classification_path}`")
        lines.append(
            "- matched: "
            + (", ".join(f"`{m.id}` ({m.confidence:.2f}, {m.source})" for m in t.matched) or "none")
        )
        pre = [c for c in t.concepts if c.role == "prerequisite"]
        if pre:
            lines.append(
                "- prerequisites: "
                + ", ".join(
                    f"`{c.id}` (d{c.depth}{', weak' if c.weak else ''}; "
                    + " → ".join([e.source for e in c.path] + [c.path[-1].target])
                    + ")"
                    for c in pre
                    if c.path
                )
            )
        rel = [c.id for c in t.concepts if c.role == "related"]
        if rel:
            lines.append("- related: " + ", ".join(f"`{r}`" for r in rel))
        if t.controller:
            lines.append(
                "- controller: " + " → ".join(f"{s.action} ({s.reason})" for s in t.controller)
            )
    chunks = ", ".join(
        f"`{c.concept_id}/{c.kind}`" + (f" {c.score:.2f}" if c.score is not None else "")
        for c in t.chunks
    )
    lines.append(f"- context ({t.used_tokens}/{t.budget_tokens} tokens): {chunks or 'none'}")
    if t.citations:
        lines.append("- citations: " + ", ".join(f"`{c}`" for c in t.citations))
    lines.append("- timings (ms): " + ", ".join(f"{k} {v}" for k, v in t.timings_ms.items()))
    return lines


async def run(offline: bool, out: Path) -> int:
    settings = Settings()
    rows = [json.loads(line) for line in TESTSET.read_text(encoding="utf-8").splitlines() if line]
    items = pick_items(rows)
    llm = build_router(settings)
    embedder = get_embedding_provider(settings)
    driver = None
    db = None
    if offline:
        mem = InMemoryGraph.from_subject("dsa")
        graph: Any = mem
        chunks = [c for cs in mem.chunks.values() for c in cs]
        names = {c.id: c.name for c in mem.concepts.values()}
        vectors: Any = InMemoryVectorSearch(chunks, embedder, names)
        source = "in-memory graph from concepts.yaml + notes; in-memory vector search"
    else:
        driver = create_driver(settings)
        graph = GraphRepository(driver)
        db = Database(settings)
        vectors = PgVectorSearch(db)
        source = "Neo4j (NEO4J_URI) + pgvector (DATABASE_URL)"
    pipeline = TutorPipeline(
        graph=graph,
        llm=llm,
        embedder=embedder,
        vectors=vectors,
        catalogues=CatalogueCache(),
        classify_threshold=settings.classify_threshold,
        context_budget=settings.context_token_budget,
        plain_top_k=settings.plain_rag_top_k,
    )
    providers = ", ".join(f"{p.name}:{p.model}" for p in llm.providers)
    report = [
        "# Phase 6 smoke run: GraphRAG vs plain RAG",
        "",
        f"Generated {dt.datetime.now(dt.UTC):%Y-%m-%d %H:%M} UTC by `scripts/phase6_smoke.py`.",
        "",
        f"- LLM providers: {providers}",
        f"- Embeddings: {embedder.model} (dim {embedder.dim})",
        f"- Retrieval source: {source}",
        f"- Budget {settings.context_token_budget} tokens, plain RAG top-k "
        f"{settings.plain_rag_top_k}, classify threshold {settings.classify_threshold}",
        "- Personalisation: none (a new student: every prerequisite counts as weak). "
        "Agentic controller: on.",
        "",
    ]
    if any(p.name == "fake" for p in llm.providers):
        report += [
            "> **Fake mode.** Answers are the deterministic FakeProvider ones (assembled from the "
            "retrieved chunks), so only the retrieval columns are meaningful. Re-run with real "
            "keys to review real answers (Human Action Needed in progressfile.md).",
            "",
        ]
    summary = [
        "| id | category | gold concepts | gold prerequisites | GraphRAG concepts | "
        "GraphRAG prereqs | plain concepts | plain prereqs |",
        "|---|---|---|---|---|---|---|---|",
    ]
    details: list[str] = []
    totals = {"g_pre": [0, 0], "p_pre": [0, 0], "g_con": [0, 0], "p_con": [0, 0]}
    try:
        for item in items:
            results: dict[str, tuple[RetrievalTrace, str]] = {}
            for mode in ("graphrag", "plain_rag"):
                turn = TurnInput(question=item["question"], mode=mode, use_cache=False)
                done: DoneEvent | None = None
                async for event in pipeline.run(turn):
                    if isinstance(event, DoneEvent):
                        done = event
                assert done is not None
                results[mode] = (done.trace, done.content)
            g, p = results["graphrag"][0], results["plain_rag"][0]
            gc, pc = context_concepts(g), context_concepts(p)
            gold, pre = item["gold_concepts"], item["gold_prerequisites"]
            for key, wanted, got in (("g_con", gold, gc), ("p_con", gold, pc),
                                     ("g_pre", pre, gc), ("p_pre", pre, pc)):  # fmt: skip
                totals[key][0] += sum(1 for w in wanted if w in got)
                totals[key][1] += len(wanted)
            summary.append(
                f"| {item['id']} | {item['category']} | {', '.join(gold) or '-'} | "
                f"{', '.join(pre) or '-'} | {coverage(gold, gc)} | {coverage(pre, gc)} | "
                f"{coverage(gold, pc)} | {coverage(pre, pc)} |"
            )
            details += ["", f"## {item['id']} ({item['category']})", "", f"> {item['question']}", ""]
            for mode in ("graphrag", "plain_rag"):
                trace, content = results[mode]
                text = content if len(content) <= ANSWER_CHARS else content[:ANSWER_CHARS] + " …"
                details += [f"### {mode}", "", *fmt_trace(trace), "", "Answer:", "", "```text",
                            text, "```", ""]  # fmt: skip
            print(f"{item['id']}: graphrag prereqs {coverage(pre, gc)}, plain {coverage(pre, pc)}")
    finally:
        if driver is not None:
            await driver.close()
        if db is not None:
            await db.dispose()
        for provider in llm.providers:
            await provider.aclose()

    def pct(key: str) -> str:
        hit, total = totals[key]
        return f"{hit}/{total}" + (f" ({100 * hit / total:.0f}%)" if total else "")

    report += [
        "## Summary",
        "",
        "Coverage = gold ids that appear among the concepts of the chunks put in the context.",
        "",
        *summary,
        "",
        f"- Gold concepts in context: GraphRAG {pct('g_con')}, plain RAG {pct('p_con')}",
        f"- Gold prerequisites in context: GraphRAG {pct('g_pre')}, plain RAG {pct('p_pre')}",
        "",
        "Review notes (fill in together): are the matched concepts right? Did the answer connect "
        "the weak prerequisite? Any hallucinated content outside the context?",
        "",
        "# Details",
        *details,
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out.relative_to(REPO) if out.resolve().is_relative_to(REPO) else out}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true", help="in-memory graph and vectors")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    return asyncio.run(run(args.offline, args.out))


if __name__ == "__main__":
    sys.exit(main())
