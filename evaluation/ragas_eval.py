"""Run the 85-item evaluation test set through GraphRAG and plain RAG and write a report.

    uv run --project apps/api --group eval python evaluation/ragas_eval.py --offline
    uv run --project apps/api --group eval python evaluation/ragas_eval.py --run-id dev-real --push

- Calls the backend pipeline directly (same code as /tutor), response cache disabled, agentic
  step off (both modes answer directly, so the comparison isolates retrieval).
- --offline uses the in-memory graph and vector search from the source files; otherwise Neo4j
  (NEO4J_URI) and pgvector (DATABASE_URL) of the dev environment.
- Resumable: outputs append to evaluation/reports/<run_id>/raw.jsonl and finished (item, mode)
  pairs are skipped on the next run. On provider errors (429 / 5xx after the router's retries)
  it waits and retries, then records the error and moves on.
- RAGAs metrics run only when the judge model is real (LLM_JUDGE_PROVIDER is not "fake") or
  --ragas is given; custom metrics always run.
- --push stores the summary in eval_runs / eval_results of DATABASE_URL (dev only).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.core.config import Settings  # noqa: E402
from app.db.session import Database  # noqa: E402
from app.graph.driver import create_driver  # noqa: E402
from app.graph.memory import InMemoryGraph  # noqa: E402
from app.graph.repository import GraphRepository  # noqa: E402
from app.llm.embeddings import get_embedding_provider  # noqa: E402
from app.llm.errors import LLMError  # noqa: E402
from app.llm.registry import build_judge_router, build_router  # noqa: E402
from app.tutor.catalogue import CatalogueCache  # noqa: E402
from app.tutor.pipeline import DoneEvent, TurnInput, TutorPipeline  # noqa: E402
from app.tutor.plain_rag import InMemoryVectorSearch, PgVectorSearch  # noqa: E402
from evaluation.report import write_report  # noqa: E402

TESTSET = REPO / "data" / "subjects" / "dsa" / "eval" / "testset.jsonl"
REPORTS = REPO / "evaluation" / "reports"
MODES = ("graphrag", "plain_rag")
RETRIES = 3
RETRY_WAIT_S = 30.0


def load_items(
    limit: int | None, ids: list[str] | None, categories: list[str] | None
) -> list[dict[str, Any]]:
    items = [
        json.loads(line)
        for line in TESTSET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if ids:
        items = [i for i in items if i["id"] in ids]
    if categories:
        items = [i for i in items if i["category"] in categories]
    if limit:
        # spread a small run across categories instead of taking the first N items
        by_cat: dict[str, list[dict[str, Any]]] = {}
        for i in items:
            by_cat.setdefault(i["category"], []).append(i)
        picked: list[dict[str, Any]] = []
        while len(picked) < limit and any(by_cat.values()):
            for cat in sorted(by_cat):
                if by_cat[cat] and len(picked) < limit:
                    picked.append(by_cat[cat].pop(0))
        items = picked
    return items


def read_raw(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


async def chunk_texts_db(db: Database, ids: list[str]) -> dict[str, dict[str, str]]:
    from sqlalchemy import select

    from app.db.tables import content_chunks

    if not ids:
        return {}
    async with db.sessions()() as session:
        rows = await session.execute(
            select(
                content_chunks.c.id,
                content_chunks.c.concept_id,
                content_chunks.c.kind,
                content_chunks.c.text,
            ).where(content_chunks.c.id.in_(ids))
        )
        return {r.id: {"concept_id": r.concept_id, "kind": r.kind, "text": r.text} for r in rows}


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    llm = build_router(settings)
    judge = build_judge_router(settings)
    embedder = get_embedding_provider(settings)
    items = load_items(args.limit, args.ids, args.categories)
    run_id = args.run_id or dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    run_dir = REPORTS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "raw.jsonl"

    driver = None
    db: Database | None = None
    if args.offline:
        mem = InMemoryGraph.from_subject("dsa")
        graph: Any = mem
        all_chunks = {c.id: c for cs in mem.chunks.values() for c in cs}
        vectors: Any = InMemoryVectorSearch(
            list(all_chunks.values()), embedder, {c.id: c.name for c in mem.concepts.values()}
        )
        source = "offline (in-memory graph and vectors from the source files)"
    else:
        driver = create_driver(settings)
        graph = GraphRepository(driver)
        db = Database(settings)
        vectors = PgVectorSearch(db)
        all_chunks = {}
        source = "dev services (Neo4j + pgvector)"
    pipeline = TutorPipeline(
        graph=graph,
        llm=llm,
        embedder=embedder,
        vectors=vectors,
        catalogues=CatalogueCache(),
        cache=None,
        classify_threshold=settings.classify_threshold,
        context_budget=settings.context_token_budget,
        plain_top_k=settings.plain_rag_top_k,
    )

    done = {(r["item_id"], r["mode"]) for r in read_raw(raw_path) if "error" not in r}
    todo = [(i, m) for i in items for m in MODES if (i["id"], m) not in done]
    print(f"run {run_id}: {len(items)} items x {len(MODES)} modes, {len(todo)} to do ({source})")
    try:
        with raw_path.open("a", encoding="utf-8") as out:
            for n, (item, mode) in enumerate(todo, 1):
                record: dict[str, Any] = {
                    "item_id": item["id"],
                    "category": item["category"],
                    "mode": mode,
                    "question": item["question"],
                    "gold_concepts": item["gold_concepts"],
                    "gold_prerequisites": item["gold_prerequisites"],
                    "reference_answer": item.get("reference_answer", ""),
                }
                for attempt in range(1, RETRIES + 1):
                    turn = TurnInput(
                        question=item["question"], mode=mode, agentic=False, use_cache=False
                    )
                    started = time.monotonic()
                    try:
                        final: DoneEvent | None = None
                        async for event in pipeline.run(turn):
                            if isinstance(event, DoneEvent):
                                final = event
                        assert final is not None
                        break
                    except LLMError as e:
                        if attempt == RETRIES:
                            record["error"] = str(e)[:300]
                            final = None
                            break
                        print(f"  provider error ({e}); waiting {RETRY_WAIT_S:.0f} s")
                        await asyncio.sleep(RETRY_WAIT_S)
                if final is not None:
                    trace = final.trace
                    ids = [c.id for c in trace.chunks]
                    if all_chunks:
                        texts = {
                            i: {
                                "concept_id": all_chunks[i].concept_id,
                                "kind": all_chunks[i].kind,
                                "text": all_chunks[i].text,
                            }
                            for i in ids
                            if i in all_chunks
                        }
                    else:
                        assert db is not None
                        texts = await chunk_texts_db(db, ids)
                    record.update(
                        answer=final.content,
                        contexts=[{"id": i, **texts[i]} for i in ids if i in texts],
                        matched=[m.id for m in trace.matched],
                        is_on_topic=trace.is_on_topic,
                        classification_path=trace.classification_path,
                        latency_ms=int((time.monotonic() - started) * 1000),
                        tokens_in=sum(c.tokens_in for c in final.calls),
                        tokens_out=sum(c.tokens_out for c in final.calls),
                        trace=trace.model_dump(mode="json"),
                    )
                out.write(json.dumps(record) + "\n")
                out.flush()
                if n % 20 == 0 or n == len(todo):
                    print(f"  {n}/{len(todo)}")
        records = [r for r in read_raw(raw_path) if "error" not in r]
        # keep the latest record per (item, mode)
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for r in records:
            latest[(r["item_id"], r["mode"])] = r
        records = [latest[k] for k in sorted(latest)]

        judge_is_fake = all(p.name == "fake" for p in judge.providers)
        ragas_note = "not run: the judge is the offline fake model (set LLM_JUDGE_PROVIDER)"
        if args.ragas or (not judge_is_fake and not args.no_ragas):
            from evaluation.ragas_adapter import ragas_scores

            pending = [r for r in records if "ragas" not in r and r.get("answer")]
            for start in range(0, len(pending), 10):
                batch = pending[start : start + 10]
                for r, scores in zip(batch, ragas_scores(batch, judge, embedder), strict=True):
                    r["ragas"] = scores
            raw_path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
            ragas_note = "judge: " + ", ".join(f"{p.name}:{p.model}" for p in judge.providers)

        meta = {
            "run_id": run_id,
            "generated": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "source": source,
            "providers": ", ".join(f"{p.name}:{p.model}" for p in llm.providers),
            "embeddings": f"{embedder.model} (dim {embedder.dim})",
            "items": len({r["item_id"] for r in records}),
            "ragas": ragas_note,
            "fake": any(p.name == "fake" for p in llm.providers),
        }
        summary = write_report(run_dir, records, meta)
        print(f"wrote {run_dir.relative_to(REPO) / 'report.md'}")
        if args.push:
            await push(settings, run_id, meta, summary, records)
    finally:
        if driver is not None:
            await driver.close()
        if db is not None:
            await db.dispose()
        for p in [*llm.providers, *judge.providers]:
            await p.aclose()
    return 0


async def push(
    settings: Settings,
    run_id: str,
    meta: dict[str, Any],
    summary: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    """Store the run in eval_runs / eval_results (the admin evaluation page reads them)."""
    from urllib.parse import urlsplit

    from sqlalchemy import insert

    from app.db.tables import eval_results, eval_runs

    host = urlsplit(settings.database_url.replace("+asyncpg", "")).hostname or "?"
    print(f"pushing run to database on {host}")
    db = Database(settings)
    try:
        async with db.sessions()() as session, session.begin():
            run_row = (
                await session.execute(
                    insert(eval_runs)
                    .values(
                        name=run_id,
                        config=meta,
                        summary=summary,
                        finished_at=dt.datetime.now(dt.UTC),
                    )
                    .returning(eval_runs.c.id)
                )
            ).scalar_one()
            from evaluation import metrics

            for r in records:
                await session.execute(
                    insert(eval_results).values(
                        run_id=run_row,
                        item_id=r["item_id"],
                        mode=r["mode"],
                        question=r["question"],
                        answer=r.get("answer"),
                        contexts=r.get("contexts"),
                        metrics={
                            "category": r["category"],
                            "gold_concepts": r["gold_concepts"],
                            "gold_prerequisites": r["gold_prerequisites"],
                            "prerequisite_hit": metrics.prerequisite_hit(r),
                            "concept_hit_at_1": metrics.concept_hit_at_k(r, 1),
                            "concept_hit_at_3": metrics.concept_hit_at_k(r, 3),
                            "off_topic_correct": metrics.off_topic_correct(r),
                            "matched": r.get("matched"),
                            **(r.get("ragas") or {}),
                        },
                        latency_ms=r.get("latency_ms"),
                        tokens_in=r.get("tokens_in"),
                        tokens_out=r.get("tokens_out"),
                    )
                )
        print(f"pushed run {run_row} ({len(records)} results)")
    finally:
        await db.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="items, spread across categories")
    parser.add_argument("--ids", nargs="*", default=None)
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--ragas", action="store_true", help="force RAGAs metrics")
    parser.add_argument("--no-ragas", action="store_true", help="skip RAGAs metrics")
    parser.add_argument(
        "--push", action="store_true", help="store the run in eval_runs/eval_results"
    )
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
