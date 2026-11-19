"""Caches: keys, hit/miss/expiry, invalidation by concept and by message, query embeddings,
and the seed's content-change invalidation."""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.cache.keys import cache_key, normalize_text
from app.cache.service import CachedQueryEmbedder, LLMCache
from app.content.notes import Chunk
from app.core.config import Settings
from app.db.engine import to_asyncpg_dsn
from app.db.migrate import apply_migrations
from app.db.repositories import ContentRepository
from app.db.session import Database
from app.llm.embeddings import FakeEmbeddingProvider
from tests.conftest import requires_postgres

# ---------------------------------------------------------------- keys (no database)


def test_normalize_text() -> None:
    assert normalize_text("  What is a Heap?? ") == normalize_text("what is a   heap")
    assert normalize_text("a[i] = 1") != normalize_text("a i 1")  # inner punctuation matters


def test_cache_key_parts() -> None:
    base = cache_key("resp", "What is a heap?", mode="graphrag", concept_ids=["b", "a"], bucket="x")
    assert base.startswith("resp:") and len(base) == 5 + 64
    same = cache_key(
        "resp", "what is a heap", mode="graphrag", concept_ids=["a", "b", "a"], bucket="x"
    )
    assert base == same  # normalised text, concept order and duplicates do not matter
    for other in (
        cache_key("resp", "What is a heap?", mode="plain_rag", concept_ids=["a", "b"], bucket="x"),
        cache_key("resp", "What is a heap?", mode="graphrag", concept_ids=["a"], bucket="x"),
        cache_key("resp", "What is a heap?", mode="graphrag", concept_ids=["a", "b"], bucket="y"),
        cache_key("cls", "What is a heap?", mode="graphrag", concept_ids=["a", "b"], bucket="x"),
    ):
        assert other != base
    with pytest.raises(ValueError):
        cache_key("nope", "x")


# ---------------------------------------------------------------- service against Postgres


class Now:
    def __init__(self) -> None:
        self.t = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.UTC)

    def __call__(self) -> dt.datetime:
        return self.t


class Env:
    def __init__(self, cache: LLMCache, now: Now, conn: asyncpg.Connection, db: Database):
        self.cache, self.now, self.conn, self.db = cache, now, conn, db


@pytest.fixture
async def env(fresh_db_url: str) -> AsyncIterator[Env]:
    await apply_migrations(fresh_db_url)
    db = Database(Settings(_env_file=None, database_url=fresh_db_url))
    now = Now()
    conn = await asyncpg.connect(to_asyncpg_dsn(fresh_db_url), statement_cache_size=0)
    try:
        yield Env(LLMCache(db, now=now), now, conn, db)
    finally:
        await conn.close()
        await db.dispose()


@requires_postgres
async def test_hit_miss_expiry_and_hit_count(env: Env) -> None:
    key = cache_key("resp", "what is a heap", mode="graphrag", concept_ids=["binary_heap"])
    assert await env.cache.get_response(key) is None
    await env.cache.put_response(key, {"text": "A heap is..."}, ["binary_heap"])
    assert await env.cache.get_response(key) == {"text": "A heap is..."}
    assert await env.cache.get_response(key) is not None
    assert await env.conn.fetchval("select hits from response_cache where key_hash=$1", key) == 2
    env.now.t += dt.timedelta(days=7, seconds=1)  # default TTL is 7 days
    assert await env.cache.get_response(key) is None
    assert await env.cache.purge() == 1


@requires_postgres
async def test_invalidation_by_concept_only_hits_dependent_entries(env: Env) -> None:
    heap = cache_key("resp", "heap?", concept_ids=["binary_heap", "array"])
    stack = cache_key("resp", "stack?", concept_ids=["stack"])
    cls = cache_key("cls", "heap?")
    await env.cache.put_response(heap, {"text": "h"}, ["binary_heap", "array"])
    await env.cache.put_response(stack, {"text": "s"}, ["stack"])
    await env.cache.put_classification(cls, {"concept_ids": ["binary_heap"]}, ["binary_heap"])
    # e.g. the edge array -> binary_heap changed: both endpoints are invalidated
    assert await env.cache.invalidate_concepts(["array", "binary_heap"]) == 2
    assert await env.cache.get_response(heap) is None
    assert await env.cache.get_classification(cls) is None
    assert await env.cache.get_response(stack) == {"text": "s"}
    # a fresh put revives the key
    await env.cache.put_response(heap, {"text": "h2"}, ["binary_heap"])
    assert await env.cache.get_response(heap) == {"text": "h2"}


@requires_postgres
async def test_reported_message_invalidates_its_entry(env: Env) -> None:
    key = cache_key("resp", "bad answer?")
    await env.cache.put_response(key, {"text": "wrong"}, ["stack"])
    assert await env.cache.invalidate_key(key) == 1
    assert await env.cache.get_response(key) is None
    assert await env.cache.invalidate_key(key) == 0


@requires_postgres
async def test_disabled_cache_and_custom_ttl(env: Env) -> None:
    key = cache_key("resp", "q")
    await env.conn.execute(
        "insert into app_settings (key, value) values ('cache', $1::jsonb)",
        json.dumps({"enabled": False}),
    )
    await env.cache.put_response(key, {"text": "x"}, [])
    assert await env.cache.get_response(key) is None
    await env.conn.execute(
        "update app_settings set value = $1::jsonb where key = 'cache'",
        json.dumps({"enabled": True, "response_ttl_days": 1}),
    )
    await env.cache.put_response(key, {"text": "x"}, [])
    env.now.t += dt.timedelta(hours=25)
    assert await env.cache.get_response(key) is None


@requires_postgres
async def test_query_embeddings_are_cached_in_memory_and_in_the_database(env: Env) -> None:
    inner = FakeEmbeddingProvider(dim=16)
    embedder = CachedQueryEmbedder(inner, env.cache)
    first = await embedder.embed(["what is a heap", "what is a heap", "stack"])
    assert first[0] == first[1] and embedder.misses == 2
    assert await embedder.embed(["What is a heap?"]) == [first[0]]  # normalised, from memory
    assert embedder.misses == 2
    fresh = CachedQueryEmbedder(inner, env.cache)  # new process: empty memory, DB still has it
    assert await fresh.embed(["stack"]) == [first[2]] and fresh.misses == 0
    stats = await env.cache.stats()
    assert stats["emb"]["entries"] == 2


@requires_postgres
async def test_changed_concepts_detects_new_edited_and_removed_chunks(env: Env) -> None:
    await env.conn.execute("insert into subjects (id, name) values ('dsa', 'DSA')")
    for cid in ("stack", "queue"):
        await env.conn.execute(
            "insert into concepts (id, subject_id, name, cluster, difficulty, order_index) "
            "values ($1, 'dsa', $1, 'linear', 1, 0)",
            cid,
        )

    def chunk(cid: str, n: int, text: str) -> Chunk:
        return Chunk(id=f"{cid}#{n}", concept_id=cid, subject_id="dsa", kind="explanation",
                     heading="h", text=text, order=n, reviewed=False)  # fmt: skip

    v1 = [chunk("stack", 0, "LIFO"), chunk("queue", 0, "FIFO"), chunk("queue", 1, "ring")]
    async with env.db.sessions()() as s, s.begin():
        repo = ContentRepository(s)
        assert await repo.changed_concepts(v1) == {"stack", "queue"}  # all new
        await repo.upsert_chunks(v1)
        assert await repo.changed_concepts(v1) == set()
        v2 = [chunk("stack", 0, "LIFO, edited"), chunk("queue", 0, "FIFO")]  # queue#1 removed
        assert await repo.changed_concepts(v2) == {"stack", "queue"}
        v3 = [chunk("stack", 0, "LIFO"), chunk("queue", 0, "FIFO"), chunk("queue", 1, "ring")]
        assert await repo.changed_concepts(v3) == set()
