"""First-admin promotion by e-mail (Phase 15, scripts/promote_admin.py)."""

from __future__ import annotations

import asyncpg
import pytest

from app.auth.promote import UserNotFoundError, set_role_by_email
from app.db.engine import create_engine, to_asyncpg_dsn
from app.db.migrate import apply_migrations

from .conftest import requires_postgres

pytestmark = requires_postgres


async def test_promote_by_email_is_case_insensitive_idempotent_and_audited(
    fresh_db_url: str,
) -> None:
    await apply_migrations(fresh_db_url)
    conn = await asyncpg.connect(to_asyncpg_dsn(fresh_db_url), statement_cache_size=0)
    engine = create_engine(fresh_db_url, pool_size=1, max_overflow=0)
    try:
        uid = await conn.fetchval(
            "insert into auth.users (email) values ($1) returning id", "Owner@Example.com"
        )
        assert await conn.fetchval("select role::text from profiles where id = $1", uid) == (
            "student"
        )

        first = await set_role_by_email(engine, "  owner@example.COM ", "admin")
        assert (first.user_id, first.old_role, first.new_role, first.changed) == (
            uid,
            "student",
            "admin",
            True,
        )
        assert await conn.fetchval("select role::text from profiles where id = $1", uid) == "admin"

        again = await set_role_by_email(engine, "owner@example.com", "admin")
        assert not again.changed

        rows = await conn.fetch("select actor, action, target, details from audit_log order by id")
        assert len(rows) == 1  # the no-op run wrote nothing
        assert rows[0]["actor"] is None
        assert rows[0]["action"] == "admin.update_user"
        assert rows[0]["target"] == str(uid)
        assert '"to": "admin"' in rows[0]["details"]

        with pytest.raises(UserNotFoundError):
            await set_role_by_email(engine, "nobody@example.com", "admin")
        with pytest.raises(ValueError):
            await set_role_by_email(engine, "owner@example.com", "root")  # type: ignore[arg-type]
    finally:
        await engine.dispose()
        await conn.close()
