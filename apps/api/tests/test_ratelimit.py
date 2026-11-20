"""Per-minute limits on expensive non-AI endpoints (Phase 13)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.ratelimit import DEFAULT_LIMITS, RouteLimiter
from app.main import create_app
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


async def test_limiter_allows_the_limit_then_refuses_with_retry_after() -> None:
    clock = Clock()
    rl = RouteLimiter(clock)
    for _ in range(3):
        await rl.check("x", "user-1", 3)
    with pytest.raises(AppError) as exc:
        await rl.check("x", "user-1", 3)
    err = exc.value
    assert err.status_code == 429 and err.code == "RATE_LIMITED"
    assert err.headers == {"Retry-After": "60"}
    await rl.check("x", "user-2", 3)  # other keys are independent
    await rl.check("y", "user-1", 3)  # and so are other routes
    clock.now += 60
    await rl.check("x", "user-1", 3)  # the window slid


async def test_idle_keys_are_pruned() -> None:
    clock = Clock()
    rl = RouteLimiter(clock)
    for ip in range(100):
        await rl.check("health_deep", f"10.0.0.{ip}", 30)
    assert len(rl.window._hits) == 100
    clock.now += 400  # past the prune interval and the window
    await rl.check("health_deep", "10.0.0.200", 30)
    assert list(rl.window._hits) == ["health_deep:10.0.0.200"]


async def test_public_readiness_endpoint_is_limited_per_ip() -> None:
    app = create_app(Settings(_env_file=None))
    app.state.route_limits = {**DEFAULT_LIMITS, "health_deep": 2}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        codes = [(await c.get("/health/deep")).status_code for _ in range(3)]
        assert codes[:2] == [200, 200]
        assert codes[2] == 429
        r = await c.get("/health/deep")
        assert r.json()["error"]["code"] == "RATE_LIMITED" and "Retry-After" in r.headers
        assert (await c.get("/health")).status_code == 200  # liveness is never limited


@requires_postgres
async def test_data_export_is_limited_per_user(env: Env) -> None:  # noqa: F811
    app = env.client._transport.app  # type: ignore[attr-defined]
    app.state.route_limits = {**DEFAULT_LIMITS, "me_export": 1}
    _, ada = await env.user("ada-rl@example.com")
    _, bob = await env.user("bob-rl@example.com")
    assert (await env.client.get("/me/export", headers=ada)).status_code == 200
    assert (await env.client.get("/me/export", headers=ada)).status_code == 429
    assert (await env.client.get("/me/export", headers=bob)).status_code == 200
