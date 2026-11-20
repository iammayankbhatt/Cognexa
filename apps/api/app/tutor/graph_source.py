"""The read-only graph queries the tutor pipeline needs.

`GraphRepository` (Neo4j, the product) and `InMemoryGraph` (built from the subject's source files,
for offline evaluation and tests) both satisfy it.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from app.graph.models import GraphConcept
from app.graph.repository import ChunkRecord, PathConcept


class TutorGraph(Protocol):
    async def list_concepts(self, subject_id: str) -> list[GraphConcept]: ...

    async def search_concepts(
        self, subject_id: str, text: str, limit: int = 10
    ) -> list[tuple[str, float]]: ...

    async def get_prerequisites(self, concept_id: str, depth: int = 2) -> list[PathConcept]: ...

    async def get_related(self, concept_id: str) -> list[GraphConcept]: ...

    async def get_chunks(
        self, concept_ids: Iterable[str], kinds: Iterable[str] | None = None, limit: int = 50
    ) -> list[ChunkRecord]: ...
