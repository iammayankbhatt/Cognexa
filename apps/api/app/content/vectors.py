"""Embed content chunks: batched, retrying, resumable, skipping chunks whose text is unchanged."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import EMBEDDING_DIM, concepts, content_chunks
from app.llm.embeddings import EmbeddingProvider
from app.llm.errors import FatalLLMError

BATCH_SIZE = 32
MAX_ATTEMPTS = 4


class DimensionMismatchError(RuntimeError):
    pass


@dataclass
class EmbedResult:
    embedded: int
    skipped_unchanged: int
    batches: int


async def database_vector_dim(session: AsyncSession) -> int:
    """Dimension of content_chunks.embedding as declared in the database."""
    result = await session.execute(
        text(
            "select atttypmod from pg_attribute "
            "where attrelid = 'content_chunks'::regclass and attname = 'embedding'"
        )
    )
    return int(result.scalar_one())


async def check_dimensions(
    session: AsyncSession, provider: EmbeddingProvider, configured: int
) -> None:
    """Refuse to run when provider, EMBEDDING_DIM, code and database disagree (DEC-014)."""
    db_dim = await database_vector_dim(session)
    values = {
        "provider": provider.dim,
        "EMBEDDING_DIM": configured,
        "app.db.tables.EMBEDDING_DIM": EMBEDDING_DIM,
        "database column": db_dim,
    }
    if len(set(values.values())) != 1:
        detail = ", ".join(f"{k}={v}" for k, v in values.items())
        raise DimensionMismatchError(
            f"embedding dimensions disagree ({detail}). To change the size, add a migration that "
            "alters content_chunks.embedding, update EMBEDDING_DIM and re-run seed_vectors."
        )


async def _embed_with_retry(
    provider: EmbeddingProvider,
    texts: list[str],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> list[list[float]]:
    delay = 1.0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            vectors = await provider.embed(texts)
        except FatalLLMError:
            raise  # bad key, unknown model, wrong dimension: retrying cannot help
        except Exception:
            if attempt == MAX_ATTEMPTS:
                raise
            await sleep(delay)
            delay *= 2
            continue
        if len(vectors) != len(texts) or any(len(v) != provider.dim for v in vectors):
            raise DimensionMismatchError("provider returned vectors of the wrong count or size")
        return vectors
    raise AssertionError("unreachable")


async def embed_pending(
    session: AsyncSession,
    provider: EmbeddingProvider,
    *,
    batch_size: int = BATCH_SIZE,
    limit: int | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> EmbedResult:
    """Embed every chunk whose embedding is missing or stale. Commits after each batch, so an
    interrupted run resumes where it stopped. Chunks already embedded from the same text are
    skipped."""
    total = (await session.execute(select(func.count()).select_from(content_chunks))).scalar_one()
    pending_filter = content_chunks.c.embedding.is_(
        None
    ) | content_chunks.c.embedding_hash.is_distinct_from(content_chunks.c.content_hash)
    embedded = batches = 0
    while limit is None or embedded < limit:
        take = batch_size if limit is None else min(batch_size, limit - embedded)
        rows = (
            await session.execute(
                select(
                    content_chunks.c.id,
                    content_chunks.c.heading,
                    content_chunks.c.text,
                    content_chunks.c.content_hash,
                    concepts.c.name,
                )
                .join(concepts, concepts.c.id == content_chunks.c.concept_id)
                .where(pending_filter)
                .order_by(content_chunks.c.id)
                .limit(take)
            )
        ).all()
        if not rows:
            break
        inputs = [f"{r.name} - {r.heading}\n{r.text}" for r in rows]
        vectors = await _embed_with_retry(provider, inputs, sleep)
        for r, vec in zip(rows, vectors, strict=True):
            await session.execute(
                update(content_chunks)
                .where(content_chunks.c.id == r.id)
                .values(
                    embedding=vec,
                    embedding_hash=r.content_hash,
                    embedding_model=provider.model,
                )
            )
        await session.commit()
        embedded += len(rows)
        batches += 1
    await session.commit()  # end the read transaction so callers can begin their own
    return EmbedResult(embedded=embedded, skipped_unchanged=total - embedded, batches=batches)
