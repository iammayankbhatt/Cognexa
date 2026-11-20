"""Admin evaluation console: runs pushed by evaluation/ragas_eval.py --push (read-only)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.auth.deps import CurrentUser, require_role
from app.core.errors import AppError
from app.db.session import Database, get_database
from app.db.tables import eval_results, eval_runs

router = APIRouter(prefix="/admin/evaluation", tags=["admin"])
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
DB = Annotated[Database, Depends(get_database)]


def _run(r: Any, results: int | None = None) -> dict[str, Any]:
    summary = r.summary or {}
    return {
        "id": str(r.id),
        "name": r.name,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "config": r.config or {},
        "results": results,
        "headline": (summary.get("table") or {}),
        "headline_pairs": summary.get("headline_pairs") or [],
        "overall_pairs": summary.get("overall_pairs") or [],
    }


@router.get("/runs")
async def list_runs(_: Reviewer, db: DB) -> dict[str, Any]:
    async with db.sessions()() as session:
        counts: dict[uuid.UUID, int] = dict(
            (
                await session.execute(
                    select(eval_results.c.run_id, func.count()).group_by(eval_results.c.run_id)
                )
            ).all()
        )
        rows = (
            await session.execute(
                select(eval_runs).order_by(eval_runs.c.started_at.desc()).limit(50)
            )
        ).all()
    items = []
    for r in rows:
        v = _run(r, int(counts.get(r.id, 0)))
        v.pop("headline")  # the list stays light; GET /runs/{id} has the tables
        items.append(v)
    return {"items": items}


@router.get("/runs/{run_id}")
async def get_run(run_id: uuid.UUID, _: Reviewer, db: DB) -> dict[str, Any]:
    async with db.sessions()() as session:
        row = (await session.execute(select(eval_runs).where(eval_runs.c.id == run_id))).first()
        if row is None:
            raise AppError("not_found", "Evaluation run not found.", 404)
        n = (
            await session.execute(
                select(func.count())
                .select_from(eval_results)
                .where(eval_results.c.run_id == run_id)
            )
        ).scalar_one()
    return _run(row, int(n))


@router.get("/runs/{run_id}/items")
async def run_items(
    run_id: uuid.UUID,
    _: Reviewer,
    db: DB,
    category: Annotated[str | None, Query(max_length=40)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    """Items with both modes side by side (answer, metrics, context concepts)."""
    async with db.sessions()() as session:
        rows = (
            await session.execute(
                select(eval_results)
                .where(eval_results.c.run_id == run_id)
                .order_by(eval_results.c.item_id, eval_results.c.mode)
            )
        ).all()
    items: dict[str, dict[str, Any]] = {}
    for r in rows:
        m = r.metrics or {}
        if category and m.get("category") != category:
            continue
        if q and q.lower() not in r.question.lower():
            continue
        item = items.setdefault(
            r.item_id,
            {
                "item_id": r.item_id,
                "question": r.question,
                "category": m.get("category"),
                "gold_concepts": m.get("gold_concepts") or [],
                "gold_prerequisites": m.get("gold_prerequisites") or [],
                "modes": {},
            },
        )
        item["modes"][str(r.mode)] = {
            "answer": r.answer,
            "context_concepts": list(
                dict.fromkeys(c.get("concept_id") for c in (r.contexts or []))
            ),
            "metrics": {
                k: v
                for k, v in m.items()
                if k not in ("category", "gold_concepts", "gold_prerequisites")
            },
            "latency_ms": r.latency_ms,
            "tokens": (r.tokens_in or 0) + (r.tokens_out or 0),
        }
    return {"items": list(items.values()), "total": len(items)}
