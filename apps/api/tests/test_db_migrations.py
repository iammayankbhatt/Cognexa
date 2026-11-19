"""Migration, RLS, trigger and constraint tests against a throwaway database."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import insert, select, text

from app.db.engine import create_engine, to_asyncpg_dsn
from app.db.migrate import MIGRATIONS_DIR, MigrationError, apply_migrations, list_migrations
from app.db.tables import EMBEDDING_DIM, content_chunks, metadata

from .conftest import requires_postgres

pytestmark = requires_postgres

EXPECTED_TABLES = {t.name for t in metadata.sorted_tables}


@pytest.fixture
async def migrated_url(fresh_db_url: str) -> str:
    applied = await apply_migrations(fresh_db_url)
    assert len(applied) == len(list_migrations())
    return fresh_db_url


@pytest.fixture
async def conn(migrated_url: str) -> AsyncIterator[asyncpg.Connection]:
    c = await asyncpg.connect(to_asyncpg_dsn(migrated_url), statement_cache_size=0)
    yield c
    await c.close()


@asynccontextmanager
async def as_user(c: asyncpg.Connection, user_id: uuid.UUID | None) -> AsyncIterator[None]:
    """Run statements as the `authenticated` role with a JWT subject (or as anon), then roll back."""
    tx = c.transaction()
    await tx.start()
    try:
        if user_id is None:
            await c.execute("set local role anon")
        else:
            await c.execute("select set_config('request.jwt.claim.sub', $1, true)", str(user_id))
            await c.execute("set local role authenticated")
        yield
    finally:
        await tx.rollback()


async def make_user(c: asyncpg.Connection, email: str, meta: str = "{}") -> uuid.UUID:
    uid: uuid.UUID = await c.fetchval(
        "insert into auth.users (email, raw_user_meta_data) values ($1, $2::jsonb) returning id",
        email,
        meta,
    )
    return uid


async def seed_subject(c: asyncpg.Connection) -> None:
    await c.execute("insert into subjects (id, name) values ('s', 'S') on conflict do nothing")
    await c.execute(
        "insert into concepts (id, subject_id, name, cluster, difficulty) "
        "values ('c1', 's', 'C1', 'k', 1), ('c2', 's', 'C2', 'k', 2) on conflict do nothing"
    )


# ------------------------------------------------------------------ applying migrations
async def test_migrations_apply_and_are_idempotent(fresh_db_url: str) -> None:
    first = await apply_migrations(fresh_db_url)
    assert first and first == [p.stem for p in list_migrations()]
    assert await apply_migrations(fresh_db_url) == []


async def test_editing_an_applied_migration_is_rejected(fresh_db_url: str, tmp_path: Path) -> None:
    copy = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, copy)
    await apply_migrations(fresh_db_url, directory=copy)
    first = sorted(copy.glob("*.sql"))[0]
    first.write_text(first.read_text(encoding="utf-8") + "\n-- tampered\n", encoding="utf-8")
    with pytest.raises(MigrationError, match="modified after being applied"):
        await apply_migrations(fresh_db_url, directory=copy)


async def test_supabase_cli_managed_database_is_refused(fresh_db_url: str) -> None:
    """BUG-014: a database migrated by the Supabase CLI must not be migrated again by us."""
    c = await asyncpg.connect(to_asyncpg_dsn(fresh_db_url), statement_cache_size=0)
    try:
        await c.execute("create schema supabase_migrations")
    finally:
        await c.close()
    with pytest.raises(MigrationError, match="managed by the Supabase CLI"):
        await apply_migrations(fresh_db_url)
    c = await asyncpg.connect(to_asyncpg_dsn(fresh_db_url), statement_cache_size=0)
    try:  # refused before touching anything
        assert await c.fetchval("select to_regclass('public.schema_migrations')") is None
    finally:
        await c.close()


async def test_all_expected_tables_exist_with_rls(conn: asyncpg.Connection) -> None:
    rows = await conn.fetch(
        "select c.relname, c.relrowsecurity from pg_class c join pg_namespace n on n.oid = c.relnamespace "
        "where n.nspname = 'public' and c.relkind = 'r'"
    )
    found = {r["relname"]: r["relrowsecurity"] for r in rows}
    assert set(found) >= EXPECTED_TABLES
    assert not [name for name, rls in found.items() if not rls], "tables without RLS"


async def test_core_definitions_match_the_database(conn: asyncpg.Connection) -> None:
    for table in metadata.sorted_tables:
        rows = await conn.fetch(
            "select column_name from information_schema.columns "
            "where table_schema = 'public' and table_name = $1",
            table.name,
        )
        assert {r["column_name"] for r in rows} == {c.name for c in table.columns}, table.name


async def test_vector_column_dimension_and_hnsw_index(conn: asyncpg.Connection) -> None:
    dim = await conn.fetchval(
        "select atttypmod from pg_attribute "
        "where attrelid = 'content_chunks'::regclass and attname = 'embedding'"
    )
    assert dim == EMBEDDING_DIM
    index_def = await conn.fetchval(
        "select indexdef from pg_indexes where indexname = 'content_chunks_embedding_idx'"
    )
    assert "hnsw" in index_def and "vector_cosine_ops" in index_def


# ------------------------------------------------------------------ triggers
async def test_profile_created_for_new_auth_user(conn: asyncpg.Connection) -> None:
    named = await make_user(conn, "ada@example.com", '{"full_name": "Ada Lovelace"}')
    plain = await make_user(conn, "grace@example.com")
    assert (
        await conn.fetchval("select display_name from profiles where id = $1", named)
        == "Ada Lovelace"
    )
    assert await conn.fetchval("select display_name from profiles where id = $1", plain) == "grace"
    row = await conn.fetchrow("select role, theme, study_group from profiles where id = $1", plain)
    assert (row["role"], row["theme"], row["study_group"]) == ("student", "neon-noir", "none")


async def test_deleting_auth_user_cascades(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    uid = await make_user(conn, "gone@example.com")
    await conn.execute(
        "insert into notes (user_id, concept_id, subject_id, body) values ($1, 'c1', 's', 'hi')",
        uid,
    )
    await conn.execute("delete from auth.users where id = $1", uid)
    assert await conn.fetchval("select count(*) from profiles where id = $1", uid) == 0
    assert await conn.fetchval("select count(*) from notes where user_id = $1", uid) == 0


async def test_updated_at_trigger(conn: asyncpg.Connection) -> None:
    uid = await make_user(conn, "t@example.com")
    before = await conn.fetchval("select updated_at from profiles where id = $1", uid)
    await conn.execute("select pg_sleep(0.05)")
    await conn.execute("update profiles set display_name = 'x' where id = $1", uid)
    after = await conn.fetchval("select updated_at from profiles where id = $1", uid)
    assert after > before


# ------------------------------------------------------------------ row level security
async def test_users_only_see_their_own_rows(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    a = await make_user(conn, "a@example.com")
    b = await make_user(conn, "b@example.com")
    for uid, body in ((a, "note a"), (b, "note b")):
        await conn.execute(
            "insert into notes (user_id, concept_id, subject_id, body) values ($1, 'c1', 's', $2)",
            uid,
            body,
        )
        await conn.execute(
            "insert into mastery (user_id, concept_id, subject_id, score, attempts, correct) "
            "values ($1, 'c1', 's', 0.5, 2, 1)",
            uid,
        )
    async with as_user(conn, a):
        assert [r["body"] for r in await conn.fetch("select body from notes")] == ["note a"]
        assert await conn.fetchval("select count(*) from mastery") == 1
        assert await conn.fetchval("select count(*) from profiles") == 1
    async with as_user(conn, b):
        assert [r["body"] for r in await conn.fetch("select body from notes")] == ["note b"]


async def test_user_cannot_write_other_users_or_forbidden_tables(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    a = await make_user(conn, "a2@example.com")
    b = await make_user(conn, "b2@example.com")
    async with as_user(conn, a):
        # may write own note...
        await conn.execute(
            "insert into notes (user_id, concept_id, subject_id) values ($1, 'c1', 's')", a
        )
    async with as_user(conn, a):
        # ...but not a note for someone else
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(
                "insert into notes (user_id, concept_id, subject_id) values ($1, 'c1', 's')", b
            )
    async with as_user(conn, a):
        # mastery is backend-only: no insert policy
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(
                "insert into mastery (user_id, concept_id, subject_id) values ($1, 'c1', 's')", a
            )
    for table in ("content_chunks", "questions", "app_settings", "response_cache", "audit_log"):
        async with as_user(conn, a):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.fetch(f"select * from {table}")


async def test_anon_sees_nothing(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    await make_user(conn, "anon-target@example.com")
    for table in ("profiles", "subjects", "concepts", "notes", "mastery", "chat_threads"):
        async with as_user(conn, None):
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.fetch(f"select * from {table}")


async def test_signed_in_users_can_read_subjects_and_concepts(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    uid = await make_user(conn, "reader@example.com")
    async with as_user(conn, uid):
        assert await conn.fetchval("select count(*) from concepts") == 2


async def test_user_cannot_escalate_role_quota_or_study_group(conn: asyncpg.Connection) -> None:
    uid = await make_user(conn, "sneaky@example.com")
    async with as_user(conn, uid):
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("update profiles set role = 'admin' where id = $1", uid)
    async with as_user(conn, uid):
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(
                "update profiles set quota_override = '{\"x\": 1}' where id = $1", uid
            )
    async with as_user(conn, uid):
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute("update profiles set study_group = 'adaptive' where id = $1", uid)
    async with as_user(conn, uid):
        await conn.execute(
            "update profiles set display_name = 'Me', theme = 'titanium-light' where id = $1", uid
        )
        assert (
            await conn.fetchval("select theme from profiles where id = $1", uid) == "titanium-light"
        )
    # the backend (table owner / service role) may still change the role
    await conn.execute("update profiles set role = 'reviewer' where id = $1", uid)
    assert await conn.fetchval("select role from profiles where id = $1", uid) == "reviewer"


# ------------------------------------------------------------------ constraints
async def test_check_constraints_reject_bad_data(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    uid = await make_user(conn, "c@example.com")
    bad = [
        "insert into concepts (id, subject_id, name, cluster, difficulty) values ('x','s','X','k',9)",
        f"insert into mastery (user_id, concept_id, subject_id, score) values ('{uid}','c1','s',1.5)",
        f"insert into mastery (user_id, concept_id, subject_id, attempts, correct) "
        f"values ('{uid}','c1','s',1,2)",
        "insert into questions (id, concept_id, subject_id, type, difficulty, prompt, answer) "
        "values ('q','c1','s','mcq',5,'p','{}')",
        "update profiles set theme = 'rainbow'",
        "insert into study_settings (id) values (2)",
    ]
    for sql in bad:
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(sql)


async def test_study_settings_singleton_row_exists(conn: asyncpg.Connection) -> None:
    row = await conn.fetchrow("select id, enabled from study_settings")
    assert row["id"] == 1 and row["enabled"] is False


async def test_unique_and_foreign_key_constraints(conn: asyncpg.Connection) -> None:
    await seed_subject(conn)
    uid = await make_user(conn, "u@example.com")
    await conn.execute(
        "insert into notes (user_id, concept_id, subject_id) values ($1, 'c1', 's')", uid
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(
            "insert into notes (user_id, concept_id, subject_id) values ($1, 'c1', 's')", uid
        )
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await conn.execute(
            "insert into notes (user_id, concept_id, subject_id) values ($1, 'ghost', 's')", uid
        )


# ------------------------------------------------------------------ vectors through SQLAlchemy Core
async def test_embedding_round_trip_and_nearest_neighbour(migrated_url: str) -> None:
    engine = create_engine(migrated_url)
    try:
        async with engine.begin() as sa:
            await sa.execute(text("insert into subjects (id, name) values ('s','S')"))
            await sa.execute(
                text(
                    "insert into concepts (id, subject_id, name, cluster, difficulty) "
                    "values ('c1','s','C1','k',1)"
                )
            )

            def vec(hot: int) -> list[float]:
                v = [0.0] * EMBEDDING_DIM
                v[hot] = 1.0
                return v

            await sa.execute(
                insert(content_chunks),
                [
                    {
                        "id": f"k{i}",
                        "concept_id": "c1",
                        "subject_id": "s",
                        "kind": "overview",
                        "heading": "h",
                        "text": f"t{i}",
                        "embedding": vec(i),
                    }
                    for i in range(3)
                ],
            )
            row = (
                await sa.execute(
                    select(content_chunks.c.embedding).where(content_chunks.c.id == "k1")
                )
            ).scalar_one()
            assert len(row) == EMBEDDING_DIM and row[1] == 1.0
            nearest = (
                await sa.execute(
                    select(content_chunks.c.id)
                    .order_by(content_chunks.c.embedding.cosine_distance(vec(2)))
                    .limit(1)
                )
            ).scalar_one()
            assert nearest == "k2"
            with pytest.raises(Exception, match="dimensions"):
                await sa.execute(
                    insert(content_chunks).values(
                        id="bad",
                        concept_id="c1",
                        subject_id="s",
                        kind="x",
                        text="t",
                        embedding=[0.1, 0.2],
                    )
                )
    finally:
        await engine.dispose()
