"""Caching for AI work: answers, classifications and query embeddings.

- Answers (`resp:`) and classifications (`cls:`) carry the concept ids they used, so changing a
  concept's content or one of its edges invalidates exactly the entries that depended on it.
  A reported message invalidates its own entry.
- Query embeddings (`emb:`) depend only on the text and the embedding model; they expire by TTL.
- TTLs and an on/off switch live in app_settings["cache"] (admin-editable).
A cached answer still counts as one AI request for the user (Ticket.mark_cached), with no tokens.
"""

from __future__ import annotations

import datetime as dt
from collections import OrderedDict
from collections.abc import Callable, Iterable
from typing import Any

from app.cache.keys import cache_key
from app.cache.repository import CacheRepository
from app.db.repositories import DEFAULT_APP_SETTINGS, AppSettingsRepository
from app.db.session import Database
from app.llm.embeddings import EmbeddingProvider


class LLMCache:
    def __init__(self, db: Database, now: Callable[[], dt.datetime] | None = None) -> None:
        self.db = db
        self._now = now or (lambda: dt.datetime.now(dt.UTC))

    async def config(self) -> dict[str, Any]:
        async with self.db.sessions()() as session:
            stored = await AppSettingsRepository(session).get("cache") or {}
        return {**DEFAULT_APP_SETTINGS["cache"], **stored}

    async def _get(self, key: str) -> dict[str, Any] | None:
        cfg = await self.config()
        if not cfg["enabled"]:
            return None
        async with self.db.sessions()() as session, session.begin():
            return await CacheRepository(session).get(key, self._now())

    async def _put(
        self, key: str, payload: dict[str, Any], concept_ids: Iterable[str], ttl_field: str
    ) -> None:
        cfg = await self.config()
        if not cfg["enabled"]:
            return
        expires = self._now() + dt.timedelta(days=float(cfg[ttl_field]))
        async with self.db.sessions()() as session, session.begin():
            await CacheRepository(session).put(key, payload, concept_ids, expires)

    # ---------------------------------------------------------------- answers
    async def get_response(self, key: str) -> dict[str, Any] | None:
        return await self._get(key)

    async def put_response(
        self, key: str, payload: dict[str, Any], concept_ids: Iterable[str]
    ) -> None:
        await self._put(key, payload, concept_ids, "response_ttl_days")

    # ---------------------------------------------------------------- classifications
    async def get_classification(self, key: str) -> dict[str, Any] | None:
        return await self._get(key)

    async def put_classification(
        self, key: str, payload: dict[str, Any], concept_ids: Iterable[str]
    ) -> None:
        await self._put(key, payload, concept_ids, "classification_ttl_days")

    # ---------------------------------------------------------------- invalidation
    async def invalidate_concepts(
        self, concept_ids: Iterable[str], kinds: Iterable[str] = ("resp", "cls", "grade")
    ) -> int:
        """Concept content changed, or an edge touching these concepts changed."""
        async with self.db.sessions()() as session, session.begin():
            return await CacheRepository(session).invalidate_concepts(concept_ids, kinds)

    async def invalidate_key(self, key: str) -> int:
        """A message built from this entry was reported: never serve it again."""
        async with self.db.sessions()() as session, session.begin():
            return await CacheRepository(session).invalidate_key(key)

    async def purge(self) -> int:
        async with self.db.sessions()() as session, session.begin():
            return await CacheRepository(session).purge(self._now())

    async def stats(self) -> dict[str, Any]:
        async with self.db.sessions()() as session:
            return await CacheRepository(session).stats()


class CachedQueryEmbedder(EmbeddingProvider):
    """Wraps an embedding provider for *queries*: in-memory LRU first, then the database."""

    def __init__(self, inner: EmbeddingProvider, cache: LLMCache, lru_size: int = 512) -> None:
        self.inner = inner
        self.cache = cache
        self.model = inner.model
        self.dim = inner.dim
        self._lru: OrderedDict[str, list[float]] = OrderedDict()
        self._lru_size = lru_size
        self.misses = 0

    def _key(self, text: str) -> str:
        return cache_key("emb", text, model=f"{self.model}:{self.dim}")

    def _remember(self, key: str, vector: list[float]) -> None:
        self._lru[key] = vector
        self._lru.move_to_end(key)
        while len(self._lru) > self._lru_size:
            self._lru.popitem(last=False)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        keys = [self._key(t) for t in texts]
        found: dict[str, list[float]] = {}
        for key in keys:
            if key in self._lru:
                self._lru.move_to_end(key)
                found[key] = self._lru[key]
            elif (hit := await self.cache._get(key)) is not None:
                found[key] = [float(v) for v in hit["v"]]
                self._remember(key, found[key])
        missing = [(k, t) for k, t in zip(keys, texts, strict=True) if k not in found]
        unique = list(dict.fromkeys(missing))
        if unique:
            self.misses += len(unique)
            vectors = await self.inner.embed([t for _, t in unique])
            for (key, _), vector in zip(unique, vectors, strict=True):
                found[key] = vector
                self._remember(key, vector)
                await self.cache._put(key, {"v": vector}, (), "embedding_ttl_days")
        return [found[k] for k in keys]
