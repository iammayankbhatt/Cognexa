"""Repositories for the Postgres tables. Phase 2 covers the concept mirror and app settings; later
phases add one repository per domain (quizzes, chat, usage, ...) in this same style."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import app_settings, concepts, subjects
from app.graph.models import ConceptFile

# Quota and cap defaults (CLAUDE.md rule 2 / Phase 2 part D). Admin edits survive re-seeding because
# defaults are only inserted when the key is missing.
DEFAULT_APP_SETTINGS: dict[str, dict[str, Any]] = {
    "quota.student": {
        "daily_ai_requests": 40,
        "per_minute": 6,
        "max_input_chars": 2000,
        "max_output_tokens": 900,
    },
    "quota.role_multipliers": {"student": 1, "reviewer": 5, "admin": 5},
    "quota.global_daily_cap": {"ai_requests": 1500},
}


class ConceptMirrorRepository:
    """Postgres mirror of the Neo4j concept nodes (for foreign keys and fast lookups)."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def upsert_from_file(self, doc: ConceptFile) -> tuple[int, int]:
        """Idempotently upsert the subject and all its concepts. Returns (subjects, concepts)."""
        sub = insert(subjects).values(id=doc.subject.id, name=doc.subject.name)
        await self._s.execute(
            sub.on_conflict_do_update(
                index_elements=[subjects.c.id], set_={"name": sub.excluded.name}
            )
        )
        rows = [
            {
                "id": c.id,
                "subject_id": doc.subject.id,
                "name": c.name,
                "cluster": c.cluster,
                "difficulty": c.difficulty,
                "order_index": c.order_index if c.order_index is not None else 0,
            }
            for c in doc.concepts
        ]
        if rows:
            stmt = insert(concepts).values(rows)
            await self._s.execute(
                stmt.on_conflict_do_update(
                    index_elements=[concepts.c.id],
                    set_={
                        "subject_id": stmt.excluded.subject_id,
                        "name": stmt.excluded.name,
                        "cluster": stmt.excluded.cluster,
                        "difficulty": stmt.excluded.difficulty,
                        "order_index": stmt.excluded.order_index,
                    },
                )
            )
        return 1, len(rows)

    async def count(self, subject_id: str) -> int:
        result = await self._s.execute(
            select(func.count()).select_from(concepts).where(concepts.c.subject_id == subject_id)
        )
        return int(result.scalar_one())

    async def concept_ids(self, subject_id: str) -> list[str]:
        result = await self._s.execute(
            select(concepts.c.id)
            .where(concepts.c.subject_id == subject_id)
            .order_by(concepts.c.order_index)
        )
        return [r[0] for r in result]


class AppSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def ensure_defaults(self) -> int:
        """Insert default settings that are missing. Never overwrites existing values.
        Returns how many keys were inserted."""
        inserted = 0
        for key, value in DEFAULT_APP_SETTINGS.items():
            stmt = (
                insert(app_settings)
                .values(key=key, value=value)
                .on_conflict_do_nothing(index_elements=[app_settings.c.key])
                .returning(app_settings.c.key)
            )
            if (await self._s.execute(stmt)).first() is not None:
                inserted += 1
        return inserted

    async def get(self, key: str) -> dict[str, Any] | None:
        result = await self._s.execute(
            select(app_settings.c.value).where(app_settings.c.key == key)
        )
        row = result.first()
        return dict(row[0]) if row else None

    async def set(self, key: str, value: dict[str, Any]) -> None:
        stmt = insert(app_settings).values(key=key, value=value)
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=[app_settings.c.key],
                set_={"value": stmt.excluded.value, "updated_at": func.now()},
            )
        )
