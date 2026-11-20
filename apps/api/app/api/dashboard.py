"""Progress dashboard (one call) and the learner's knowledge map (graph + mastery per node)."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app.api.recommendations import streak_days
from app.auth.deps import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.db.session import Database, get_database
from app.db.tables import chat_messages, chat_threads, notes, questions, quiz_answers, quiz_sessions
from app.graph.provider import GraphProvider
from app.llm.deps import get_usage_guard
from app.mastery.model import MasteryParams, band
from app.mastery.repository import MasteryRepository
from app.recommender.engine import frontier_gap, weak_concepts
from app.recommender.service import RecommenderService, build_graph, learner_state
from app.usage.guard import UsageGuard

router = APIRouter(tags=["dashboard"])
User = Annotated[CurrentUser, Depends(get_current_user)]
SUBJECT = Annotated[str, Query(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
TUTOR_SECONDS_PER_QUESTION = 90  # time-on-task estimate for a tutor question
TREND_DAYS = 30
FEED_ITEMS = 12


def _iso_day(d: dt.date) -> str:
    return d.isoformat()


@router.get("/dashboard")
async def dashboard(
    request: Request,
    user: User,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    guard: Annotated[UsageGuard, Depends(get_usage_guard)],
    subject_id: SUBJECT = "dsa",
) -> dict[str, Any]:
    now = dt.datetime.now(dt.UTC)
    week_ago = now - dt.timedelta(days=7)
    params = MasteryParams.from_settings(settings)
    provider: GraphProvider = request.app.state.graph
    graph_source = provider.repository()
    graph = await build_graph(graph_source, subject_id)
    concepts = {
        c.id: c for c in await graph_source.list_concepts(subject_id) if c.status == "approved"
    }

    async with db.sessions()() as session:
        view = await MasteryRepository(session, params).view(user.id, subject_id, now)
        state = await learner_state(session, user.id, subject_id, params, now)
        quiz_week = (
            await session.execute(
                select(func.count())
                .select_from(quiz_sessions)
                .where(
                    quiz_sessions.c.user_id == user.id,
                    quiz_sessions.c.submitted_at >= week_ago,
                )
            )
        ).scalar_one()
        quiz_ms = (
            await session.execute(
                select(func.coalesce(func.sum(quiz_answers.c.time_ms), 0)).where(
                    quiz_answers.c.user_id == user.id, quiz_answers.c.created_at >= week_ago
                )
            )
        ).scalar_one()
        tutor_week = (
            await session.execute(
                select(func.count())
                .select_from(chat_messages)
                .where(
                    chat_messages.c.user_id == user.id,
                    chat_messages.c.role == "user",
                    chat_messages.c.created_at >= week_ago,
                )
            )
        ).scalar_one()
        trend_rows = (
            await session.execute(
                select(
                    func.date(quiz_answers.c.created_at).label("day"),
                    func.avg(quiz_answers.c.score),
                    func.count(),
                )
                .where(
                    quiz_answers.c.user_id == user.id,
                    quiz_answers.c.score.is_not(None),
                    quiz_answers.c.created_at >= now - dt.timedelta(days=TREND_DAYS),
                )
                .group_by("day")
                .order_by("day")
            )
        ).all()
        active_days = {
            r[0]
            for r in await session.execute(
                select(func.date(quiz_answers.c.created_at))
                .where(
                    quiz_answers.c.user_id == user.id,
                    quiz_answers.c.created_at >= now - dt.timedelta(days=400),
                )
                .distinct()
            )
        }
        recent_quizzes = (
            await session.execute(
                select(
                    quiz_sessions.c.id,
                    quiz_sessions.c.mode,
                    quiz_sessions.c.concept_id,
                    quiz_sessions.c.score,
                    quiz_sessions.c.max_score,
                    quiz_sessions.c.submitted_at,
                )
                .where(
                    quiz_sessions.c.user_id == user.id, quiz_sessions.c.submitted_at.is_not(None)
                )
                .order_by(quiz_sessions.c.submitted_at.desc())
                .limit(FEED_ITEMS)
            )
        ).all()
        recent_questions = (
            await session.execute(
                select(chat_messages.c.content, chat_messages.c.created_at, chat_threads.c.id)
                .select_from(
                    chat_messages.join(chat_threads, chat_threads.c.id == chat_messages.c.thread_id)
                )
                .where(
                    chat_messages.c.user_id == user.id,
                    chat_messages.c.role == "user",
                    chat_messages.c.superseded_at.is_(None),
                )
                .order_by(chat_messages.c.created_at.desc())
                .limit(FEED_ITEMS)
            )
        ).all()
        recent_notes = (
            await session.execute(
                select(notes.c.concept_id, notes.c.updated_at, notes.c.bookmarked)
                .where(notes.c.user_id == user.id)
                .order_by(notes.c.updated_at.desc())
                .limit(5)
            )
        ).all()
        n_questions: dict[str, int] = dict(
            (
                await session.execute(
                    select(questions.c.concept_id, func.count())
                    .where(questions.c.subject_id == subject_id, questions.c.status == "active")
                    .group_by(questions.c.concept_id)
                )
            ).all()
        )

    practised = {m["concept_id"]: m for m in view if m["attempts"] > 0}
    eff = {cid: practised[cid]["effective"] if cid in practised else 0.0 for cid in concepts}
    bands = {"weak": 0, "developing": 0, "strong": 0, "not_started": 0}
    for cid in concepts:
        if cid in practised:
            bands[band(practised[cid]["effective"], params)] += 1
        else:
            bands["not_started"] += 1
    clusters: dict[str, dict[str, Any]] = {}
    for c in sorted(concepts.values(), key=lambda c: c.order_index):
        k = clusters.setdefault(
            c.cluster, {"cluster": c.cluster, "concepts": 0, "practised": 0, "total": 0.0}
        )
        k["concepts"] += 1
        k["practised"] += 1 if c.id in practised else 0
        k["total"] += eff[c.id]
    per_cluster = [
        {
            "cluster": k["cluster"],
            "concepts": k["concepts"],
            "practised": k["practised"],
            "mastery": round(k["total"] / k["concepts"], 3),
        }
        for k in clusters.values()
    ]

    weak = []
    for w in weak_concepts(graph, state)[:3]:
        gap = frontier_gap(graph, state, w)
        weak.append(
            {
                "concept_id": w,
                "name": graph.name(w),
                "mastery": state.effective.get(w),
                "asked": state.asked_7d.get(w, 0),
                "fix": {"concept_id": gap[0], "name": graph.name(gap[0])} if gap else None,
            }
        )

    feed: list[dict[str, Any]] = []
    for r in recent_quizzes:
        feed.append(
            {
                "kind": "quiz",
                "at": r.submitted_at,
                "id": str(r.id),
                "mode": str(r.mode),
                "concept_id": r.concept_id,
                "name": graph.name(r.concept_id) if r.concept_id else None,
                "score": float(r.score or 0),
                "max_score": float(r.max_score or 0),
            }
        )
    for qr in recent_questions:
        feed.append(
            {
                "kind": "question",
                "at": qr.created_at,
                "thread_id": str(qr.id),
                "text": qr.content[:140],
            }
        )
    for nr in recent_notes:
        feed.append(
            {
                "kind": "note",
                "at": nr.updated_at,
                "concept_id": nr.concept_id,
                "name": graph.name(nr.concept_id),
                "bookmarked": nr.bookmarked,
            }
        )
    feed.sort(key=lambda e: e["at"], reverse=True)

    trend_by_day = {r[0]: (float(r[1]), int(r[2])) for r in trend_rows}
    trend = []
    for i in range(TREND_DAYS - 1, -1, -1):
        d = (now - dt.timedelta(days=i)).date()
        avg, n = trend_by_day.get(d, (None, 0))
        trend.append(
            {
                "date": _iso_day(d),
                "accuracy": round(avg, 3) if avg is not None else None,
                "answers": n,
            }
        )

    recs = await RecommenderService(db, settings, graph_source).for_user(
        user, subject_id, surface="dashboard"
    )
    usage = await guard.usage_summary(user, days=1)
    return {
        "subject_id": subject_id,
        "overall_mastery": round(sum(eff.values()) / len(concepts), 3) if concepts else 0.0,
        "concepts_total": len(concepts),
        "concepts_practised": len(practised),
        "bands": bands,
        "streak_days": streak_days(active_days, now.date()),
        "time_on_task_minutes_7d": round(
            (int(quiz_ms) / 1000 + int(tutor_week) * TUTOR_SECONDS_PER_QUESTION) / 60
        ),
        "quizzes_this_week": int(quiz_week),
        "tutor_questions_this_week": int(tutor_week),
        "accuracy_trend": trend,
        "per_cluster": per_cluster,
        "weak_concepts": weak,
        "activity": feed[:FEED_ITEMS],
        "recommendations": recs,
        "review_due": len(state.due),
        "usage_today": {
            "ai_requests": usage["today"]["ai_requests"],
            "daily_quota": usage["limits"]["daily_ai_requests"],
        },
        "question_counts": {cid: int(n) for cid, n in n_questions.items()},
    }


@router.get("/graph/mastery")
async def graph_mastery(
    request: Request,
    user: User,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: SUBJECT = "dsa",
) -> dict[str, Any]:
    """Every approved concept with the learner's effective mastery, plus approved edges."""
    provider: GraphProvider = request.app.state.graph
    repo = provider.repository()
    params = MasteryParams.from_settings(settings)
    async with db.sessions()() as session:
        rows = {
            m["concept_id"]: m
            for m in await MasteryRepository(session, params).view(user.id, subject_id)
        }
    nodes = []
    for c in await repo.list_concepts(subject_id):
        if c.status != "approved":
            continue
        m = rows.get(c.id)
        practised = bool(m and m["attempts"] > 0)
        nodes.append(
            {
                "id": c.id,
                "name": c.name,
                "cluster": c.cluster,
                "difficulty": c.difficulty,
                "order_index": c.order_index,
                "description": c.description,
                "mastery": m["effective"] if practised and m else None,
                "band": m["band"] if practised and m else "not_started",
                "attempts": m["attempts"] if m else 0,
                "last_practiced_at": m["last_practiced_at"] if m else None,
                "next_review_at": m["next_review_at"] if m else None,
            }
        )
    edges = [
        {"source": e.source, "target": e.target, "type": e.type}
        for e in await repo.list_edges(subject_id)
        if e.status == "approved"
    ]
    return {"subject_id": subject_id, "nodes": nodes, "edges": edges}
