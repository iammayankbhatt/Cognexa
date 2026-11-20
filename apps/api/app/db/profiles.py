"""Profiles, per-user usage and the admin user list (Phase 4)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import Column, MetaData, Table, Text, func, insert, or_, select, text, update
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import (
    audit_log,
    chat_messages,
    chat_threads,
    mastery,
    message_feedback,
    notes,
    profiles,
    quiz_answers,
    quiz_sessions,
    recommendations_log,
    revision_sheets,
    usage_daily,
)

PROFILE_FIELDS = (
    "id",
    "display_name",
    "role",
    "theme",
    "study_group",
    "onboarding_completed",
    "experience_level",
    "quota_override",
    "disabled_at",
    "created_at",
)

# Read-only view of Supabase's auth.users (owned by Supabase Auth; never written from here).
auth_users = Table(
    "users",
    MetaData(),
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("email", Text),
    schema="auth",
)

# Every table that holds a user's own rows, with the column that names the user.
USER_TABLES: list[tuple[Table, str]] = [
    (quiz_sessions, "user_id"),
    (quiz_answers, "user_id"),
    (mastery, "user_id"),
    (chat_threads, "user_id"),
    (message_feedback, "user_id"),
    (usage_daily, "user_id"),
    (notes, "user_id"),
    (revision_sheets, "user_id"),
    (recommendations_log, "user_id"),
]


def _row(mapping: Any) -> dict[str, Any]:
    return {k: mapping[k] for k in mapping.keys()}  # noqa: SIM118 (RowMapping, not dict)


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, user_id: uuid.UUID) -> dict[str, Any] | None:
        cols = [profiles.c[f] for f in PROFILE_FIELDS]
        row = (await self._s.execute(select(*cols).where(profiles.c.id == user_id))).mappings()
        first = row.first()
        return _row(first) if first else None

    async def ensure(self, user_id: uuid.UUID) -> dict[str, Any] | None:
        """Return the profile, creating it if the signup trigger has not (yet) done so.

        Returns None when no auth user with this id exists (the foreign key rejects the insert).
        """
        found = await self.get(user_id)
        if found:
            return found
        try:
            async with self._s.begin_nested():
                await self._s.execute(
                    pg_insert(profiles)
                    .values(id=user_id)
                    .on_conflict_do_nothing(index_elements=[profiles.c.id])
                )
        except IntegrityError:
            return None
        return await self.get(user_id)

    async def update_self(self, user_id: uuid.UUID, changes: dict[str, Any]) -> None:
        allowed = {"display_name", "theme", "experience_level", "onboarding_completed"}
        values = {k: v for k, v in changes.items() if k in allowed}
        if values:
            await self._s.execute(update(profiles).where(profiles.c.id == user_id).values(**values))

    async def usage_today(self, user_id: uuid.UUID, today: dt.date) -> dict[str, int]:
        row = (
            await self._s.execute(
                select(
                    usage_daily.c.ai_requests, usage_daily.c.tokens_in, usage_daily.c.tokens_out
                ).where(usage_daily.c.user_id == user_id, usage_daily.c.date == today)
            )
        ).first()
        if row is None:
            return {"ai_requests": 0, "tokens_in": 0, "tokens_out": 0}
        return {"ai_requests": row[0], "tokens_in": int(row[1]), "tokens_out": int(row[2])}

    # ------------------------------------------------------------------ admin
    async def list_users(
        self, query: str | None, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        cond = []
        if query:
            like = f"%{query}%"
            cond.append(or_(profiles.c.display_name.ilike(like), auth_users.c.email.ilike(like)))
        base = select(*[profiles.c[f] for f in PROFILE_FIELDS], auth_users.c.email).select_from(
            profiles.join(auth_users, auth_users.c.id == profiles.c.id)
        )
        if cond:
            base = base.where(*cond)
        total = (
            await self._s.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            await self._s.execute(
                base.order_by(profiles.c.created_at.desc()).limit(limit).offset(offset)
            )
        ).mappings()
        return [_row(r) for r in rows], int(total)

    async def email_for(self, user_id: uuid.UUID) -> str | None:
        found = await self._s.execute(select(auth_users.c.email).where(auth_users.c.id == user_id))
        return found.scalar_one_or_none()

    async def admin_update(
        self, actor: uuid.UUID | None, target: uuid.UUID, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        allowed = {"role", "quota_override", "study_group", "disabled_at"}
        values = {k: v for k, v in changes.items() if k in allowed}
        before = await self.get(target)
        if before is None:
            return None
        if values:
            await self._s.execute(update(profiles).where(profiles.c.id == target).values(**values))
            await self.audit(
                actor,
                "admin.update_user",
                str(target),
                {
                    k: {"from": _jsonable(before.get(k)), "to": _jsonable(v)}
                    for k, v in values.items()
                },
            )
        return await self.get(target)

    async def audit(
        self, actor: uuid.UUID | None, action: str, target: str | None, details: dict[str, Any]
    ) -> None:
        await self._s.execute(
            insert(audit_log).values(actor=actor, action=action, target=target, details=details)
        )

    # ------------------------------------------------------------------ data rights
    async def export(self, user_id: uuid.UUID) -> dict[str, Any]:
        out: dict[str, Any] = {"profile": _jsonable(await self.get(user_id))}
        for table, col in USER_TABLES:
            rows = (await self._s.execute(select(table).where(table.c[col] == user_id))).mappings()
            out[table.name] = [_jsonable(_row(r)) for r in rows]
        thread_ids = [t["id"] for t in out.get("chat_threads", [])]
        if thread_ids:
            rows = (
                await self._s.execute(
                    select(chat_messages).where(chat_messages.c.thread_id.in_(thread_ids))
                )
            ).mappings()
            out["chat_messages"] = [_jsonable(_row(r)) for r in rows]
        else:
            out["chat_messages"] = []
        return out

    async def delete_auth_user_sql(self, user_id: uuid.UUID) -> bool:
        """Delete the auth user directly (plain Postgres / tests). Cascades to every user row.

        On Supabase the backend uses the Auth admin API instead (see app.auth.admin)."""
        result = await self._s.execute(
            text("delete from auth.users where id = :id"), {"id": user_id}
        )
        return bool(getattr(result, "rowcount", 0))


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    if hasattr(value, "__float__") and not isinstance(value, bool | int | float):
        return float(value)
    return value
