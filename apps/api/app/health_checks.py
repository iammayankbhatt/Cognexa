"""Dependency probes for /health/deep. Never raise; always return a status dict."""

import asyncio
import time
from typing import Literal, TypedDict

from neo4j import AsyncGraphDatabase
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings

Status = Literal["ok", "error", "not_configured"]


class DependencyStatus(TypedDict):
    status: Status
    latency_ms: float | None
    detail: str | None


def _result(status: Status, start: float | None, detail: str | None = None) -> DependencyStatus:
    latency = round((time.perf_counter() - start) * 1000, 1) if start is not None else None
    return {"status": status, "latency_ms": latency, "detail": detail}


def _async_url(url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


async def _ping_postgres(url: str) -> None:
    # CLAUDE.md rule 6: no prepared-statement caching (Supabase pooler, transaction mode).
    engine = create_async_engine(
        _async_url(url),
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def _ping_neo4j(uri: str, user: str, password: str) -> None:
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        await driver.verify_connectivity()
    finally:
        await driver.close()


async def check_postgres(settings: Settings) -> DependencyStatus:
    if not settings.database_url:
        return _result("not_configured", None, "DATABASE_URL is not set")
    start = time.perf_counter()
    try:
        await asyncio.wait_for(
            _ping_postgres(settings.database_url), settings.health_check_timeout_s
        )
    except Exception as exc:
        return _result("error", start, type(exc).__name__)
    return _result("ok", start)


async def check_neo4j(settings: Settings) -> DependencyStatus:
    if not (settings.neo4j_uri and settings.neo4j_user and settings.neo4j_password):
        return _result("not_configured", None, "NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD not set")
    start = time.perf_counter()
    try:
        await asyncio.wait_for(
            _ping_neo4j(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password),
            settings.health_check_timeout_s,
        )
    except Exception as exc:
        return _result("error", start, type(exc).__name__)
    return _result("ok", start)
