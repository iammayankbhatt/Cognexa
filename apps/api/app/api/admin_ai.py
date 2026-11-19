"""Admin: AI usage dashboard data, editable settings (quotas, cache, flags, pricing), LLM check."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, require_role
from app.cache.service import LLMCache
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.flags import get_flags
from app.db.profiles import ProfileRepository, auth_users
from app.db.repositories import DEFAULT_APP_SETTINGS, AppSettingsRepository
from app.db.session import Database, get_database, get_session
from app.db.tables import global_usage_daily, llm_calls, usage_daily
from app.guardrails.output import check_output
from app.guardrails.prompts import GUARD_RULES
from app.llm.deps import get_llm, get_usage_guard
from app.llm.errors import LLMError
from app.llm.router import LLMRouter
from app.llm.types import Message
from app.usage.guard import UsageGuard

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[CurrentUser, Depends(require_role("admin"))]
Session = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------- usage


def _num(v: Any) -> float:
    return float(v or 0)


@router.get("/usage")
async def admin_usage(
    _: AdminUser,
    session: Session,
    db: Annotated[Database, Depends(get_database)],
    llm: Annotated[LLMRouter, Depends(get_llm)],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> dict[str, Any]:
    """Usage by day, by user, by provider/model, notional cost, cache hit and fallback rates."""
    today = dt.datetime.now(dt.UTC).date()
    since = today - dt.timedelta(days=days - 1)
    since_ts = dt.datetime.combine(since, dt.time(), tzinfo=dt.UTC)

    cost_by_day = dict(
        (
            await session.execute(
                select(usage_daily.c.date, func.sum(usage_daily.c.est_cost_usd))
                .where(usage_daily.c.date >= since)
                .group_by(usage_daily.c.date)
            )
        ).all()
    )
    by_day = [
        {
            "date": r.date,
            "ai_requests": int(r.ai_requests),
            "tokens_in": int(r.tokens_in),
            "tokens_out": int(r.tokens_out),
            "est_cost_usd": _num(cost_by_day.get(r.date)),
        }
        for r in await session.execute(
            select(global_usage_daily)
            .where(global_usage_daily.c.date >= since)
            .order_by(global_usage_daily.c.date)
        )
    ]

    user_rows = await session.execute(
        select(
            usage_daily.c.user_id,
            auth_users.c.email,
            func.sum(usage_daily.c.ai_requests).label("requests"),
            func.sum(usage_daily.c.tokens_in + usage_daily.c.tokens_out).label("tokens"),
            func.sum(usage_daily.c.est_cost_usd).label("cost"),
        )
        .select_from(usage_daily.outerjoin(auth_users, auth_users.c.id == usage_daily.c.user_id))
        .where(usage_daily.c.date >= since)
        .group_by(usage_daily.c.user_id, auth_users.c.email)
        .order_by(func.sum(usage_daily.c.ai_requests).desc())
        .limit(20)
    )
    by_user = [
        {
            "user_id": str(r.user_id),
            "email": r.email,
            "ai_requests": int(r.requests or 0),
            "tokens": int(r.tokens or 0),
            "est_cost_usd": _num(r.cost),
        }
        for r in user_rows
    ]

    model_rows = await session.execute(
        select(
            llm_calls.c.provider,
            llm_calls.c.model,
            func.count().label("calls"),
            func.sum(llm_calls.c.tokens_in).label("tokens_in"),
            func.sum(llm_calls.c.tokens_out).label("tokens_out"),
            func.sum(llm_calls.c.est_cost_usd).label("cost"),
            func.avg(case((llm_calls.c.cached.is_(False), llm_calls.c.latency_ms))).label("lat"),
            func.sum(cast(llm_calls.c.cached, Integer)).label("cached"),
            func.sum(cast(llm_calls.c.fallback_used, Integer)).label("fallback"),
        )
        .where(llm_calls.c.created_at >= since_ts)
        .group_by(llm_calls.c.provider, llm_calls.c.model)
        .order_by(func.count().desc())
    )
    by_model = [
        {
            "provider": r.provider,
            "model": r.model,
            "calls": int(r.calls),
            "tokens_in": int(r.tokens_in or 0),
            "tokens_out": int(r.tokens_out or 0),
            "est_cost_usd": _num(r.cost),
            "avg_latency_ms": round(_num(r.lat)),
            "cached": int(r.cached or 0),
            "fallback": int(r.fallback or 0),
        }
        for r in model_rows
    ]
    calls = sum(m["calls"] for m in by_model)
    cached = sum(m["cached"] for m in by_model)
    fallback = sum(m["fallback"] for m in by_model)
    return {
        "days": days,
        "since": since,
        "totals": {
            "ai_requests": sum(d["ai_requests"] for d in by_day),
            "tokens": sum(d["tokens_in"] + d["tokens_out"] for d in by_day),
            "est_cost_usd": round(sum(d["est_cost_usd"] for d in by_day), 6),
            "calls": calls,
            "cache_hit_rate": round(cached / calls, 4) if calls else 0.0,
            "fallback_rate": round(fallback / (calls - cached), 4) if calls - cached else 0.0,
        },
        "by_day": by_day,
        "by_user": by_user,
        "by_model": by_model,
        "cache": await LLMCache(db).stats(),
        "providers": llm.status(),
    }


# ---------------------------------------------------------------- settings


class QuotaSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_ai_requests: int = Field(ge=0, le=10000)
    per_minute: int = Field(ge=1, le=600)
    max_input_chars: int = Field(ge=100, le=20000)
    max_output_tokens: int = Field(ge=50, le=8000)


class RoleMultipliers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student: int = Field(ge=1, le=100)
    reviewer: int = Field(ge=1, le=100)
    admin: int = Field(ge=1, le=100)


class GlobalCap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ai_requests: int = Field(ge=0, le=1_000_000)


class CacheSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    response_ttl_days: float = Field(gt=0, le=90)
    classification_ttl_days: float = Field(gt=0, le=90)
    embedding_ttl_days: float = Field(gt=0, le=365)


class Features(BaseModel):
    model_config = ConfigDict(extra="forbid")

    AGENTIC_MODE: bool
    STUDY_MODE: bool
    PLAIN_RAG_VISIBLE_TO_STUDENTS: bool


class Price(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_per_1m: float = Field(ge=0, le=1000)
    output_per_1m: float = Field(ge=0, le=1000)


class Pricing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default: Price
    models: dict[Annotated[str, Field(min_length=1, max_length=120)], Price] = Field(
        default_factory=dict, max_length=50
    )


class SettingsIn(BaseModel):
    """Any subset of sections; each section given is replaced as a whole."""

    model_config = ConfigDict(extra="forbid")

    quota: QuotaSettings | None = None
    role_multipliers: RoleMultipliers | None = None
    global_cap: GlobalCap | None = None
    cache: CacheSettings | None = None
    features: Features | None = None
    pricing: Pricing | None = None


SECTION_KEYS = {
    "quota": "quota.student",
    "role_multipliers": "quota.role_multipliers",
    "global_cap": "quota.global_daily_cap",
    "cache": "cache",
    "features": "features",
    "pricing": "llm.pricing",
}


async def _settings_view(session: AsyncSession, settings: Settings) -> dict[str, Any]:
    repo = AppSettingsRepository(session)
    view: dict[str, Any] = {}
    for section, key in SECTION_KEYS.items():
        if section == "features":
            view[section] = await get_flags(session, settings)
        else:
            view[section] = {**DEFAULT_APP_SETTINGS[key], **(await repo.get(key) or {})}
    view["providers"] = {  # read-only: configured in env (model ids never hard-coded)
        "primary": {"provider": settings.llm_primary_provider, "model": settings.llm_primary_model},
        "fallback": {
            "provider": settings.llm_fallback_provider,
            "model": settings.llm_fallback_model,
        },
        "judge": {"provider": settings.llm_judge_provider, "model": settings.llm_judge_model},
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "dim": settings.embedding_dim,
        },
        "keys": {"groq": bool(settings.groq_api_key), "gemini": bool(settings.gemini_api_key)},
    }
    return view


@router.get("/settings")
async def get_admin_settings(
    _: AdminUser, session: Session, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, Any]:
    return await _settings_view(session, settings)


@router.put("/settings")
async def put_admin_settings(
    body: SettingsIn,
    admin: AdminUser,
    session: Session,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    changed = body.model_dump(exclude_none=True)
    if not changed:
        raise AppError("validation_error", "Send at least one settings section.", 422)
    repo = AppSettingsRepository(session)
    for section, value in changed.items():
        await repo.set(SECTION_KEYS[section], value)
    await ProfileRepository(session).audit(
        admin.id, "settings.update", ",".join(sorted(changed)), changed
    )
    return await _settings_view(session, settings)


# ---------------------------------------------------------------- live LLM check


class LLMCheckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(default="Reply with the single word: ready", min_length=1, max_length=200)


@router.post("/llm/check")
async def llm_check(
    body: LLMCheckIn,
    admin: AdminUser,
    llm: Annotated[LLMRouter, Depends(get_llm)],
    guard: Annotated[UsageGuard, Depends(get_usage_guard)],
) -> dict[str, Any]:
    """Send a tiny prompt through the router (counts against the admin's quota)."""
    system = "You are a health check. Answer in at most five words.\n\n" + GUARD_RULES
    async with guard.request(admin, body.prompt, purpose="admin_check") as ticket:
        try:
            result = await llm.complete(
                [Message("system", system), Message("user", body.prompt)], max_tokens=20
            )
        except LLMError as e:
            raise AppError("llm_unavailable", f"The model call failed: {e}", 502) from e
        await ticket.record(result)
    checked = check_output(result.text, system)
    return {
        "ok": True,
        "provider": result.provider,
        "model": result.model,
        "fallback_used": result.fallback_used,
        "attempts": result.attempts,
        "latency_ms": result.latency_ms,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "est_cost_usd": result.est_cost_usd,
        "text": checked.text[:300],
        "providers": llm.status(),
    }
