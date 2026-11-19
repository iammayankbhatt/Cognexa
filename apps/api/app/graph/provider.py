"""Per-application Neo4j handle: the driver is created lazily and closed on shutdown."""

from __future__ import annotations

from neo4j import AsyncDriver

from app.core.config import Settings
from app.core.errors import AppError
from app.graph.driver import create_driver
from app.graph.repository import GraphRepository


class GraphProvider:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None

    @property
    def configured(self) -> bool:
        s = self._settings
        return bool(s.neo4j_uri and s.neo4j_user and s.neo4j_password)

    def repository(self) -> GraphRepository:
        if not self.configured:
            raise AppError("graph_not_configured", "The knowledge graph is not configured.", 503)
        if self._driver is None:
            self._driver = create_driver(self._settings)
        return GraphRepository(self._driver)

    async def close(self) -> None:
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
