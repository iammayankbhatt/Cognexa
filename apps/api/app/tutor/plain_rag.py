"""The plain-RAG baseline: embed the question, take the top-k chunks by cosine similarity.

It searches the SAME chunks as GraphRAG (content_chunks in Postgres, embedded by
seed_vectors.py), under the same token budget and answer prompt minus the graph instructions, so
evaluation compares retrieval strategies and nothing else.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import select

from app.db.session import Database
from app.db.tables import content_chunks
from app.graph.repository import ChunkRecord
from app.llm.embeddings import EmbeddingProvider
from app.tutor.catalogue import cosine


class VectorSearch(Protocol):
    async def search(
        self, subject_id: str, vector: list[float], k: int, model: str
    ) -> list[tuple[ChunkRecord, float]]: ...


def _record(row: object) -> ChunkRecord:
    m = row._mapping  # type: ignore[attr-defined]
    return ChunkRecord(
        id=m["id"], concept_id=m["concept_id"], subject_id=m["subject_id"], kind=m["kind"],
        heading=m["heading"], text=m["text"], order=m["order"], reviewed=m["reviewed"],
    )  # fmt: skip


class PgVectorSearch:
    """Cosine distance (`<=>`) over content_chunks.embedding, limited to chunks embedded with the
    current embedding model (a model switch must not mix vector spaces)."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def search(
        self, subject_id: str, vector: list[float], k: int, model: str
    ) -> list[tuple[ChunkRecord, float]]:
        distance = content_chunks.c.embedding.cosine_distance(vector).label("distance")
        query = (
            select(content_chunks, distance)
            .where(
                content_chunks.c.subject_id == subject_id,
                content_chunks.c.embedding.is_not(None),
                content_chunks.c.embedding_model == model,
            )
            .order_by(distance)
            .limit(max(1, min(k, 50)))
        )
        async with self.db.sessions()() as session:
            rows = (await session.execute(query)).all()
        return [(_record(r), round(1.0 - float(r.distance), 4)) for r in rows]


class InMemoryVectorSearch:
    """Brute-force cosine over chunks embedded on first use (offline evaluation and tests)."""

    def __init__(
        self,
        chunks: Iterable[ChunkRecord],
        embedder: EmbeddingProvider,
        names: dict[str, str] | None = None,
    ) -> None:
        self.chunks = list(chunks)
        self.embedder = embedder
        self.names = names or {}
        self._vectors: list[list[float]] | None = None

    async def search(
        self, subject_id: str, vector: list[float], k: int, model: str
    ) -> list[tuple[ChunkRecord, float]]:
        if self._vectors is None:
            self._vectors = await self.embedder.embed(
                # same input format as seed_vectors.py (app.content.vectors)
                [
                    f"{self.names.get(c.concept_id, c.concept_id)} - {c.heading}\n{c.text}"
                    for c in self.chunks
                ]
            )
        scored = [
            (c, round(cosine(vector, v), 4))
            for c, v in zip(self.chunks, self._vectors, strict=True)
            if c.subject_id == subject_id
        ]
        scored.sort(key=lambda t: -t[1])
        return scored[: max(1, k)]
