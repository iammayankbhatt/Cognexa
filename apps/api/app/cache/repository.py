"""response_cache table access (one table, kind-prefixed keys: resp / cls / emb)."""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import response_cache


class CacheRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, key: str, now: dt.datetime) -> dict[str, Any] | None:
        """Payload of a live entry (and count the hit), or None."""
        row = (
            await self._s.execute(
                update(response_cache)
                .where(
                    response_cache.c.key_hash == key,
                    response_cache.c.invalidated.is_(False),
                    response_cache.c.expires_at > now,
                )
                .values(hits=response_cache.c.hits + 1)
                .returning(response_cache.c.payload)
            )
        ).first()
        return dict(row[0]) if row else None

    async def put(
        self,
        key: str,
        payload: dict[str, Any],
        concept_ids: Iterable[str],
        expires_at: dt.datetime,
    ) -> None:
        stmt = insert(response_cache).values(
            key_hash=key,
            payload=payload,
            concept_ids=sorted(set(concept_ids)),
            expires_at=expires_at,
        )
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=[response_cache.c.key_hash],
                set_={
                    "payload": stmt.excluded.payload,
                    "concept_ids": stmt.excluded.concept_ids,
                    "expires_at": stmt.excluded.expires_at,
                    "created_at": func.now(),
                    "invalidated": False,
                    "hits": 0,
                },
            )
        )

    async def invalidate_key(self, key: str) -> int:
        result = await self._s.execute(
            update(response_cache)
            .where(response_cache.c.key_hash == key, response_cache.c.invalidated.is_(False))
            .values(invalidated=True)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def invalidate_concepts(self, concept_ids: Iterable[str], kinds: Iterable[str]) -> int:
        """Invalidate every live entry of the given kinds that used any of these concepts."""
        ids = sorted(set(concept_ids))
        prefixes = [f"{k}:%" for k in kinds]
        if not ids or not prefixes:
            return 0
        result = await self._s.execute(
            update(response_cache)
            .where(
                and_(
                    response_cache.c.invalidated.is_(False),
                    response_cache.c.concept_ids.overlap(ids),
                    or_(*[response_cache.c.key_hash.like(p) for p in prefixes]),
                )
            )
            .values(invalidated=True)
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def purge(self, now: dt.datetime) -> int:
        """Delete expired and invalidated entries."""
        result = await self._s.execute(
            delete(response_cache).where(
                (response_cache.c.expires_at <= now) | response_cache.c.invalidated.is_(True)
            )
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]

    async def stats(self) -> dict[str, Any]:
        rows = await self._s.execute(
            select(
                func.split_part(response_cache.c.key_hash, ":", 1).label("kind"),
                func.count(),
                func.coalesce(func.sum(response_cache.c.hits), 0),
            )
            .where(response_cache.c.invalidated.is_(False))
            .group_by("kind")
        )
        return {r[0]: {"entries": int(r[1]), "hits": int(r[2])} for r in rows}
