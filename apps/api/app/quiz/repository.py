"""Questions, quiz sessions and answers (Postgres). Every query is scoped by user id."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import concepts, mastery, questions, quiz_answers, quiz_sessions
from app.quiz.grading import QuestionData


class QuizRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------------------------------------------------------------- questions
    async def questions(
        self,
        subject_id: str,
        *,
        concept_ids: Iterable[str] | None = None,
        ids: Iterable[str] | None = None,
        types: Iterable[str] | None = None,
    ) -> list[QuestionData]:
        q = select(questions).where(
            questions.c.subject_id == subject_id, questions.c.status == "active"
        )
        if concept_ids is not None:
            q = q.where(questions.c.concept_id.in_(list(concept_ids)))
        if ids is not None:
            q = q.where(questions.c.id.in_(list(ids)))
        if types is not None:
            q = q.where(questions.c.type.in_(list(types)))
        rows = await self.session.execute(q.order_by(questions.c.id))
        return [QuestionData.from_row(dict(r._mapping)) for r in rows]

    async def questions_by_id(self, ids: Iterable[str]) -> dict[str, QuestionData]:
        wanted = list(ids)
        if not wanted:
            return {}
        rows = await self.session.execute(select(questions).where(questions.c.id.in_(wanted)))
        return {r.id: QuestionData.from_row(dict(r._mapping)) for r in rows}

    async def recently_seen(self, user_id: uuid.UUID, days: int) -> set[str]:
        since = dt.datetime.now(dt.UTC) - dt.timedelta(days=days)
        rows = await self.session.execute(
            select(quiz_answers.c.question_id).where(
                quiz_answers.c.user_id == user_id, quiz_answers.c.created_at >= since
            )
        )
        return {r[0] for r in rows}

    async def concept_rows(self, subject_id: str) -> list[dict[str, Any]]:
        rows = await self.session.execute(
            select(concepts.c.id, concepts.c.name, concepts.c.cluster, concepts.c.order_index)
            .where(concepts.c.subject_id == subject_id)
            .order_by(concepts.c.order_index)
        )
        return [dict(r._mapping) for r in rows]

    async def concept_names(self, ids: Iterable[str]) -> dict[str, str]:
        wanted = [i for i in ids if i]
        if not wanted:
            return {}
        rows = await self.session.execute(
            select(concepts.c.id, concepts.c.name).where(concepts.c.id.in_(wanted))
        )
        return {r.id: r.name for r in rows}

    async def due_concepts(
        self, user_id: uuid.UUID, subject_id: str, now: dt.datetime
    ) -> list[str]:
        rows = await self.session.execute(
            select(mastery.c.concept_id)
            .where(
                mastery.c.user_id == user_id,
                mastery.c.subject_id == subject_id,
                mastery.c.next_review_at.is_not(None),
                mastery.c.next_review_at <= now,
            )
            .order_by(mastery.c.next_review_at)
        )
        return [r[0] for r in rows]

    # ---------------------------------------------------------------- sessions
    async def create_session(self, **values: Any) -> dict[str, Any]:
        row = (
            await self.session.execute(
                insert(quiz_sessions).values(**values).returning(quiz_sessions)
            )
        ).one()
        return dict(row._mapping)

    async def get_session(
        self, user_id: uuid.UUID, session_id: uuid.UUID, *, lock: bool = False
    ) -> dict[str, Any] | None:
        q = select(quiz_sessions).where(
            quiz_sessions.c.id == session_id, quiz_sessions.c.user_id == user_id
        )
        if lock:
            q = q.with_for_update()
        row = (await self.session.execute(q)).first()
        return dict(row._mapping) if row else None

    async def finish_session(
        self, session_id: uuid.UUID, score: float, max_score: float, at: dt.datetime
    ) -> None:
        await self.session.execute(
            update(quiz_sessions)
            .where(quiz_sessions.c.id == session_id)
            .values(submitted_at=at, score=score, max_score=max_score, updated_at=at)
        )

    async def set_score(self, session_id: uuid.UUID, score: float) -> None:
        await self.session.execute(
            update(quiz_sessions).where(quiz_sessions.c.id == session_id).values(score=score)
        )

    async def history(
        self, user_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        cond = (quiz_sessions.c.user_id == user_id) & quiz_sessions.c.submitted_at.is_not(None)
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(quiz_sessions).where(cond)
                )
            ).scalar_one()
        )
        rows = await self.session.execute(
            select(quiz_sessions, concepts.c.name.label("concept_name"))
            .select_from(
                quiz_sessions.outerjoin(concepts, concepts.c.id == quiz_sessions.c.concept_id)
            )
            .where(cond)
            .order_by(quiz_sessions.c.submitted_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [dict(r._mapping) for r in rows], total

    # ---------------------------------------------------------------- answers
    async def answers(self, session_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = await self.session.execute(
            select(quiz_answers).where(quiz_answers.c.session_id == session_id)
        )
        return [dict(r._mapping) for r in rows]

    async def save_answer(self, **values: Any) -> dict[str, Any]:
        """Insert or replace the answer to one question of a session."""
        stmt = pg_insert(quiz_answers).values(**values)
        update_cols = {k: v for k, v in values.items() if k not in ("session_id", "question_id")}
        row = (
            await self.session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[quiz_answers.c.session_id, quiz_answers.c.question_id],
                    set_=update_cols,
                ).returning(quiz_answers)
            )
        ).one()
        return dict(row._mapping)
