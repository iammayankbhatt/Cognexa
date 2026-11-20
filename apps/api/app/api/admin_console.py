"""Admin console: overview, moderation of reported answers, thumbs-down analytics, a user's usage
(never their chats unless an answer was reported; privacy policy), and usage CSV export."""

from __future__ import annotations

import csv
import datetime as dt
import io
import uuid
from collections import Counter
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.auth.deps import CurrentUser, require_role
from app.cache.service import LLMCache
from app.core.errors import AppError
from app.core.ratelimit import limit_by_user
from app.db.profiles import ProfileRepository, auth_users
from app.db.repositories import DEFAULT_APP_SETTINGS, AppSettingsRepository
from app.db.session import Database, get_database, get_session
from app.db.tables import (
    chat_messages,
    eval_runs,
    global_usage_daily,
    graph_proposals,
    llm_calls,
    message_feedback,
    profiles,
    quiz_sessions,
    usage_daily,
)

router = APIRouter(prefix="/admin", tags=["admin"])
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
AdminUser = Annotated[CurrentUser, Depends(require_role("admin"))]
Session = Annotated[AsyncSession, Depends(get_session)]
ReportStatus = Literal["open", "reviewing", "resolved", "dismissed"]


def _today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


# ---------------------------------------------------------------------- overview
@router.get("/overview")
async def overview(_: Reviewer, session: Session) -> dict[str, Any]:
    today = _today()
    week = today - dt.timedelta(days=6)
    users = (await session.execute(select(func.count()).select_from(profiles))).scalar_one()

    async def active_since(day: dt.date) -> int:
        since = dt.datetime.combine(day, dt.time(), tzinfo=dt.UTC)
        ai = select(usage_daily.c.user_id).where(
            usage_daily.c.date >= day, usage_daily.c.ai_requests > 0
        )
        quiz = select(quiz_sessions.c.user_id).where(quiz_sessions.c.started_at >= since)
        both = ai.union(quiz).subquery()
        return int((await session.execute(select(func.count()).select_from(both))).scalar_one())

    g = (
        await session.execute(select(global_usage_daily).where(global_usage_daily.c.date == today))
    ).first()
    cap_setting = await AppSettingsRepository(session).get("quota.global_daily_cap")
    cap = int((cap_setting or DEFAULT_APP_SETTINGS["quota.global_daily_cap"])["ai_requests"])
    start = dt.datetime.combine(today, dt.time(), tzinfo=dt.UTC)
    calls = (
        await session.execute(
            select(
                func.count(),
                func.sum(cast(llm_calls.c.cached, Integer)),
                func.sum(llm_calls.c.est_cost_usd),
            ).where(llm_calls.c.created_at >= start)
        )
    ).one()
    open_reports = (
        await session.execute(
            select(func.count()).where(
                message_feedback.c.report_reason.is_not(None),
                message_feedback.c.status.in_(["open", "reviewing"]),
            )
        )
    ).scalar_one()
    pending = (
        await session.execute(select(func.count()).where(graph_proposals.c.status == "pending"))
    ).scalar_one()
    last_eval = (
        await session.execute(
            select(eval_runs.c.id, eval_runs.c.name, eval_runs.c.finished_at)
            .order_by(eval_runs.c.started_at.desc())
            .limit(1)
        )
    ).first()
    n_calls, n_cached, cost = int(calls[0] or 0), int(calls[1] or 0), float(calls[2] or 0)
    return {
        "users": int(users),
        "dau": await active_since(today),
        "wau": await active_since(week),
        "ai_requests_today": int(g.ai_requests) if g else 0,
        "global_cap": cap,
        "cache_hit_rate_today": round(n_cached / n_calls, 4) if n_calls else None,
        "est_cost_today_usd": round(cost, 6),
        "open_reports": int(open_reports),
        "pending_proposals": int(pending),
        "last_eval_run": (
            {"id": str(last_eval.id), "name": last_eval.name, "finished_at": last_eval.finished_at}
            if last_eval
            else None
        ),
    }


# ---------------------------------------------------------------------- moderation
class ReportAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["reviewing", "resolved", "dismissed"]
    note: str | None = Field(default=None, max_length=2000)


def _concepts(trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not trace:
        return []
    return [
        {"id": c.get("id"), "name": c.get("name"), "role": c.get("role")}
        for c in trace.get("concepts", [])
        if isinstance(c, dict)
    ]


@router.get("/reports")
async def list_reports(
    _: Reviewer,
    session: Session,
    status: Annotated[ReportStatus | None, Query()] = "open",
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> dict[str, Any]:
    """Reported answers with the full message, the question it answered, the retrieval trace and
    the student's comment (reported answers are the only chat content reviewers can see)."""
    question = aliased(chat_messages)
    conds: list[Any] = [message_feedback.c.report_reason.is_not(None)]
    if status:
        conds.append(message_feedback.c.status == status)
    base = (
        select(
            message_feedback.c.id,
            message_feedback.c.report_reason,
            message_feedback.c.comment,
            message_feedback.c.status,
            message_feedback.c.resolution_note,
            message_feedback.c.created_at,
            message_feedback.c.user_id,
            auth_users.c.email,
            chat_messages.c.id.label("message_id"),
            chat_messages.c.content,
            chat_messages.c.mode,
            chat_messages.c.retrieval_trace,
            chat_messages.c.created_at.label("answered_at"),
            question.c.content.label("question"),
        )
        .select_from(
            message_feedback.join(
                chat_messages, chat_messages.c.id == message_feedback.c.message_id
            )
            .outerjoin(question, question.c.id == chat_messages.c.reply_to)
            .outerjoin(auth_users, auth_users.c.id == message_feedback.c.user_id)
        )
        .where(*conds)
    )
    total = (await session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await session.execute(
            base.order_by(message_feedback.c.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()
    items = [
        {
            "id": str(r.id),
            "reason": r.report_reason,
            "comment": r.comment,
            "status": r.status,
            "resolution_note": r.resolution_note,
            "reported_at": r.created_at,
            "reporter": r.email,
            "message": {
                "id": str(r.message_id),
                "content": r.content,
                "mode": r.mode,
                "answered_at": r.answered_at,
                "question": r.question,
                "trace": r.retrieval_trace,
                "concepts": _concepts(r.retrieval_trace),
            },
        }
        for r in rows
    ]
    return {"items": items, "total": int(total), "page": page, "page_size": page_size}


async def _report(session: AsyncSession, report_id: uuid.UUID) -> Any:
    row = (
        await session.execute(
            select(message_feedback, chat_messages.c.retrieval_trace)
            .join(chat_messages, chat_messages.c.id == message_feedback.c.message_id)
            .where(
                message_feedback.c.id == report_id, message_feedback.c.report_reason.is_not(None)
            )
        )
    ).first()
    if row is None:
        raise AppError("not_found", "Report not found.", 404)
    return row


@router.post("/reports/{report_id}")
async def act_on_report(
    report_id: uuid.UUID, body: ReportAction, user: Reviewer, session: Session
) -> dict[str, Any]:
    await _report(session, report_id)
    await session.execute(
        update(message_feedback)
        .where(message_feedback.c.id == report_id)
        .values(
            status=body.status,
            resolution_note=body.note,
            resolved_by=user.id if body.status != "reviewing" else None,
            updated_at=func.now(),
        )
    )
    await ProfileRepository(session).audit(
        user.id, f"moderation.{body.status}", str(report_id), {"note": body.note}
    )
    await session.commit()
    return {"id": str(report_id), "status": body.status, "resolution_note": body.note}


@router.post("/reports/{report_id}/invalidate-cache")
async def invalidate_report_cache(
    report_id: uuid.UUID,
    user: Reviewer,
    session: Session,
    db: Annotated[Database, Depends(get_database)],
) -> dict[str, Any]:
    """Never serve the cached answer behind this report again (cache_key in the trace)."""
    row = await _report(session, report_id)
    key = (row.retrieval_trace or {}).get("cache_key")
    removed = await LLMCache(db).invalidate_key(key) if key else 0
    await ProfileRepository(session).audit(
        user.id, "moderation.invalidate_cache", str(report_id), {"removed": removed}
    )
    await session.commit()
    return {"removed": removed, "had_cache_key": bool(key)}


@router.get("/feedback/by-concept")
async def thumbs_down_by_concept(
    _: Reviewer,
    session: Session,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict[str, Any]:
    """Thumbs up/down and reports per matched concept: where answers disappoint students."""
    since = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
    rows = (
        await session.execute(
            select(
                message_feedback.c.rating,
                message_feedback.c.report_reason,
                chat_messages.c.matched_concepts,
            )
            .join(chat_messages, chat_messages.c.id == message_feedback.c.message_id)
            .where(message_feedback.c.created_at >= since)
        )
    ).all()
    down: Counter[str] = Counter()
    up: Counter[str] = Counter()
    reports: Counter[str] = Counter()
    names: dict[str, str] = {}
    for r in rows:
        for m in r.matched_concepts or []:
            cid = m.get("id") if isinstance(m, dict) else m
            if not isinstance(cid, str):
                continue
            if isinstance(m, dict) and m.get("name"):
                names[cid] = m["name"]
            if r.rating == -1:
                down[cid] += 1
            elif r.rating == 1:
                up[cid] += 1
            if r.report_reason:
                reports[cid] += 1
    ids = sorted(set(down) | set(reports) | set(up), key=lambda c: (-down[c], -reports[c], c))
    return {
        "days": days,
        "items": [
            {
                "concept_id": c,
                "name": names.get(c, c),
                "thumbs_down": down[c],
                "thumbs_up": up[c],
                "reports": reports[c],
            }
            for c in ids
        ],
    }


# ---------------------------------------------------------------------- users & usage
@router.get("/users/{user_id}/usage")
async def user_usage(
    user_id: uuid.UUID,
    _: AdminUser,
    session: Session,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict[str, Any]:
    """A user's AI usage and activity counts. No chat content (privacy policy)."""
    profile = await ProfileRepository(session).get(user_id)
    if profile is None:
        raise AppError("not_found", "User not found.", 404)
    since = _today() - dt.timedelta(days=days - 1)
    history = [
        {
            "date": r.date,
            "ai_requests": int(r.ai_requests),
            "tokens_in": int(r.tokens_in),
            "tokens_out": int(r.tokens_out),
            "est_cost_usd": float(r.est_cost_usd or 0),
        }
        for r in await session.execute(
            select(usage_daily)
            .where(usage_daily.c.user_id == user_id, usage_daily.c.date >= since)
            .order_by(usage_daily.c.date)
        )
    ]
    quizzes = (
        await session.execute(select(func.count()).where(quiz_sessions.c.user_id == user_id))
    ).scalar_one()
    questions = (
        await session.execute(
            select(func.count()).where(
                chat_messages.c.user_id == user_id, chat_messages.c.role == "user"
            )
        )
    ).scalar_one()
    reports = (
        await session.execute(
            select(func.count()).where(
                message_feedback.c.user_id == user_id, message_feedback.c.report_reason.is_not(None)
            )
        )
    ).scalar_one()
    return {
        "user_id": str(user_id),
        "days": days,
        "history": history,
        "totals": {
            "ai_requests": sum(h["ai_requests"] for h in history),
            "est_cost_usd": round(sum(h["est_cost_usd"] for h in history), 6),
            "quizzes": int(quizzes),
            "tutor_questions": int(questions),
            "reports_filed": int(reports),
        },
    }


@router.get("/usage/export.csv", dependencies=[Depends(limit_by_user("admin_export"))])
async def usage_csv(
    _: AdminUser,
    session: Session,
    request: Request,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> Response:
    """One row per day x provider x model: calls, cached, fallbacks, tokens, notional cost."""
    since = dt.datetime.combine(_today() - dt.timedelta(days=days - 1), dt.time(), tzinfo=dt.UTC)
    day = func.date(llm_calls.c.created_at)
    rows = await session.execute(
        select(
            day.label("date"),
            llm_calls.c.provider,
            llm_calls.c.model,
            func.count().label("calls"),
            func.sum(cast(llm_calls.c.cached, Integer)).label("cached"),
            func.sum(cast(llm_calls.c.fallback_used, Integer)).label("fallbacks"),
            func.sum(llm_calls.c.tokens_in).label("tokens_in"),
            func.sum(llm_calls.c.tokens_out).label("tokens_out"),
            func.sum(llm_calls.c.est_cost_usd).label("cost"),
        )
        .where(llm_calls.c.created_at >= since)
        .group_by(day, llm_calls.c.provider, llm_calls.c.model)
        .order_by(day, llm_calls.c.provider, llm_calls.c.model)
    )
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["date", "provider", "model", "calls", "cached", "fallbacks", "tokens_in",
                "tokens_out", "est_cost_usd"])  # fmt: skip
    for r in rows:
        w.writerow([r.date, r.provider, r.model, r.calls, r.cached or 0, r.fallbacks or 0,
                    r.tokens_in or 0, r.tokens_out or 0, f"{float(r.cost or 0):.6f}"])  # fmt: skip
    stamp = _today().strftime("%Y%m%d")
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="cognexa-usage-{stamp}.csv"'},
    )
