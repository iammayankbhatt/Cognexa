"""Recommendations (next best step) and the spaced-review queue. Neither uses AI, so both keep
working when the LLM quota is exhausted."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app.auth.deps import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import Database, get_database
from app.db.tables import concepts, questions, quiz_answers
from app.graph.provider import GraphProvider
from app.mastery.model import MasteryParams
from app.mastery.repository import MasteryRepository
from app.recommender.service import RecommenderService

router = APIRouter(tags=["recommendations"])
User = Annotated[CurrentUser, Depends(get_current_user)]
SUBJECT = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
REVIEW_QUESTIONS = 5


def get_recommender(
    request: Request,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RecommenderService:
    provider: GraphProvider = request.app.state.graph
    return RecommenderService(db, settings, provider.repository())


Recommender = Annotated[RecommenderService, Depends(get_recommender)]


@router.get("/recommendations")
async def recommendations(
    user: User,
    service: Recommender,
    subject_id: SUBJECT = "dsa",
    surface: Literal["dashboard", "tutor", "quiz", "review", "learn"] = "dashboard",
    limit: Annotated[int, Query(ge=1, le=3)] = 3,
) -> dict[str, Any]:
    return await service.for_user(user, subject_id, surface=surface, limit=limit)


@router.post("/recommendations/{log_id}/click", status_code=204)
async def click(log_id: uuid.UUID, user: User, service: Recommender) -> None:
    if not await service.click(user, log_id):
        raise AppError("not_found", "Recommendation not found.", 404)


def streak_days(days: set[dt.date], today: dt.date) -> int:
    """Consecutive days with quiz activity, ending today (or yesterday, if nothing yet today)."""
    start = today if today in days else today - dt.timedelta(days=1)
    n = 0
    while start - dt.timedelta(days=n) in days:
        n += 1
    return n


@router.get("/review/due")
async def review_due(
    user: User,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: SUBJECT = "dsa",
) -> dict[str, Any]:
    """Concepts due for spaced review (with up to 5 question ids each), the next due date and the
    activity streak."""
    now = dt.datetime.now(dt.UTC)
    params = MasteryParams.from_settings(settings)
    async with db.sessions()() as session:
        view = await MasteryRepository(session, params).view(user.id, subject_id, now)
        scheduled = [m for m in view if m["next_review_at"] is not None]
        due = sorted(
            (m for m in scheduled if m["next_review_at"] <= now), key=lambda m: m["next_review_at"]
        )
        upcoming = sorted(m["next_review_at"] for m in scheduled if m["next_review_at"] > now)
        ids = [m["concept_id"] for m in due]
        names: dict[str, str] = {}
        qrows: list[Any] = []
        if ids:
            name_rows = await session.execute(
                select(concepts.c.id, concepts.c.name).where(concepts.c.id.in_(ids))
            )
            names = {r.id: r.name for r in name_rows}
            q_result = await session.execute(
                select(questions.c.concept_id, questions.c.id)
                .where(questions.c.concept_id.in_(ids), questions.c.status == "active")
                .order_by(questions.c.concept_id, questions.c.difficulty, questions.c.id)
            )
            qrows = list(q_result.all())
        active = await session.execute(
            select(func.date(quiz_answers.c.created_at))
            .where(
                quiz_answers.c.user_id == user.id,
                quiz_answers.c.created_at >= now - dt.timedelta(days=400),
            )
            .distinct()
        )
        days = {r[0] for r in active}
    by_concept: dict[str, list[str]] = {}
    for cid, qid in qrows:
        lst = by_concept.setdefault(cid, [])
        if len(lst) < REVIEW_QUESTIONS:
            lst.append(qid)
    return {
        "due": [
            {
                "concept_id": m["concept_id"],
                "name": names.get(m["concept_id"], m["concept_id"]),
                "effective": m["effective"],
                "band": m["band"],
                "next_review_at": m["next_review_at"],
                "question_ids": by_concept.get(m["concept_id"], []),
            }
            for m in due
        ],
        "next_due_at": upcoming[0] if upcoming else None,
        "scheduled": len(scheduled),
        "streak_days": streak_days(days, now.date()),
    }
