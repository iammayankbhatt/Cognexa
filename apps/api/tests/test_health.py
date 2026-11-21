import logging

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def client() -> AsyncClient:
    app = create_app(Settings(_env_file=None, database_url=None, neo4j_uri=None))
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_health_ok(client: AsyncClient) -> None:
    async with client as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-request-id"]


async def test_request_id_is_echoed(client: AsyncClient) -> None:
    async with client as c:
        r = await c.get("/health", headers={"X-Request-ID": "abc12345-test"})
    assert r.headers["x-request-id"] == "abc12345-test"


async def test_bad_request_id_is_replaced(client: AsyncClient) -> None:
    async with client as c:
        r = await c.get("/health", headers={"X-Request-ID": "bad id with spaces!"})
    assert r.headers["x-request-id"] != "bad id with spaces!"


async def test_deep_health_not_configured(client: AsyncClient) -> None:
    async with client as c:
        r = await c.get("/health/deep")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["postgres"]["status"] == "not_configured"
    assert body["dependencies"]["neo4j"]["status"] == "not_configured"


async def test_deep_health_unreachable_reports_error_without_crashing() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+asyncpg://u:p@127.0.0.1:1/db",
        neo4j_uri="bolt://127.0.0.1:1",
        neo4j_user="neo4j",
        neo4j_password="x",
        health_check_timeout_s=2.0,
    )
    app = create_app(settings)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health/deep")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["postgres"]["status"] == "error"
    assert body["dependencies"]["neo4j"]["status"] == "error"
    assert body["dependencies"]["postgres"]["latency_ms"] is not None


async def test_unknown_route_uses_error_envelope(client: AsyncClient) -> None:
    async with client as c:
        r = await c.get("/nope")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "not_found"
    assert err["request_id"] == r.headers["x-request-id"]


async def test_unhandled_exception_uses_error_envelope() -> None:
    app = create_app(Settings(_env_file=None))

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internals")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"


async def test_unhandled_exception_keeps_cors_and_request_id() -> None:
    """BUG-055: the catch-all handler ran in Starlette's outermost ServerErrorMiddleware, so the
    500 had no CORS header (the browser hid it as a network error) and request_id was '-'."""
    settings = Settings(_env_file=None, allowed_origins=["https://web.example"])
    app = create_app(settings)

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("secret internals")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get(
            "/boom", headers={"Origin": "https://web.example", "X-Request-ID": "rid-12345678"}
        )
    assert r.status_code == 500
    body = r.json()["error"]
    assert body["code"] == "internal_error" and "secret" not in r.text
    assert body["request_id"] == "rid-12345678"
    assert r.headers["x-request-id"] == "rid-12345678"
    assert r.headers["access-control-allow-origin"] == "https://web.example"
    assert "secret" not in r.text


async def test_cors_allows_configured_origin_only() -> None:
    app = create_app(Settings(_env_file=None, allowed_origins=["http://good.example"]))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        good = await c.get("/health", headers={"Origin": "http://good.example"})
        bad = await c.get("/health", headers={"Origin": "http://evil.example"})
    assert good.headers.get("access-control-allow-origin") == "http://good.example"
    assert "access-control-allow-origin" not in bad.headers


def test_allowed_origins_parsed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.test, http://b.test")
    assert Settings(_env_file=None).allowed_origins == ["http://a.test", "http://b.test"]


async def test_access_log_line_emitted(
    client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.access"):
        async with client as c:
            await c.get("/health")
    assert any(r.getMessage() == "request" and r.__dict__["status"] == 200 for r in caplog.records)


def test_wildcard_cors_origin_is_refused() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="not allowed"):
        Settings(_env_file=None, allowed_origins="https://ok.example, *")


async def test_large_json_is_gzipped_but_small_replies_are_not() -> None:
    from fastapi.responses import JSONResponse

    app = create_app(Settings(_env_file=None))

    @app.get("/big")
    async def big() -> JSONResponse:
        return JSONResponse({"items": ["concept"] * 500})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/big", headers={"Accept-Encoding": "gzip"})
        assert r.headers.get("content-encoding") == "gzip" and len(r.json()["items"]) == 500
        small = await c.get("/health", headers={"Accept-Encoding": "gzip"})
        assert "content-encoding" not in small.headers


async def test_neo4j_outage_is_a_503_graph_unavailable() -> None:
    """BUG-058: with Neo4j down, /dashboard, /recommendations, /concepts/{id}... answered a
    generic 500 'Something went wrong' instead of saying the graph is unavailable."""
    from neo4j.exceptions import ServiceUnavailable

    app = create_app(Settings(_env_file=None, allowed_origins=["https://web.example"]))

    @app.get("/graph-down")
    async def graph_down() -> None:
        raise ServiceUnavailable("Couldn't connect to localhost:7687")

    @app.get("/pg-down")
    async def pg_down() -> None:
        raise ConnectionRefusedError("postgres refused")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/graph-down", headers={"Origin": "https://web.example"})
        pg = await c.get("/pg-down")
    assert r.status_code == 503 and r.json()["error"]["code"] == "graph_unavailable"
    assert "7687" not in r.text
    assert r.headers["access-control-allow-origin"] == "https://web.example"
    assert pg.status_code == 500 and pg.json()["error"]["code"] == "internal_error"
