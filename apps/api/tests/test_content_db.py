"""Chunk/question loading, change tracking and embedding, against a throwaway Postgres."""

from __future__ import annotations

import math
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.content.loader import load_chunks, load_questions
from app.content.vectors import (
    DimensionMismatchError,
    _embed_with_retry,
    check_dimensions,
    embed_pending,
)
from app.db.engine import create_engine, session_factory
from app.db.migrate import apply_migrations
from app.db.repositories import ConceptMirrorRepository, ContentRepository
from app.db.tables import EMBEDDING_DIM, content_chunks, questions
from app.graph.loader import load_subject
from app.llm.embeddings import (
    EmbeddingProvider,
    EmbeddingProviderUnavailableError,
    FakeEmbeddingProvider,
    get_embedding_provider,
)

from .conftest import requires_postgres
from .content_helpers import note_text, write_subject

# ------------------------------------------------------------------ fake embeddings (no database)


async def test_fake_embeddings_are_deterministic_unit_vectors() -> None:
    p = FakeEmbeddingProvider(dim=64)
    a1, a2 = (
        await p.embed(["stack overflow in recursion"]),
        await p.embed(["stack overflow in recursion"]),
    )
    assert a1 == a2
    assert len(a1[0]) == 64
    assert math.isclose(math.sqrt(sum(x * x for x in a1[0])), 1.0, rel_tol=1e-9)


async def test_fake_embeddings_rank_shared_words_higher() -> None:
    p = FakeEmbeddingProvider(dim=256)
    q, near, far = await p.embed(
        [
            "recursion call stack overflow",
            "the call stack overflows during deep recursion",
            "sorting hash table",
        ]
    )

    def dot(x: list[float], y: list[float]) -> float:
        return sum(a * b for a, b in zip(x, y, strict=True))

    assert dot(q, near) > dot(q, far)


async def test_fake_embeddings_handle_empty_text_and_validate_dim() -> None:
    p = FakeEmbeddingProvider(dim=16)
    (v,) = await p.embed(["   !!! "])
    assert math.isclose(sum(x * x for x in v), 1.0)
    with pytest.raises(ValueError):
        FakeEmbeddingProvider(dim=2)


def test_provider_factory() -> None:
    from app.core.config import Settings

    p = get_embedding_provider(
        Settings(_env_file=None, embedding_provider="fake", embedding_dim=32)
    )
    assert p.dim == 32
    with pytest.raises(EmbeddingProviderUnavailableError, match="Phase 5"):
        get_embedding_provider(Settings(_env_file=None, embedding_provider="gemini"))


# ------------------------------------------------------------------ retry logic (no database)
class FlakyProvider(EmbeddingProvider):
    def __init__(self, failures: int, dim: int = 16) -> None:
        self.dim, self.model, self.failures, self.calls = dim, "flaky", failures, 0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls <= self.failures:
            raise ConnectionError("rate limited")
        return [[0.1] * self.dim for _ in texts]


async def test_retry_backs_off_then_succeeds() -> None:
    delays: list[float] = []

    async def fake_sleep(d: float) -> None:
        delays.append(d)

    p = FlakyProvider(failures=2)
    out = await _embed_with_retry(p, ["a", "b"], fake_sleep)
    assert len(out) == 2 and p.calls == 3 and delays == [1.0, 2.0]


async def test_retry_gives_up_after_max_attempts() -> None:
    async def no_sleep(_: float) -> None: ...

    p = FlakyProvider(failures=99)
    with pytest.raises(ConnectionError):
        await _embed_with_retry(p, ["a"], no_sleep)
    assert p.calls == 4


async def test_wrong_size_vectors_are_rejected() -> None:
    class Bad(FlakyProvider):
        async def embed(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 3 for _ in texts]

    with pytest.raises(DimensionMismatchError):
        await _embed_with_retry(Bad(0), ["a"])


# ------------------------------------------------------------------ database
@pytest.fixture
async def mini(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_db_url: str
) -> AsyncIterator[AsyncSession]:
    write_subject(tmp_path, monkeypatch)
    await apply_migrations(fresh_db_url)
    engine = create_engine(fresh_db_url)
    async with session_factory(engine)() as s:
        async with s.begin():
            await ConceptMirrorRepository(s).upsert_from_file(load_subject("mini"))
            repo = ContentRepository(s)
            await repo.upsert_chunks(load_chunks("mini"))
            await repo.upsert_questions([("mini", cid, q) for cid, q in load_questions("mini")])
        yield s
    await engine.dispose()


pytestmark_db = requires_postgres


@requires_postgres
async def test_chunks_and_questions_are_loaded(mini: AsyncSession) -> None:
    repo = ContentRepository(mini)
    assert await repo.count_chunks("mini") == 30  # 3 concepts x 10 sections
    assert await repo.count_questions("mini") == 24  # 3 concepts x 8 questions
    row = (
        (await mini.execute(select(questions).where(questions.c.id == "mid-q01"))).mappings().one()
    )
    assert row["type"] == "mcq" and row["answer"] == "a" and len(row["options"]) == 4
    short = (
        await mini.execute(select(questions.c.rubric).where(questions.c.id == "mid-q08"))
    ).scalar_one()
    assert short["key_points"] == ["purpose", "reason"]


@requires_postgres
async def test_reloading_is_idempotent(mini: AsyncSession) -> None:
    async with mini.begin():
        repo = ContentRepository(mini)
        assert await repo.upsert_chunks(load_chunks("mini")) == 30
        await repo.upsert_questions([("mini", cid, q) for cid, q in load_questions("mini")])
    assert await ContentRepository(mini).count_chunks("mini") == 30
    assert await ContentRepository(mini).count_questions("mini") == 24


@requires_postgres
async def test_embedding_is_resumable_and_skips_unchanged_chunks(mini: AsyncSession) -> None:
    provider = FakeEmbeddingProvider(EMBEDDING_DIM)
    first = await embed_pending(mini, provider, batch_size=7, limit=10)
    assert first.embedded == 10 and first.batches == 2  # interrupted early: resumable
    rest = await embed_pending(mini, provider, batch_size=7)
    assert rest.embedded == 20
    again = await embed_pending(mini, provider)
    assert again.embedded == 0 and again.skipped_unchanged == 30
    done = (
        await mini.execute(
            select(content_chunks.c.embedding_model).where(content_chunks.c.id == "mid#overview")
        )
    ).scalar_one()
    assert done == "fake-embedding"


@requires_postgres
async def test_only_changed_chunks_are_re_embedded(
    mini: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeEmbeddingProvider(EMBEDDING_DIM)
    await embed_pending(mini, provider)
    note = tmp_path / "mini" / "content" / "mid.md"
    note.write_text(
        note_text("mid").replace("## Complexity\nConstant", "## Complexity\nLinear and constant"),
        encoding="utf-8",
    )
    async with mini.begin():
        await ContentRepository(mini).upsert_chunks(load_chunks("mini"))
    stale = (
        (
            await mini.execute(
                select(content_chunks.c.id).where(content_chunks.c.embedding.is_(None))
            )
        )
        .scalars()
        .all()
    )
    assert stale == ["mid#complexity"]
    result = await embed_pending(mini, provider)
    assert result.embedded == 1


@requires_postgres
async def test_removed_sections_and_questions_are_cleaned_up(
    mini: AsyncSession, tmp_path: Path
) -> None:
    note = tmp_path / "mini" / "content" / "top.md"
    note.write_text(
        note_text("top").replace("## Leads To\nIt leads to many things.\n\n", ""), encoding="utf-8"
    )
    chunks = [c for c in load_chunks("mini") if c.concept_id != "top" or c.kind != "next"]
    qs = [(cid, q) for cid, q in load_questions("mini") if q.id != "top-q08"]
    async with mini.begin():
        repo = ContentRepository(mini)
        await repo.upsert_chunks(chunks)
        await repo.upsert_questions([("mini", cid, q) for cid, q in qs])
    assert await ContentRepository(mini).count_chunks("mini") == 29
    assert await ContentRepository(mini).count_questions("mini") == 23
    assert (
        await ContentRepository(mini).count_questions("mini", "inactive") == 1
    )  # deactivated, not deleted


@requires_postgres
async def test_dimension_guard(mini: AsyncSession) -> None:
    await check_dimensions(mini, FakeEmbeddingProvider(EMBEDDING_DIM), EMBEDDING_DIM)
    with pytest.raises(DimensionMismatchError, match="disagree"):
        await check_dimensions(mini, FakeEmbeddingProvider(32), EMBEDDING_DIM)
    with pytest.raises(DimensionMismatchError):
        await check_dimensions(mini, FakeEmbeddingProvider(EMBEDDING_DIM), 1536)


@requires_postgres
async def test_nearest_chunk_search_with_fake_embeddings(mini: AsyncSession) -> None:
    provider = FakeEmbeddingProvider(EMBEDDING_DIM)
    async with mini.begin():
        await mini.execute(
            update(content_chunks)
            .where(content_chunks.c.id == "mid#overview")
            .values(text="the call stack grows with every recursive function call")
        )
    await embed_pending(
        mini, provider
    )  # text changed in place without hash: embedded from old hash
    (qvec,) = await provider.embed(["recursive function call stack"])
    rows = (
        (
            await mini.execute(
                text(
                    "select id from content_chunks order by embedding <=> cast(:v as vector) limit 3"
                ),
                {"v": "[" + ",".join(map(str, qvec)) + "]"},
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 3
