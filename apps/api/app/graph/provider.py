"""Per-application Neo4j handle: the driver is created lazily and closed on shutdown.

It also keeps a short-lived copy of each subject's concept and edge lists (the "syllabus"), which
the dashboard, recommender, knowledge map, quizzes and revision sheets all read on every request.
The graph changes only through the admin editor, which invalidates the copy at once; other
writers (seed scripts in another process) are picked up when the TTL expires.
"""

from __future__ import annotations

import time
from typing import Any

from neo4j import AsyncDriver

from app.core.config import Settings
from app.core.errors import AppError
from app.graph.driver import create_driver
from app.graph.models import GraphConcept, GraphEdge
from app.graph.repository import GraphRepository

SYLLABUS_TTL_S = 120.0


class CachedSyllabus:
    """A GraphRepository whose list_concepts / list_edges are served from the provider's cache.
    Every other method goes straight to the repository."""

    def __init__(self, repo: GraphRepository, provider: GraphProvider) -> None:
        self._repo = repo
        self._provider = provider

    async def list_concepts(self, subject_id: str) -> list[GraphConcept]:
        concepts, _ = await self._provider._syllabus(self._repo, subject_id)
        return list(concepts)

    async def list_edges(self, subject_id: str) -> list[GraphEdge]:
        _, edges = await self._provider._syllabus(self._repo, subject_id)
        return list(edges)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repo, name)


class GraphProvider:
    def __init__(self, settings: Settings, clock: Any = time.monotonic) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None
        self._clock = clock
        self._cache: dict[str, tuple[float, list[GraphConcept], list[GraphEdge]]] = {}

    @property
    def configured(self) -> bool:
        s = self._settings
        return bool(s.neo4j_uri and s.neo4j_user and s.neo4j_password)

    def driver(self) -> AsyncDriver:
        """The one shared driver of this process (created on first use)."""
        if not self.configured:
            raise AppError("graph_not_configured", "The knowledge graph is not configured.", 503)
        if self._driver is None:
            self._driver = create_driver(self._settings)
        return self._driver

    def repository(self) -> GraphRepository:
        return GraphRepository(self.driver())

    def syllabus(self) -> CachedSyllabus:
        """Repository for read-mostly callers: cached concept and edge lists."""
        return CachedSyllabus(self.repository(), self)

    async def _syllabus(
        self, repo: GraphRepository, subject_id: str
    ) -> tuple[list[GraphConcept], list[GraphEdge]]:
        hit = self._cache.get(subject_id)
        if hit is not None and self._clock() - hit[0] < SYLLABUS_TTL_S:
            return hit[1], hit[2]
        concepts = await repo.list_concepts(subject_id)
        edges = await repo.list_edges(subject_id)
        self._cache[subject_id] = (self._clock(), concepts, edges)
        return concepts, edges

    def invalidate(self, subject_id: str | None = None) -> None:
        if subject_id is None:
            self._cache.clear()
        else:
            self._cache.pop(subject_id, None)

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None


def syllabus_of(provider: Any) -> Any:
    """`provider.syllabus()` when available (tests may install a simpler stand-in provider)."""
    fn = getattr(provider, "syllabus", None)
    return fn() if callable(fn) else provider.repository()
