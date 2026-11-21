"""The signed-in user's own profile, usage, data export and account deletion."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.admin import AuthAdminError, admin_api_configured, delete_auth_user
from app.auth.deps import CurrentUser, ProfileCache, get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.flags import get_flags
from app.core.ratelimit import limit_by_user
from app.db.profiles import ProfileRepository
from app.db.repositories import AppSettingsRepository
from app.db.session import get_session
from app.llm.deps import get_usage_guard
from app.usage.guard import UsageGuard, load_limits

router = APIRouter(tags=["me"])

Theme = Literal["neon-noir", "titanium-dark", "titanium-light"]
Experience = Literal["beginner", "intermediate", "advanced"]


class Usage(BaseModel):
    date: dt.date
    ai_requests: int
    tokens_in: int
    tokens_out: int
    daily_quota: int


class UsageDay(BaseModel):
    date: dt.date
    ai_requests: int
    tokens_in: int
    tokens_out: int
    est_cost_usd: float


class UsageToday(UsageDay):
    remaining: int
    resets_at: dt.datetime


class UsageLimits(BaseModel):
    daily_ai_requests: int
    per_minute: int
    max_input_chars: int
    max_output_tokens: int


class UsageOut(BaseModel):
    today: UsageToday
    limits: UsageLimits
    history: list[UsageDay]


class MeOut(BaseModel):
    id: str
    email: str | None
    display_name: str | None
    role: str
    theme: str
    study_group: str
    onboarding_completed: bool
    experience_level: str | None
    created_at: dt.datetime | None
    usage: Usage
    # tutor modes this user may chat in (plain_rag: reviewers/admins, or students when the
    # PLAIN_RAG_VISIBLE_TO_STUDENTS flag is on); the web shows a mode switch only if > 1 (BUG-057)
    tutor_modes: list[Literal["graphrag", "plain_rag"]]


class MePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    theme: Theme | None = None


class OnboardingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    experience_level: Experience


class DeleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: Literal["DELETE"]


def _utc_today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


async def build_me(
    session: AsyncSession, user: CurrentUser, profile: dict[str, Any], settings: Settings
) -> MeOut:
    repo = ProfileRepository(session)
    today = _utc_today()
    usage = await repo.usage_today(user.id, today)
    fresh = CurrentUser(id=user.id, email=user.email, role=str(profile["role"]), profile=profile)
    quota = (await load_limits(AppSettingsRepository(session), fresh)).daily
    role = str(profile["role"])
    plain = (
        role != "student" or (await get_flags(session, settings))["PLAIN_RAG_VISIBLE_TO_STUDENTS"]
    )
    return MeOut(
        id=str(user.id),
        email=user.email,
        display_name=profile.get("display_name"),
        role=role,
        theme=str(profile["theme"]),
        study_group=str(profile["study_group"]),
        onboarding_completed=bool(profile["onboarding_completed"]),
        experience_level=profile.get("experience_level"),
        created_at=profile.get("created_at"),
        usage=Usage(date=today, daily_quota=quota, **usage),
        tutor_modes=["graphrag", "plain_rag"] if plain else ["graphrag"],
    )


def _cache(request: Request) -> ProfileCache:
    cache: ProfileCache = request.app.state.profile_cache
    return cache


@router.get("/me/usage", response_model=UsageOut)
async def get_my_usage(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    guard: Annotated[UsageGuard, Depends(get_usage_guard)],
) -> UsageOut:
    """Today's usage with limits and reset time, plus the last 30 days."""
    return UsageOut.model_validate(await guard.usage_summary(user, days=30))


@router.get("/me", response_model=MeOut)
async def get_me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MeOut:
    profile = await ProfileRepository(session).get(user.id) or user.profile
    return await build_me(session, user, profile, settings)


@router.patch("/me", response_model=MeOut)
async def patch_me(
    body: MePatch,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MeOut:
    changes = body.model_dump(exclude_none=True)
    if "display_name" in changes:
        changes["display_name"] = changes["display_name"].strip()
        if not changes["display_name"]:
            raise AppError("validation_error", "display_name: must not be blank", 422)
    repo = ProfileRepository(session)
    await repo.update_self(user.id, changes)
    await session.commit()
    _cache(request).invalidate(user.id)
    profile = await repo.get(user.id) or user.profile
    return await build_me(session, user, profile, settings)


@router.post("/me/onboarding-complete", response_model=MeOut)
async def complete_onboarding(
    body: OnboardingIn,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MeOut:
    repo = ProfileRepository(session)
    await repo.update_self(
        user.id, {"experience_level": body.experience_level, "onboarding_completed": True}
    )
    await session.commit()
    _cache(request).invalidate(user.id)
    profile = await repo.get(user.id) or user.profile
    return await build_me(session, user, profile, settings)


@router.get("/me/export", dependencies=[Depends(limit_by_user("me_export"))])
async def export_me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    data = await ProfileRepository(session).export(user.id)
    return {
        "exported_at": dt.datetime.now(dt.UTC).isoformat(),
        "user": {"id": str(user.id), "email": user.email},
        "data": data,
    }


@router.delete("/me")
async def delete_me(
    body: DeleteIn,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, str]:
    """Delete the account. Removing the auth user cascades to the profile and every user row."""
    repo = ProfileRepository(session)
    await repo.audit(None, "user.delete_account", str(user.id), {"by": "self"})
    if admin_api_configured(settings):
        await session.commit()  # keep the audit entry even though the actor row disappears
        try:
            await delete_auth_user(settings, user.id)
        except AuthAdminError as exc:
            raise AppError(
                "delete_failed", "Could not delete the account. Try again.", 502
            ) from exc
    else:
        await repo.delete_auth_user_sql(user.id)
        await session.commit()
    _cache(request).invalidate(user.id)
    return {"status": "deleted"}
