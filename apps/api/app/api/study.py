"""User-study endpoints: the student's study status, consent, withdrawal; admin controls and the
anonymised CSV export."""

from __future__ import annotations

import csv
import datetime as dt
import io
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from app.auth.deps import CurrentUser, ProfileCache, get_current_user, require_role
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.flags import get_flags
from app.core.ratelimit import limit_by_user
from app.db.repositories import AppSettingsRepository
from app.db.session import Database, get_database
from app.db.tables import audit_log, profiles, study_settings
from app.study import service

router = APIRouter(tags=["study"])
User = Annotated[CurrentUser, Depends(get_current_user)]
Admin = Annotated[CurrentUser, Depends(require_role("admin"))]
DB = Annotated[Database, Depends(get_database)]


async def _profile(session: Any, user_id: Any) -> dict[str, Any]:
    row = (await session.execute(select(profiles).where(profiles.c.id == user_id))).first()
    if row is None:
        raise AppError("not_found", "Profile not found.", 404)
    return dict(row._mapping)


@router.get("/study/me")
async def my_study(
    user: User, db: DB, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, Any]:
    async with db.sessions()() as session:
        flags = await get_flags(session, settings)
        return await service.study_state(
            session, await _profile(session, user.id), bool(flags.get("STUDY_MODE"))
        )


def _drop_cached_profile(request: Request, user: CurrentUser) -> None:
    cache: ProfileCache = request.app.state.profile_cache
    cache.invalidate(user.id)  # the study group is part of the cached profile


@router.post("/study/consent")
async def give_consent(
    request: Request, user: User, db: DB, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, Any]:
    async with db.sessions()() as session, session.begin():
        flags = await get_flags(session, settings)
        if not flags.get("STUDY_MODE"):
            raise AppError("study_off", "The study is not running.", 409)
        if user.role != "student":
            raise AppError("forbidden", "Only students take part in the study.", 403)
        await service.consent(session, user.id)
    _drop_cached_profile(request, user)
    return await my_study(user, db, settings)


@router.post("/study/withdraw")
async def withdraw(
    request: Request, user: User, db: DB, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, Any]:
    async with db.sessions()() as session, session.begin():
        await service.withdraw(session, user.id)
    _drop_cached_profile(request, user)
    return await my_study(user, db, settings)


# ---------------------------------------------------------------- admin


class StudyPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    assignment: Literal["random", "alternate"] | None = None
    posttest_unlock_at: dt.datetime | None = None
    clear_unlock_date: bool = False
    posttest_after_days: int | None = Field(default=None, ge=0, le=365)
    pretest_minutes: int | None = Field(default=None, ge=5, le=120)


async def _admin_view(session: Any, settings: Settings) -> dict[str, Any]:
    s = await service.load_settings(session)
    flags = await get_flags(session, settings)
    return {
        "enabled": bool(flags.get("STUDY_MODE")),
        "assignment": str(s["assignment"]),
        "posttest_unlock_at": s.get("posttest_unlock_at"),
        "posttest_after_days": s.get("posttest_after_days"),
        "pretest_minutes": s.get("pretest_minutes"),
        "started_at": s.get("started_at"),
        "funnel": await service.funnel(session),
    }


@router.get("/admin/study")
async def admin_study(
    _: Admin, db: DB, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, Any]:
    async with db.sessions()() as session:
        return await _admin_view(session, settings)


@router.put("/admin/study")
async def update_study(
    body: StudyPatch, admin: Admin, db: DB, settings: Annotated[Settings, Depends(get_settings)]
) -> dict[str, Any]:
    values: dict[str, Any] = body.model_dump(
        exclude_none=True, exclude={"enabled", "clear_unlock_date"}
    )
    if body.clear_unlock_date:
        values["posttest_unlock_at"] = None
    async with db.sessions()() as session, session.begin():
        if body.enabled is not None:
            values["enabled"] = body.enabled
            repo = AppSettingsRepository(session)
            features = await repo.get("features") or {}
            await repo.set("features", {**features, "STUDY_MODE": body.enabled})
            current = await service.load_settings(session)
            if body.enabled and not current.get("started_at"):
                values["started_at"] = dt.datetime.now(dt.UTC)
        if values:
            await session.execute(
                update(study_settings).where(study_settings.c.id == 1).values(**values)
            )
        await session.execute(
            audit_log.insert().values(
                actor=admin.id,
                action="study.update",
                target="study_settings",
                details=body.model_dump(mode="json", exclude_none=True),
            )
        )
    async with db.sessions()() as session:
        return await _admin_view(session, settings)


@router.get("/admin/study/export.csv", dependencies=[Depends(limit_by_user("admin_export"))])
async def export_csv(_: Admin, db: DB) -> Response:
    """Anonymised participant table: salted hash ids, no names or emails."""
    async with db.sessions()() as session:
        rows = await service.export_rows(session)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=service.EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow({k: ("" if v is None else v) for k, v in r.items()})
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
    return Response(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="cognexa-study-{stamp}.csv"'},
    )
