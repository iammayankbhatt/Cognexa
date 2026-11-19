"""Live checks against real Postgres + Neo4j. Run in CI (service containers) or locally.

Skipped unless DATABASE_URL and NEO4J_URI/USER/PASSWORD are present in the environment.
"""

import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.health_checks import check_neo4j, check_postgres
from app.main import create_app

pytestmark = pytest.mark.skipif(
    not (
        os.environ.get("DATABASE_URL")
        and os.environ.get("NEO4J_URI")
        and os.environ.get("NEO4J_PASSWORD")
    ),
    reason="live databases not configured",
)


def _settings() -> Settings:
    return Settings(_env_file=None, health_check_timeout_s=10.0)


async def test_postgres_reachable_and_pgvector_available() -> None:
    result = await check_postgres(_settings())
    assert result["status"] == "ok", result


async def test_neo4j_reachable() -> None:
    result = await check_neo4j(_settings())
    assert result["status"] == "ok", result


async def test_deep_health_endpoint_ok_with_live_dependencies() -> None:
    app = create_app(_settings())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health/deep")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "ok"
    assert body["dependencies"]["postgres"]["latency_ms"] is not None
    assert body["dependencies"]["neo4j"]["latency_ms"] is not None
