"""Usage guard: limiter unit tests, then every quota branch against a throwaway Postgres."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import uuid
from collections.abc import AsyncIterator

import asyncpg
import pytest

from app.auth.deps import CurrentUser
from app.core.config import Settings
from app.core.errors import AppError
from app.db.engine import to_asyncpg_dsn
from app.db.migrate import apply_migrations
from app.db.session import Database
from app.llm.types import LLMResult
from app.usage.guard import UsageGuard, next_utc_midnight
from app.usage.limiter import SlidingWindowLimiter
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401  (fixture re-used for the HTTP test)

NOW = dt.datetime(2026, 11, 20, 22, 0, tzinfo=dt.UTC)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


# ---------------------------------------------------------------- limiter (no database)


async def test_sliding_window_limits_and_frees_slots() -> None:
    clock = Clock()
    lim = SlidingWindowLimiter(60, clock)
    assert [(await lim.acquire("u", 2))[0] for _ in range(3)] == [True, True, False]
    clock.t = 30
    allowed, retry = await lim.acquire("u", 2)
    assert not allowed and retry == pytest.approx(30)
    assert (await lim.acquire("other", 2))[0]  # per user
    clock.t = 60.5
    assert (await lim.acquire("u", 2))[0]
    await lim.release("u")
    assert (await lim.acquire("u", 2))[0]


# ---------------------------------------------------------------- guard against Postgres


class G:
    def __init__(self, guard: UsageGuard, conn: asyncpg.Connection) -> None:
        self.guard = guard
        self.conn = conn

    async def user(self, role: str = "student", override: dict | None = None) -> CurrentUser:  # type: ignore[type-arg]
        email = f"u{uuid.uuid4().hex[:8]}@example.com"
        uid = await self.conn.fetchval(
            "insert into auth.users (email) values ($1) returning id", email
        )
        await self.conn.execute(
            "update profiles set role = $1, quota_override = $2::jsonb where id = $3",
            role,
            json.dumps(override) if override else None,
            uid,
        )
        return CurrentUser(id=uid, email=email, role=role, profile={"quota_override": override})

    async def setting(self, key: str, value: dict) -> None:  # type: ignore[type-arg]
        await self.conn.execute(
            "insert into app_settings (key, value) values ($1, $2::jsonb) "
            "on conflict (key) do update set value = excluded.value",
            key,
            json.dumps(value),
        )

    async def requests(self, user: CurrentUser) -> int:
        return int(
            await self.conn.fetchval(
                "select coalesce(sum(ai_requests), 0) from usage_daily where user_id = $1", user.id
            )
        )


@pytest.fixture
async def g(fresh_db_url: str) -> AsyncIterator[G]:
    await apply_migrations(fresh_db_url)
    db = Database(Settings(_env_file=None, database_url=fresh_db_url))
    conn = await asyncpg.connect(to_asyncpg_dsn(fresh_db_url), statement_cache_size=0)
    try:
        yield G(UsageGuard(db, now=lambda: NOW), conn)
    finally:
        await conn.close()
        await db.dispose()


def result(tin: int = 100, tout: int = 40, cost: float = 0.0001, cached: bool = False) -> LLMResult:
    return LLMResult("answer", "fake", "m", tin, tout, est_cost_usd=cost, cached=cached)


async def expect_429(coro, code: str) -> AppError:  # type: ignore[no-untyped-def]
    with pytest.raises(AppError) as info:
        await coro
    assert (info.value.status_code, info.value.code) == (429, code)
    assert info.value.details and "reset_at" in info.value.details
    assert info.value.headers and int(info.value.headers["Retry-After"]) >= 1
    return info.value


@requires_postgres
async def test_admit_record_and_summary(g: G) -> None:
    u = await g.user()
    async with g.guard.request(u, "what is a heap?") as ticket:
        await ticket.record(result(100, 40, 0.0002))
    async with g.guard.request(u, "and a stack?") as ticket:
        await ticket.mark_cached()  # cache hit: one request, no tokens
    s = await g.guard.usage_summary(u)
    today = s["today"]
    assert (today["ai_requests"], today["tokens_in"], today["tokens_out"]) == (2, 100, 40)
    assert today["est_cost_usd"] == pytest.approx(0.0002)
    assert today["remaining"] == 38 and today["resets_at"] == next_utc_midnight(NOW)
    assert s["limits"]["daily_ai_requests"] == 40 and len(s["history"]) == 1
    glob = await g.conn.fetchrow("select * from global_usage_daily where date = $1", NOW.date())
    assert (glob["ai_requests"], glob["tokens_in"], glob["tokens_out"]) == (2, 100, 40)
    calls = await g.conn.fetch("select * from llm_calls where user_id = $1 order by id", u.id)
    assert [(c["cached"], c["tokens_in"], c["purpose"]) for c in calls] == [
        (False, 100, "tutor"),
        (True, 0, "tutor"),
    ]


@requires_postgres
async def test_daily_quota_exceeded_with_reset_at_midnight(g: G) -> None:
    u = await g.user(override={"daily_ai_requests": 2})
    for _ in range(2):
        async with g.guard.request(u, "q") as t:
            await t.record(result())
    err = await expect_429(g.guard.admit(u, "q"), "QUOTA_EXCEEDED")
    assert err.details["reset_at"] == next_utc_midnight(NOW).isoformat()  # type: ignore[index]
    assert int(err.headers["Retry-After"]) == 2 * 3600  # type: ignore[index]  (22:00 -> 00:00)
    assert await g.requests(u) == 2


@requires_postgres
async def test_global_cap_blocks_everyone(g: G) -> None:
    await g.setting("quota.global_daily_cap", {"ai_requests": 1})
    a, b = await g.user(), await g.user()
    async with g.guard.request(a, "q") as t:
        await t.record(result())
    await expect_429(g.guard.admit(b, "q"), "GLOBAL_CAP")
    assert await g.requests(b) == 0


@requires_postgres
async def test_per_minute_limit_does_not_consume_daily_quota(g: G) -> None:
    u = await g.user(override={"per_minute": 2})
    for _ in range(2):
        async with g.guard.request(u, "q") as t:
            await t.record(result())
    err = await expect_429(g.guard.admit(u, "q"), "RATE_LIMITED")
    assert 0 < err.details["retry_after_s"] <= 60  # type: ignore[index]
    assert await g.requests(u) == 2


@requires_postgres
async def test_input_too_long_is_rejected_and_not_counted(g: G) -> None:
    u = await g.user()
    with pytest.raises(AppError) as info:
        await g.guard.admit(u, "x" * 2001)
    assert (info.value.status_code, info.value.code) == (413, "INPUT_TOO_LONG")
    assert await g.requests(u) == 0
    async with g.guard.request(u, "x" * 2000) as t:  # the limit itself is fine
        await t.record(result())


@requires_postgres
async def test_failed_call_is_refunded(g: G) -> None:
    u = await g.user()
    with pytest.raises(RuntimeError):
        async with g.guard.request(u, "q"):
            raise RuntimeError("provider down")
    assert await g.requests(u) == 0
    assert (
        await g.conn.fetchval(
            "select ai_requests from global_usage_daily where date = $1", NOW.date()
        )
        == 0
    )


@requires_postgres
async def test_role_multiplier_and_override(g: G) -> None:
    reviewer = await g.user(role="reviewer")
    assert (await g.guard.limits_for(reviewer)).daily == 200  # 40 x 5
    special = await g.user(override={"daily_ai_requests": 3})
    assert (await g.guard.limits_for(special)).daily == 3


@requires_postgres
async def test_parallel_requests_cannot_exceed_the_daily_quota(g: G) -> None:
    u = await g.user(override={"daily_ai_requests": 5, "per_minute": 100})

    async def attempt() -> str:
        try:
            async with g.guard.request(u, "q") as t:
                await t.record(result())
            return "ok"
        except AppError as e:
            return e.code

    outcomes = await asyncio.gather(*(attempt() for _ in range(20)))
    assert outcomes.count("ok") == 5 and outcomes.count("QUOTA_EXCEEDED") == 15
    assert await g.requests(u) == 5


@requires_postgres
async def test_parallel_requests_cannot_exceed_the_global_cap(g: G) -> None:
    await g.setting("quota.global_daily_cap", {"ai_requests": 3})
    users = [await g.user(override={"per_minute": 100}) for _ in range(4)]

    async def attempt(u: CurrentUser) -> str:
        try:
            await g.guard.admit(u, "q")
            return "ok"
        except AppError as e:
            return e.code

    outcomes = await asyncio.gather(*(attempt(u) for u in users for _ in range(5)))
    assert outcomes.count("ok") == 3 and outcomes.count("GLOBAL_CAP") == 17
    total = await g.conn.fetchval("select ai_requests from global_usage_daily")
    assert total == 3


# ---------------------------------------------------------------- HTTP


@requires_postgres
async def test_me_usage_endpoint(env: Env) -> None:  # noqa: F811
    _, h = await env.user("usage@example.com")
    assert (await env.client.get("/me/usage")).status_code == 401
    r = await env.client.get("/me/usage", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["today"]["ai_requests"] == 0 and body["today"]["remaining"] == 40
    assert body["limits"]["per_minute"] == 6 and body["history"] == []
    me = (await env.client.get("/me", headers=h)).json()
    assert me["usage"]["daily_quota"] == body["limits"]["daily_ai_requests"]
