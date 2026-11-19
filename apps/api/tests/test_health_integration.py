"""Live checks against real Postgres + Neo4j. Run in CI (service containers) or locally.

Skipped unless the databases are configured (environment variables or apps/api/.env).
"""

from httpx import ASGITransport, AsyncClient

from app.health_checks import check_neo4j, check_postgres
from app.main import create_app

from .conftest import live_settings, requires_neo4j, requires_postgres

pytestmark = [requires_postgres, requires_neo4j]


def _settings():  # type: ignore[no-untyped-def]
    return live_settings()


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
