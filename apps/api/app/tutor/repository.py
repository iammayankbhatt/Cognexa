"""Chat threads and messages (Postgres), plus the student's mastery map for personalisation.

Every query is scoped by user id: a student can only ever see or change their own threads.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import and_, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import chat_messages, chat_threads, mastery, message_feedback
from app.llm.types import Message


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------------------------------------------------------------- threads
    async def create_thread(
        self, user_id: uuid.UUID, subject_id: str, title: str
    ) -> dict[str, Any]:
        row = (
            await self.session.execute(
                insert(chat_threads)
                .values(user_id=user_id, subject_id=subject_id, title=title)
                .returning(chat_threads)
            )
        ).one()
        return dict(row._mapping)

    async def get_thread(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> dict[str, Any] | None:
        row = (
            await self.session.execute(
                select(chat_threads).where(
                    chat_threads.c.id == thread_id, chat_threads.c.user_id == user_id
                )
            )
        ).first()
        return dict(row._mapping) if row else None

    async def list_threads(
        self,
        user_id: uuid.UUID,
        *,
        archived: bool = False,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        cond = and_(chat_threads.c.user_id == user_id, chat_threads.c.archived.is_(archived))
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            cond = and_(cond, chat_threads.c.title.ilike(f"%{escaped}%", escape="\\"))
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(chat_threads).where(cond)
                )
            ).scalar_one()
        )
        last = (
            select(func.max(chat_messages.c.created_at))
            .where(chat_messages.c.thread_id == chat_threads.c.id)
            .scalar_subquery()
        )
        count = (
            select(func.count())
            .select_from(chat_messages)
            .where(
                chat_messages.c.thread_id == chat_threads.c.id,
                chat_messages.c.superseded_at.is_(None),
            )
            .scalar_subquery()
        )
        rows = await self.session.execute(
            select(chat_threads, last.label("last_message_at"), count.label("message_count"))
            .where(cond)
            .order_by(chat_threads.c.updated_at.desc(), chat_threads.c.id)
            .limit(limit)
            .offset(offset)
        )
        return [dict(r._mapping) for r in rows], total

    async def update_thread(
        self, user_id: uuid.UUID, thread_id: uuid.UUID, **values: Any
    ) -> dict[str, Any] | None:
        row = (
            await self.session.execute(
                update(chat_threads)
                .where(chat_threads.c.id == thread_id, chat_threads.c.user_id == user_id)
                .values(**values)
                .returning(chat_threads)
            )
        ).first()
        return dict(row._mapping) if row else None

    async def touch_thread(self, thread_id: uuid.UUID) -> None:
        await self.session.execute(
            update(chat_threads).where(chat_threads.c.id == thread_id).values(updated_at=_now())
        )

    async def delete_thread(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            delete(chat_threads)
            .where(chat_threads.c.id == thread_id, chat_threads.c.user_id == user_id)
            .returning(chat_threads.c.id)
        )
        return result.first() is not None

    # ---------------------------------------------------------------- messages
    async def add_message(self, **values: Any) -> dict[str, Any]:
        row = (
            await self.session.execute(
                insert(chat_messages).values(**values).returning(chat_messages)
            )
        ).one()
        return dict(row._mapping)

    async def get_message(self, user_id: uuid.UUID, message_id: uuid.UUID) -> dict[str, Any] | None:
        row = (
            await self.session.execute(
                select(chat_messages).where(
                    chat_messages.c.id == message_id, chat_messages.c.user_id == user_id
                )
            )
        ).first()
        return dict(row._mapping) if row else None

    async def list_messages(self, thread_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = await self.session.execute(
            select(chat_messages)
            .where(chat_messages.c.thread_id == thread_id, chat_messages.c.superseded_at.is_(None))
            .order_by(chat_messages.c.created_at, chat_messages.c.id)
        )
        return [dict(r._mapping) for r in rows]

    async def supersede(self, message_id: uuid.UUID) -> None:
        await self.session.execute(
            update(chat_messages)
            .where(chat_messages.c.id == message_id)
            .values(superseded_at=_now())
        )

    async def history(
        self, thread_id: uuid.UUID, turns: int, before: dt.datetime | None = None
    ) -> list[Message]:
        """The last `turns` user/assistant exchanges (2 messages each), oldest first."""
        cond = and_(
            chat_messages.c.thread_id == thread_id,
            chat_messages.c.superseded_at.is_(None),
            chat_messages.c.role.in_(["user", "assistant"]),
        )
        if before is not None:
            cond = and_(cond, chat_messages.c.created_at < before)
        rows = (
            await self.session.execute(
                select(chat_messages.c.role, chat_messages.c.content)
                .where(cond)
                .order_by(chat_messages.c.created_at.desc(), chat_messages.c.id.desc())
                .limit(max(0, turns) * 2)
            )
        ).all()
        return [
            Message("assistant" if r.role == "assistant" else "user", r.content)
            for r in reversed(rows)
        ]

    async def last_assistant(
        self, thread_id: uuid.UUID, before: dt.datetime | None = None
    ) -> dict[str, Any] | None:
        cond = and_(
            chat_messages.c.thread_id == thread_id,
            chat_messages.c.superseded_at.is_(None),
            chat_messages.c.role == "assistant",
        )
        if before is not None:
            cond = and_(cond, chat_messages.c.created_at < before)
        row = (
            await self.session.execute(
                select(chat_messages)
                .where(cond)
                .order_by(chat_messages.c.created_at.desc(), chat_messages.c.id.desc())
                .limit(1)
            )
        ).first()
        return dict(row._mapping) if row else None

    async def supersede_turn(self, user_message_id: uuid.UUID) -> None:
        """Hide a user message and every answer to it (edit-and-resend)."""
        await self.session.execute(
            update(chat_messages)
            .where(
                (chat_messages.c.id == user_message_id)
                | (chat_messages.c.reply_to == user_message_id),
                chat_messages.c.superseded_at.is_(None),
            )
            .values(superseded_at=_now())
        )

    async def last_user_message(self, thread_id: uuid.UUID) -> dict[str, Any] | None:
        row = (
            await self.session.execute(
                select(chat_messages)
                .where(
                    chat_messages.c.thread_id == thread_id,
                    chat_messages.c.superseded_at.is_(None),
                    chat_messages.c.role == "user",
                )
                .order_by(chat_messages.c.created_at.desc(), chat_messages.c.id.desc())
                .limit(1)
            )
        ).first()
        return dict(row._mapping) if row else None

    # ---------------------------------------------------------------- feedback
    async def upsert_feedback(
        self, message_id: uuid.UUID, user_id: uuid.UUID, values: dict[str, Any]
    ) -> dict[str, Any]:
        """One feedback row per (message, user); only the given fields change."""
        base = pg_insert(message_feedback).values(message_id=message_id, user_id=user_id, **values)
        stmt = base.on_conflict_do_update(
            index_elements=[message_feedback.c.message_id, message_feedback.c.user_id],
            set_={**values, "updated_at": func.now()},
        ).returning(message_feedback)
        row = (await self.session.execute(stmt)).one()
        return dict(row._mapping)

    async def feedback_for_thread(
        self, user_id: uuid.UUID, thread_id: uuid.UUID
    ) -> dict[uuid.UUID, dict[str, Any]]:
        rows = await self.session.execute(
            select(
                message_feedback.c.message_id,
                message_feedback.c.rating,
                message_feedback.c.report_reason,
            )
            .join(chat_messages, chat_messages.c.id == message_feedback.c.message_id)
            .where(message_feedback.c.user_id == user_id, chat_messages.c.thread_id == thread_id)
        )
        return {
            r.message_id: {"rating": r.rating, "reported": r.report_reason is not None}
            for r in rows
        }

    # ---------------------------------------------------------------- mastery
    async def mastery_map(self, user_id: uuid.UUID, subject_id: str) -> dict[str, float]:
        """Scores of practised concepts (attempts > 0); a missing id means never practised."""
        rows = await self.session.execute(
            select(mastery.c.concept_id, mastery.c.score).where(
                mastery.c.user_id == user_id,
                mastery.c.subject_id == subject_id,
                mastery.c.attempts > 0,
            )
        )
        return {r.concept_id: float(r.score) for r in rows}
