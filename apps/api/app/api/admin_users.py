"""Admin user management. Every change is written to audit_log."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, ProfileCache, require_role
from app.core.errors import AppError
from app.db.profiles import ProfileRepository
from app.db.session import get_session

router = APIRouter(prefix="/admin", tags=["admin"])

AdminUser = Annotated[CurrentUser, Depends(require_role("admin"))]


class UserOut(BaseModel):
    id: str
    email: str | None
    display_name: str | None
    role: str
    theme: str
    study_group: str
    onboarding_completed: bool
    experience_level: str | None
    quota_override: dict[str, Any] | None
    disabled_at: dt.datetime | None = None
    created_at: dt.datetime | None


class UserPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class QuotaOverride(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_ai_requests: int = Field(ge=0, le=10000)
    per_minute: int | None = Field(default=None, ge=0, le=1000)


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["student", "reviewer", "admin"] | None = None
    study_group: Literal["adaptive", "baseline", "none"] | None = None
    quota_override: QuotaOverride | None = None
    clear_quota_override: bool = False
    disabled: bool | None = None  # true: every API call is refused; false: re-enabled

    @field_validator("clear_quota_override")
    @classmethod
    def _not_both(cls, v: bool, info: Any) -> bool:
        if v and info.data.get("quota_override") is not None:
            raise ValueError("send either quota_override or clear_quota_override, not both")
        return v


def _out(row: dict[str, Any]) -> UserOut:
    return UserOut(
        id=str(row["id"]),
        email=row.get("email"),
        display_name=row.get("display_name"),
        role=str(row["role"]),
        theme=str(row["theme"]),
        study_group=str(row["study_group"]),
        onboarding_completed=bool(row["onboarding_completed"]),
        experience_level=row.get("experience_level"),
        quota_override=row.get("quota_override"),
        disabled_at=row.get("disabled_at"),
        created_at=row.get("created_at"),
    )


@router.get("/users", response_model=UserPage)
async def list_users(
    _: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    page: Annotated[int, Query(ge=1, le=10000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> UserPage:
    rows, total = await ProfileRepository(session).list_users(
        q.strip() if q and q.strip() else None, page_size, (page - 1) * page_size
    )
    return UserPage(items=[_out(r) for r in rows], total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserPatch,
    request: Request,
    admin: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserOut:
    changes: dict[str, Any] = {}
    if body.role is not None:
        if user_id == admin.id and body.role != "admin":
            raise AppError("forbidden", "Admins cannot remove their own admin role.", 403)
        changes["role"] = body.role
    if body.study_group is not None:
        changes["study_group"] = body.study_group
    if body.quota_override is not None:
        changes["quota_override"] = body.quota_override.model_dump(exclude_none=True)
    elif body.clear_quota_override:
        changes["quota_override"] = None
    if body.disabled is not None:
        if user_id == admin.id and body.disabled:
            raise AppError("forbidden", "Admins cannot disable their own account.", 403)
        changes["disabled_at"] = dt.datetime.now(dt.UTC) if body.disabled else None
    if not changes:
        raise AppError("validation_error", "Nothing to change.", 422)

    repo = ProfileRepository(session)
    updated = await repo.admin_update(admin.id, user_id, changes)
    if updated is None:
        raise AppError("not_found", "User not found.", 404)
    await session.commit()
    cache: ProfileCache = request.app.state.profile_cache
    cache.invalidate(user_id)
    return _out({**updated, "email": await repo.email_for(user_id)})
