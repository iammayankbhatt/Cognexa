"""Integration tests for /me and /admin/users against a throwaway migrated Postgres.

Tokens are signed with a test ES256 key and verified through a stubbed JWKS, exactly as real
Supabase tokens are (see tests/auth_helpers.py). Uses the plain-Postgres auth shim, so the
account-deletion path tested here is the SQL fallback; the Supabase admin-API path is exercised
manually against the local Supabase stack (progressfile Session 8).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import asyncpg
import httpx
import pytest

from app.auth.jwks import JwksCache
from app.core.config import Settings
from app.db.engine import to_asyncpg_dsn
from app.db.migrate import apply_migrations
from app.main import create_app
from tests.auth_helpers import ISSUER_BASE, StubFetcher, TestKeys, jwks_doc
from tests.conftest import requires_postgres

pytestmark = requires_postgres


class Env:
    def __init__(self, client: httpx.AsyncClient, db: asyncpg.Connection, keys: TestKeys) -> None:
        self.client = client
        self.db = db
        self.keys = keys

    async def user(self, email: str, role: str = "student") -> tuple[uuid.UUID, dict[str, str]]:
        uid: uuid.UUID = await self.db.fetchval(
            "insert into auth.users (email) values ($1) returning id", email
        )
        if role != "student":
            await self.db.execute("update profiles set role = $1 where id = $2", role, uid)
        return uid, {"Authorization": f"Bearer {self.keys.token(uid, email=email)}"}


@pytest.fixture
async def env(fresh_db_url: str) -> AsyncIterator[Env]:
    await apply_migrations(fresh_db_url)
    keys = TestKeys()
    settings = Settings(
        _env_file=None,
        database_url=fresh_db_url,
        supabase_url=ISSUER_BASE,
        profile_cache_ttl_s=0,  # always read the role fresh in tests
    )
    app = create_app(settings)
    app.state.jwks = JwksCache("http://jwks.test", fetcher=StubFetcher(jwks_doc(keys)))
    db = await asyncpg.connect(to_asyncpg_dsn(fresh_db_url), statement_cache_size=0)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://api.test") as client:
            yield Env(client, db, keys)
    finally:
        await db.close()
        await app.state.db.dispose()


async def test_me_requires_a_valid_token(env: Env) -> None:
    r = await env.client.get("/me")
    assert r.status_code == 401
    body = r.json()["error"]
    assert body["code"] == "unauthorized" and body["request_id"]
    r = await env.client.get("/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401
    expired = env.keys.token(uuid.uuid4(), expires_in=-300)
    r = await env.client.get("/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


async def test_me_returns_profile_and_usage(env: Env) -> None:
    uid, h = await env.user("ada@example.com")
    r = await env.client.get("/me", headers=h)
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["id"] == str(uid) and me["email"] == "ada@example.com"
    assert me["role"] == "student" and me["theme"] == "neon-noir"
    assert me["display_name"] == "ada"  # from the signup trigger
    assert me["onboarding_completed"] is False
    assert me["usage"]["ai_requests"] == 0 and me["usage"]["daily_quota"] == 40


async def test_token_for_deleted_user_is_rejected(env: Env) -> None:
    ghost = uuid.uuid4()  # valid signature, but no auth user with this id
    r = await env.client.get("/me", headers={"Authorization": f"Bearer {env.keys.token(ghost)}"})
    assert r.status_code == 401


async def test_patch_me_updates_theme_and_name(env: Env) -> None:
    _, h = await env.user("grace@example.com")
    r = await env.client.patch(
        "/me", headers=h, json={"theme": "titanium-light", "display_name": "  Grace H  "}
    )
    assert r.status_code == 200, r.text
    assert r.json()["theme"] == "titanium-light" and r.json()["display_name"] == "Grace H"
    for bad in (
        {"theme": "pink"},
        {"display_name": ""},
        {"role": "admin"},
        {"display_name": "x" * 81},
        {"display_name": "   "},
    ):
        r = await env.client.patch("/me", headers=h, json=bad)
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "validation_error"
    r = await env.client.get("/me", headers=h)
    assert r.json()["role"] == "student" and r.json()["theme"] == "titanium-light"


async def test_onboarding_complete(env: Env) -> None:
    _, h = await env.user("linus@example.com")
    r = await env.client.post(
        "/me/onboarding-complete", headers=h, json={"experience_level": "intermediate"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["onboarding_completed"] is True
    assert r.json()["experience_level"] == "intermediate"
    r = await env.client.post(
        "/me/onboarding-complete", headers=h, json={"experience_level": "wizard"}
    )
    assert r.status_code == 422


async def test_student_and_reviewer_cannot_use_admin_api(env: Env) -> None:
    _, student = await env.user("s@example.com")
    _, reviewer = await env.user("r@example.com", role="reviewer")
    for h in (student, reviewer):
        r = await env.client.get("/admin/users", headers=h)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "forbidden"
        r = await env.client.patch(
            f"/admin/users/{uuid.uuid4()}", headers=h, json={"role": "admin"}
        )
        assert r.status_code == 403
    assert await env.client.get("/admin/users") is not None
    assert (await env.client.get("/admin/users")).status_code == 401


async def test_admin_lists_searches_and_updates_users(env: Env) -> None:
    admin_id, admin = await env.user("boss@example.com", role="admin")
    target, target_h = await env.user("alan@example.com")
    await env.user("barbara@example.com")

    r = await env.client.get("/admin/users", headers=admin, params={"page_size": 2})
    page = r.json()
    assert r.status_code == 200 and page["total"] == 3 and len(page["items"]) == 2
    r = await env.client.get("/admin/users", headers=admin, params={"q": "alan"})
    assert [u["email"] for u in r.json()["items"]] == ["alan@example.com"]

    r = await env.client.patch(
        f"/admin/users/{target}",
        headers=admin,
        json={
            "role": "reviewer",
            "study_group": "adaptive",
            "quota_override": {"daily_ai_requests": 100},
        },
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["role"] == "reviewer" and out["study_group"] == "adaptive"
    assert (
        out["quota_override"] == {"daily_ai_requests": 100} and out["email"] == "alan@example.com"
    )
    me = (await env.client.get("/me", headers=target_h)).json()
    assert me["role"] == "reviewer" and me["usage"]["daily_quota"] == 100

    audit = await env.db.fetch("select actor, action, target, details from audit_log")
    assert len(audit) == 1
    assert audit[0]["actor"] == admin_id and audit[0]["action"] == "admin.update_user"
    assert audit[0]["target"] == str(target)

    r = await env.client.patch(
        f"/admin/users/{target}", headers=admin, json={"clear_quota_override": True}
    )
    assert r.json()["quota_override"] is None
    assert (await env.client.get("/me", headers=target_h)).json()["usage"]["daily_quota"] == 200

    r = await env.client.patch(f"/admin/users/{admin_id}", headers=admin, json={"role": "student"})
    assert r.status_code == 403  # cannot demote yourself
    r = await env.client.patch(
        f"/admin/users/{uuid.uuid4()}", headers=admin, json={"role": "admin"}
    )
    assert r.status_code == 404
    r = await env.client.patch(f"/admin/users/{target}", headers=admin, json={})
    assert r.status_code == 422
    r = await env.client.patch(f"/admin/users/{target}", headers=admin, json={"role": "god"})
    assert r.status_code == 422


async def test_export_and_delete_account(env: Env) -> None:
    uid, h = await env.user("leaving@example.com")
    await env.db.execute(
        "insert into usage_daily (user_id, date, ai_requests) values ($1, current_date, 3)", uid
    )
    r = await env.client.get("/me/export", headers=h)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["profile"]["id"] == str(uid) and data["usage_daily"][0]["ai_requests"] == 3
    assert "chat_messages" in data

    r = await env.client.request("DELETE", "/me", headers=h, json={"confirm": "nope"})
    assert r.status_code == 422
    r = await env.client.request("DELETE", "/me", headers=h, json={"confirm": "DELETE"})
    assert r.status_code == 200, r.text
    assert await env.db.fetchval("select count(*) from auth.users where id = $1", uid) == 0
    assert await env.db.fetchval("select count(*) from profiles where id = $1", uid) == 0
    assert await env.db.fetchval("select count(*) from usage_daily where user_id = $1", uid) == 0
    assert (
        await env.db.fetchval("select count(*) from audit_log where action = 'user.delete_account'")
        == 1
    )
    assert (await env.client.get("/me", headers=h)).status_code == 401


async def test_concepts_requires_auth_and_lists_seeded_concepts(env: Env) -> None:
    assert (await env.client.get("/concepts")).status_code == 401
    await env.db.execute("insert into subjects (id, name) values ('dsa', 'DSA')")
    await env.db.execute(
        "insert into concepts (id, subject_id, name, cluster, difficulty, order_index)"
        " values ('b', 'dsa', 'Beta', 'x', 2, 2), ('a', 'dsa', 'Alpha', 'x', 1, 1)"
    )
    _, h = await env.user("c@example.com")
    r = await env.client.get("/concepts", headers=h)
    assert r.status_code == 200
    assert [c["id"] for c in r.json()] == ["a", "b"]  # ordered by order_index
    assert (
        await env.client.get("/concepts", headers=h, params={"subject_id": "Bad!"})
    ).status_code == 422
