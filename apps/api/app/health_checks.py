"""Dependency probes for /health/deep. Never raise; always return a status dict.

The API passes its shared Database and GraphProvider, so a probe reuses the process-wide
connection pool and Neo4j driver instead of opening (and tearing down) new ones on every call
(Phase 13). Without them (scripts, integration tests) a short-lived connection is used.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Literal, TypedDict

from neo4j import AsyncGraphDatabase
from sqlalchemy import text

from app.core.config import Settings
from app.db.engine import create_engine

Status = Literal["ok", "error", "not_configured"]


class DependencyStatus(TypedDict):
    status: Status
    latency_ms: float | None
    detail: str | None


def _result(status: Status, start: float | None, detail: str | None = None) -> DependencyStatus:
    latency = round((time.perf_counter() - start) * 1000, 1) if start is not None else None
    return {"status": status, "latency_ms": latency, "detail": detail}


async def _ping_postgres(url: str, db: Any = None) -> None:
    if db is not None and getattr(db, "configured", False):
        async with db.sessions()() as session:
            await session.execute(text("SELECT 1"))
        return
    # Shared factory applies the pooler-safe settings (CLAUDE.md rule 6).
    engine = create_engine(url, pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def _ping_neo4j(uri: str, user: str, password: str, graph: Any = None) -> None:
    shared = getattr(graph, "driver", None) if graph is not None else None
    if callable(shared):
        await shared().verify_connectivity()
        return
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        await driver.verify_connectivity()
    finally:
        await driver.close()


async def check_postgres(settings: Settings, db: Any = None) -> DependencyStatus:
    if not settings.database_url:
        return _result("not_configured", None, "DATABASE_URL is not set")
    start = time.perf_counter()
    try:
        await asyncio.wait_for(
            _ping_postgres(settings.database_url, db), settings.health_check_timeout_s
        )
    except Exception as exc:
        return _result("error", start, type(exc).__name__)
    return _result("ok", start)


async def check_neo4j(settings: Settings, graph: Any = None) -> DependencyStatus:
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        return _result("not_configured", None, "NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD not set")
    start = time.perf_counter()
    try:
        await asyncio.wait_for(
            _ping_neo4j(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password, graph),
            settings.health_check_timeout_s,
        )
    except Exception as exc:
        return _result("error", start, type(exc).__name__)
    return _result("ok", start)
