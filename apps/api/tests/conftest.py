"""Shared fixtures. Live-database fixtures skip cleanly when the services are not configured."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from urllib.parse import urlsplit

import asyncpg
import pytest
from neo4j import AsyncDriver

from app.core.config import Settings
from app.db.engine import to_asyncpg_dsn
from app.graph.driver import create_driver
from app.graph.models import ConceptDef
from app.graph.repository import GraphRepository


def live_settings() -> Settings:
    """Settings from the environment / apps/api/.env (CI sets real service values)."""
    return Settings(health_check_timeout_s=10.0)


def _neo4j_configured() -> bool:
    s = live_settings()
    return bool(s.neo4j_uri and s.neo4j_user and s.neo4j_password)


def _postgres_configured() -> bool:
    return bool(live_settings().database_url)


requires_neo4j = pytest.mark.skipif(not _neo4j_configured(), reason="Neo4j not configured")
requires_postgres = pytest.mark.skipif(not _postgres_configured(), reason="Postgres not configured")


def make_concept(
    cid: str,
    prereqs: list[str] | None = None,
    related: list[str] | None = None,
    order_index: int = 0,
    cluster: str = "test",
) -> ConceptDef:
    return ConceptDef(
        id=cid,
        name=cid,
        cluster=cluster,
        difficulty=1,
        order_index=order_index,
        description="A concept created by an automated test.",
        aliases=[f"alias {cid}"],
        keywords=[f"keyword {cid}"],
        prerequisites=prereqs or [],
        related=related or [],
    )


@pytest.fixture
async def neo4j_driver() -> AsyncIterator[AsyncDriver]:
    if not _neo4j_configured():
        pytest.skip("Neo4j not configured")
    driver = create_driver(live_settings())
    try:
        await driver.verify_connectivity()
    except Exception as exc:  # service not running locally
        await driver.close()
        pytest.skip(f"Neo4j not reachable: {type(exc).__name__}")
    yield driver
    await driver.close()


@pytest.fixture
async def graph_repo(neo4j_driver: AsyncDriver) -> AsyncIterator[GraphRepository]:
    repo = GraphRepository(neo4j_driver)
    await repo.ensure_schema()
    yield repo


@pytest.fixture
async def isolated_subject(
    neo4j_driver: AsyncDriver, graph_repo: GraphRepository
) -> AsyncIterator[str]:
    """A unique subject id; everything created under it is deleted afterwards."""
    sid = f"t{uuid.uuid4().hex[:8]}"
    yield sid
    async with neo4j_driver.session() as session:
        await session.run(
            "MATCH (n) WHERE n.subject_id = $sid OR (n:Subject AND n.id = $sid) DETACH DELETE n",
            sid=sid,
        )


@pytest.fixture
async def fresh_db_url() -> AsyncIterator[str]:
    """URL of a brand-new empty database on the configured Postgres server (dropped afterwards).

    Needs a role that can CREATE DATABASE and CREATE EXTENSION (the docker/CI superuser does).
    """
    url = live_settings().database_url
    if not url:
        pytest.skip("Postgres not configured")
    name = f"cognexa_t_{uuid.uuid4().hex[:10]}"
    try:
        admin = await asyncpg.connect(to_asyncpg_dsn(url), statement_cache_size=0)
    except Exception as exc:
        pytest.skip(f"Postgres not reachable: {type(exc).__name__}")
    try:
        await admin.execute(f'create database "{name}"')
    finally:
        await admin.close()
    try:
        yield urlsplit(url)._replace(path=f"/{name}").geturl()
    finally:
        admin = await asyncpg.connect(to_asyncpg_dsn(url), statement_cache_size=0)
        try:
            await admin.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity where datname = $1", name
            )
            await admin.execute(f'drop database if exists "{name}"')
        finally:
            await admin.close()
