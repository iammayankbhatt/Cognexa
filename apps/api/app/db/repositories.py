"""Repositories for the Postgres tables. Phase 2 covers the concept mirror and app settings; later
phases add one repository per domain (quizzes, chat, usage, ...) in this same style."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.models import Question
from app.content.notes import Chunk
from app.db.tables import app_settings, concepts, content_chunks, questions, subjects
from app.graph.models import ConceptDef, ConceptFile

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
    "cache": {
        "enabled": True,
        "response_ttl_days": 7,
        "classification_ttl_days": 7,
        "embedding_ttl_days": 30,
    },
    # Runtime feature flags (admins edit them in /admin/settings).
    "features": {
        "AGENTIC_MODE": True,
        "STUDY_MODE": False,
        "PLAIN_RAG_VISIBLE_TO_STUDENTS": False,
    },
    # Notional $/1M tokens, see app/llm/pricing.py. Per-model entries use the env model ids.
    "llm.pricing": {"default": {"input_per_1m": 0.5, "output_per_1m": 1.5}, "models": {}},
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

    async def upsert_one(self, subject_id: str, c: ConceptDef) -> None:
        """Mirror one concept edited in the admin graph editor."""
        stmt = insert(concepts).values(
            id=c.id,
            subject_id=subject_id,
            name=c.name,
            cluster=c.cluster,
            difficulty=c.difficulty,
            order_index=c.order_index if c.order_index is not None else 0,
        )
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=[concepts.c.id],
                set_={
                    "name": stmt.excluded.name,
                    "cluster": stmt.excluded.cluster,
                    "difficulty": stmt.excluded.difficulty,
                    "order_index": stmt.excluded.order_index,
                    "updated_at": func.now(),
                },
            )
        )

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


class ContentRepository:
    """Content chunks and the question bank."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def changed_concepts(self, chunks: list[Chunk]) -> set[str]:
        """Concepts whose stored chunks differ from `chunks` (new, edited or removed chunks).
        Call before upsert_chunks; used to invalidate cached answers for exactly those concepts."""
        concept_ids = {c.concept_id for c in chunks}
        if not concept_ids:
            return set()
        stored: dict[str, set[tuple[str, str | None]]] = {}
        rows = await self._s.execute(
            select(
                content_chunks.c.concept_id, content_chunks.c.id, content_chunks.c.content_hash
            ).where(content_chunks.c.concept_id.in_(concept_ids))
        )
        for concept_id, chunk_id, content_hash in rows:
            stored.setdefault(concept_id, set()).add((chunk_id, content_hash))
        wanted: dict[str, set[tuple[str, str | None]]] = {}
        for c in chunks:
            wanted.setdefault(c.concept_id, set()).add((c.id, c.content_hash))
        return {cid for cid in concept_ids if stored.get(cid, set()) != wanted.get(cid, set())}

    async def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Insert or update chunks. A chunk whose text changed loses its (now stale) embedding.
        Chunks of the affected concepts that no longer exist in the notes are deleted."""
        if not chunks:
            return 0
        rows = [
            {
                "id": c.id,
                "concept_id": c.concept_id,
                "subject_id": c.subject_id,
                "kind": c.kind,
                "heading": c.heading,
                "text": c.text,
                "order": c.order,
                "reviewed": c.reviewed,
                "content_hash": c.content_hash,
            }
            for c in chunks
        ]
        stmt = insert(content_chunks).values(rows)
        changed = content_chunks.c.content_hash.is_distinct_from(stmt.excluded.content_hash)
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=[content_chunks.c.id],
                # chunks edited in the admin console (source 'admin') keep the admin's text
                where=content_chunks.c.source == "notes",
                set_={
                    "concept_id": stmt.excluded.concept_id,
                    "subject_id": stmt.excluded.subject_id,
                    "kind": stmt.excluded.kind,
                    "heading": stmt.excluded.heading,
                    "text": stmt.excluded.text,
                    "order": stmt.excluded.order,
                    "reviewed": stmt.excluded.reviewed,
                    "content_hash": stmt.excluded.content_hash,
                    "embedding": case((changed, None), else_=content_chunks.c.embedding),
                    "embedding_hash": case((changed, None), else_=content_chunks.c.embedding_hash),
                    "updated_at": func.now(),
                },
            )
        )
        await self._s.execute(
            delete(content_chunks).where(
                content_chunks.c.concept_id.in_({c.concept_id for c in chunks}),
                content_chunks.c.id.not_in([c.id for c in chunks]),
                # chunks approved from LLM proposals or written by admins are not in the notes
                content_chunks.c.source == "notes",
            )
        )
        return len(rows)

    async def upsert_questions(self, items: list[tuple[str, str, Question]]) -> int:
        """items = (subject_id, concept_id, question). Questions missing from the files are
        deactivated (never deleted: quiz history references them)."""
        if not items:
            return 0
        rows = [
            {
                "id": q.id,
                "concept_id": concept_id,
                "subject_id": subject_id,
                "type": q.type,
                "difficulty": q.difficulty,
                "prompt": q.prompt,
                "code": q.code,
                "language": q.language,
                "options": [o.model_dump() for o in q.options] if q.options else None,
                "answer": q.answer,
                "explanation": q.explanation,
                "rubric": q.rubric.model_dump() if q.rubric else None,
                "misconception_tag": q.misconception_tag,
                "diagnoses_prereq": q.diagnoses_prereq,
                "status": "active",
                "source": "authored",
            }
            for subject_id, concept_id, q in items
        ]
        stmt = insert(questions).values(rows)
        update_cols = {
            k: getattr(stmt.excluded, k)
            for k in (
                "concept_id",
                "subject_id",
                "type",
                "difficulty",
                "prompt",
                "code",
                "language",
                "options",
                "answer",
                "explanation",
                "rubric",
                "misconception_tag",
                "diagnoses_prereq",
                "status",
                "source",
            )
        }
        update_cols["updated_at"] = func.now()
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=[questions.c.id],
                set_=update_cols,
                # questions edited or deactivated in the admin console keep the admin's version
                where=questions.c.source.is_distinct_from("admin"),
            )
        )
        await self._s.execute(
            update(questions)
            .where(
                questions.c.concept_id.in_({r["concept_id"] for r in rows}),
                questions.c.id.not_in([r["id"] for r in rows]),
                questions.c.source == "authored",
            )
            .values(status="inactive")
        )
        return len(rows)

    async def count_chunks(self, subject_id: str) -> int:
        result = await self._s.execute(
            select(func.count())
            .select_from(content_chunks)
            .where(content_chunks.c.subject_id == subject_id)
        )
        return int(result.scalar_one())

    async def count_questions(self, subject_id: str, status: str = "active") -> int:
        result = await self._s.execute(
            select(func.count())
            .select_from(questions)
            .where(questions.c.subject_id == subject_id, questions.c.status == status)
        )
        return int(result.scalar_one())
