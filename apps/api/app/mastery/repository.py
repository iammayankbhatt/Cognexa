"""Mastery rows: read with time decay, update from graded answers."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import mastery
from app.mastery.model import (
    DEFAULT_PARAMS,
    MasteryParams,
    band,
    effective_score,
    penalised_prereq,
    updated_score,
)


@dataclass(frozen=True)
class GradedEvent:
    """One graded answer, as the mastery model sees it."""

    concept_id: str
    result: float
    difficulty: int
    diagnoses_prereq: str | None = None


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class MasteryRepository:
    def __init__(self, session: AsyncSession, params: MasteryParams = DEFAULT_PARAMS) -> None:
        self.session = session
        self.params = params

    async def rows(self, user_id: uuid.UUID, subject_id: str) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(mastery).where(mastery.c.user_id == user_id, mastery.c.subject_id == subject_id)
        )
        return [dict(r._mapping) for r in result]

    async def effective_map(
        self, user_id: uuid.UUID, subject_id: str, now: dt.datetime | None = None
    ) -> dict[str, float]:
        """Decayed scores of practised concepts (attempts > 0); absent = never practised."""
        now = now or _now()
        return {
            r["concept_id"]: effective_score(
                float(r["score"]), r["last_practiced_at"], now, self.params
            )
            for r in await self.rows(user_id, subject_id)
            if r["attempts"] > 0
        }

    async def view(
        self, user_id: uuid.UUID, subject_id: str, now: dt.datetime | None = None
    ) -> list[dict[str, Any]]:
        now = now or _now()
        out = []
        for r in await self.rows(user_id, subject_id):
            eff = effective_score(float(r["score"]), r["last_practiced_at"], now, self.params)
            out.append(
                {
                    "concept_id": r["concept_id"],
                    "score": float(r["score"]),
                    "effective": eff,
                    "band": band(eff, self.params),
                    "attempts": r["attempts"],
                    "correct": r["correct"],
                    "last_practiced_at": r["last_practiced_at"],
                    "next_review_at": r["next_review_at"],
                }
            )
        return out

    async def apply(
        self,
        user_id: uuid.UUID,
        subject_id: str,
        events: list[GradedEvent],
        now: dt.datetime | None = None,
    ) -> dict[str, float]:
        """Apply graded answers in order; returns the new stored scores of touched concepts.

        Rows are locked in concept-id order (one lock order everywhere avoids deadlocks, as in
        BUG-019). Must run inside a transaction.
        """
        if not events:
            return {}
        now = now or _now()
        touched = sorted(
            {e.concept_id for e in events}
            | {e.diagnoses_prereq for e in events if e.diagnoses_prereq}
        )
        locked = await self.session.execute(
            select(mastery)
            .where(mastery.c.user_id == user_id, mastery.c.concept_id.in_(touched))
            .order_by(mastery.c.concept_id)
            .with_for_update()
        )
        state: dict[str, dict[str, Any]] = {
            r.concept_id: {
                "score": float(r.score),
                "attempts": r.attempts,
                "correct": r.correct,
                "practised": r.last_practiced_at,
            }
            for r in locked
        }

        def row(cid: str) -> dict[str, Any]:
            return state.setdefault(
                cid, {"score": 0.0, "attempts": 0, "correct": 0, "practised": None}
            )

        practised: set[str] = set()
        changed: set[str] = set()
        for e in events:
            r = row(e.concept_id)
            r["score"] = updated_score(r["score"], e.result, e.difficulty, self.params)
            r["attempts"] += 1
            r["correct"] += 1 if e.result >= 0.999 else 0
            practised.add(e.concept_id)
            changed.add(e.concept_id)
            if e.result < 0.5 and e.diagnoses_prereq and e.diagnoses_prereq != e.concept_id:
                p = row(e.diagnoses_prereq)
                p["score"] = penalised_prereq(p["score"], self.params)
                changed.add(e.diagnoses_prereq)

        # Only concepts that changed are written (a correct answer leaves its diagnosed
        # prerequisite alone, even though that row was locked).
        for cid in sorted(changed):
            r = state[cid]
            values: dict[str, Any] = {
                "score": r["score"],
                "attempts": r["attempts"],
                "correct": r["correct"],
                "updated_at": now,
            }
            if cid in practised:
                values["last_practiced_at"] = now
            stmt = pg_insert(mastery).values(
                user_id=user_id, concept_id=cid, subject_id=subject_id, **values
            )
            await self.session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[mastery.c.user_id, mastery.c.concept_id], set_=values
                )
            )
        return {cid: state[cid]["score"] for cid in sorted(changed)}
