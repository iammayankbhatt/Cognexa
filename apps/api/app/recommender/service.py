"""Recommendations for one student: gather the learner state, route by study group, log.

Group routing (user study, Objective 5): with STUDY_MODE on, students in the `baseline` group get
the non-adaptive syllabus order everywhere; everyone else gets the rule engine. Every
recommendation shown is logged in recommendations_log (shown / clicked / completed), which the
study analysis reads. A recommendation shown again within REUSE_HOURS reuses its log row, so
reloading a page does not inflate the counts.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser
from app.core.config import Settings
from app.core.flags import get_flags
from app.db.session import Database
from app.db.tables import (
    concept_interest,
    questions,
    quiz_answers,
    quiz_sessions,
    recommendations_log,
)
from app.mastery.model import MasteryParams
from app.mastery.repository import MasteryRepository
from app.recommender.engine import (
    ConceptInfo,
    Graph,
    LearnerState,
    Recommendation,
    baseline,
    completed_concepts,
    recommend,
)
from app.tutor.suggest import SyllabusGraph

REUSE_HOURS = 12
ASKED_WINDOW_DAYS = 7
FAILURE_SCORE = 0.5


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


async def build_graph(graph: SyllabusGraph, subject_id: str) -> Graph:
    concepts = [
        ConceptInfo(c.id, c.name, c.order_index)
        for c in await graph.list_concepts(subject_id)
        if c.status == "approved"
    ]
    edges = [
        (e.source, e.target)
        for e in await graph.list_edges(subject_id)
        if e.type == "PREREQUISITE_OF" and e.status == "approved"
    ]
    return Graph(concepts, edges)


async def learner_state(
    session: AsyncSession,
    user_id: uuid.UUID,
    subject_id: str,
    params: MasteryParams,
    now: dt.datetime,
) -> LearnerState:
    view = await MasteryRepository(session, params).view(user_id, subject_id, now)
    practised = [m for m in view if m["attempts"] > 0]
    due = sorted(
        (m for m in view if m["next_review_at"] is not None and m["next_review_at"] <= now),
        key=lambda m: m["next_review_at"],
    )
    asked = await session.execute(
        select(concept_interest.c.concept_id, func.count())
        .where(
            concept_interest.c.user_id == user_id,
            concept_interest.c.subject_id == subject_id,
            concept_interest.c.asked_at >= now - dt.timedelta(days=ASKED_WINDOW_DAYS),
        )
        .group_by(concept_interest.c.concept_id)
    )
    failures = await session.execute(
        select(questions.c.concept_id, func.max(quiz_answers.c.created_at))
        .select_from(quiz_answers.join(questions, questions.c.id == quiz_answers.c.question_id))
        .where(
            quiz_answers.c.user_id == user_id,
            quiz_answers.c.score.is_not(None),
            quiz_answers.c.score < FAILURE_SCORE,
        )
        .group_by(questions.c.concept_id)
    )
    concept_quizzes = await session.execute(
        select(
            quiz_sessions.c.concept_id, func.max(quiz_sessions.c.score / quiz_sessions.c.max_score)
        )
        .where(
            quiz_sessions.c.user_id == user_id,
            quiz_sessions.c.subject_id == subject_id,
            quiz_sessions.c.mode == "concept",
            quiz_sessions.c.concept_id.is_not(None),
            quiz_sessions.c.submitted_at.is_not(None),
            quiz_sessions.c.max_score > 0,
        )
        .group_by(quiz_sessions.c.concept_id)
    )
    return LearnerState(
        effective={m["concept_id"]: m["effective"] for m in practised},
        attempts={m["concept_id"]: m["attempts"] for m in practised},
        due=[m["concept_id"] for m in due],
        asked_7d={r[0]: int(r[1]) for r in asked},
        last_failure={r[0]: r[1] for r in failures},
        completed=completed_concepts({r[0]: float(r[1]) for r in concept_quizzes}),
    )


def group_for(user: CurrentUser, flags: dict[str, bool]) -> tuple[str, str]:
    """(study group, engine): baseline only when STUDY_MODE is on and the student is in it."""
    group = str(user.profile.get("study_group") or "none")
    engine = "baseline" if flags.get("STUDY_MODE") and group == "baseline" else "adaptive"
    return group, engine


def serialise(
    rec: Recommendation, log_id: uuid.UUID | None, names: dict[str, str] | None = None
) -> dict[str, Any]:
    ids = {c for edge in rec.path for c in edge}
    return {
        "id": str(log_id) if log_id else None,
        "concept_id": rec.concept_id,
        "name": rec.name,
        "rule": rec.rule,
        "reason": rec.reason,
        "action": rec.action,
        "path": [{"source": a, "target": b} for a, b in rec.path],
        "names": {c: (names or {}).get(c, c) for c in sorted(ids)},
    }


class RecommenderService:
    def __init__(self, db: Database, settings: Settings, graph: SyllabusGraph) -> None:
        self.db = db
        self.settings = settings
        self.graph = graph
        self.params = MasteryParams.from_settings(settings)
        self._names: dict[str, str] = {}

    async def compute(
        self, user: CurrentUser, subject_id: str, limit: int = 3, now: dt.datetime | None = None
    ) -> tuple[str, str, list[Recommendation]]:
        now = now or _now()
        graph = await build_graph(self.graph, subject_id)
        self._names = {cid: c.name for cid, c in graph.concepts.items()}
        async with self.db.sessions()() as session:
            flags = await get_flags(session, self.settings)
            state = await learner_state(session, user.id, subject_id, self.params, now)
        group, engine = group_for(user, flags)
        recs = (
            baseline(graph, state, limit)
            if engine == "baseline"
            else recommend(graph, state, limit)
        )
        return group, engine, recs

    async def for_user(
        self,
        user: CurrentUser,
        subject_id: str,
        *,
        surface: str = "dashboard",
        limit: int = 3,
        log: bool = True,
    ) -> dict[str, Any]:
        now = _now()
        group, engine, recs = await self.compute(user, subject_id, limit, now)
        ids: list[uuid.UUID | None] = [None] * len(recs)
        if log and recs:
            async with self.db.sessions()() as session, session.begin():
                for i, rec in enumerate(recs):
                    ids[i] = await self._log_shown(
                        session, user.id, subject_id, rec, group, surface, now
                    )
        return {
            "study_group": group,
            "engine": engine,
            "items": [serialise(r, i, self._names) for r, i in zip(recs, ids, strict=True)],
        }

    @staticmethod
    async def _log_shown(
        session: AsyncSession,
        user_id: uuid.UUID,
        subject_id: str,
        rec: Recommendation,
        group: str,
        surface: str,
        now: dt.datetime,
    ) -> uuid.UUID:
        recent = (
            await session.execute(
                select(recommendations_log.c.id)
                .where(
                    recommendations_log.c.user_id == user_id,
                    recommendations_log.c.concept_id == rec.concept_id,
                    recommendations_log.c.reason_code == rec.rule,
                    recommendations_log.c.surface == surface,
                    recommendations_log.c.completed_at.is_(None),
                    recommendations_log.c.shown_at >= now - dt.timedelta(hours=REUSE_HOURS),
                )
                .order_by(recommendations_log.c.shown_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if recent is not None:
            return recent  # type: ignore[no-any-return]
        row_id: uuid.UUID = (
            await session.execute(
                insert(recommendations_log)
                .values(
                    user_id=user_id, subject_id=subject_id, concept_id=rec.concept_id,
                    reason_code=rec.rule, reason_text=rec.reason,
                    path=[{"source": a, "target": b} for a, b in rec.path],
                    study_group=group, surface=surface, shown_at=now,
                )
                .returning(recommendations_log.c.id)
            )
        ).scalar_one()  # fmt: skip
        return row_id

    async def click(self, user: CurrentUser, log_id: uuid.UUID) -> bool:
        async with self.db.sessions()() as session, session.begin():
            result = await session.execute(
                update(recommendations_log)
                .where(
                    recommendations_log.c.id == log_id,
                    recommendations_log.c.user_id == user.id,
                )
                .values(clicked_at=func.coalesce(recommendations_log.c.clicked_at, _now()))
                .returning(recommendations_log.c.id)
            )
            return result.first() is not None


async def mark_completed(
    session: AsyncSession, user_id: uuid.UUID, concept_ids: list[str], now: dt.datetime
) -> int:
    """A quiz on a recommended concept with >= 60 % completes its open recommendations."""
    if not concept_ids:
        return 0
    result = await session.execute(
        update(recommendations_log)
        .where(
            and_(
                recommendations_log.c.user_id == user_id,
                recommendations_log.c.concept_id.in_(concept_ids),
                recommendations_log.c.completed_at.is_(None),
                recommendations_log.c.shown_at <= now,
            )
        )
        .values(completed_at=now)
        .returning(recommendations_log.c.id)
    )
    return len(result.all())
