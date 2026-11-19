"""Neo4j driver factory. One AsyncDriver per process; sessions are created per call."""

from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import Settings


class GraphNotConfiguredError(RuntimeError):
    pass


def create_driver(settings: Settings) -> AsyncDriver:
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        raise GraphNotConfiguredError("NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are not set")
    return AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
