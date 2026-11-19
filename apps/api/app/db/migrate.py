"""Apply supabase/migrations/*.sql to a plain Postgres (local docker / CI).

Supabase projects are migrated with the Supabase CLI (`supabase db push`), not with this runner.
Applied versions are recorded in public.schema_migrations together with a checksum; editing an
already-applied migration is an error (write a new migration instead).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import asyncpg

from app.db.engine import to_asyncpg_dsn
from app.graph.loader import REPO_ROOT

MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"
AUTH_SHIM = REPO_ROOT / "supabase" / "shim" / "auth_shim.sql"
LOCK_KEY = 727274  # arbitrary advisory-lock id so two runners cannot interleave


class MigrationError(RuntimeError):
    pass


def list_migrations(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    return sorted(directory.glob("*.sql"))


def checksum(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()


def _read_inputs(directory: Path, shim: Path | None) -> tuple[str | None, list[tuple[str, str]]]:
    """Read the shim and every migration file (blocking IO, done before any async work)."""
    shim_sql = shim.read_text(encoding="utf-8") if shim is not None and shim.exists() else None
    files = [(p.stem, p.read_text(encoding="utf-8")) for p in list_migrations(directory)]
    return shim_sql, files


async def apply_migrations(
    url: str,
    *,
    directory: Path = MIGRATIONS_DIR,
    shim: Path | None = AUTH_SHIM,
    apply_shim: bool | None = None,
) -> list[str]:
    """Apply all pending migrations in order and return the versions applied by this call.

    apply_shim: True/False forces; None (default) applies the auth shim only if auth.users is
    missing.
    """
    shim_sql, files = _read_inputs(directory, shim)

    conn = await asyncpg.connect(to_asyncpg_dsn(url), statement_cache_size=0)
    try:
        await conn.fetchval("select pg_advisory_lock($1)", LOCK_KEY)

        # A database migrated by the Supabase CLI records its history in supabase_migrations;
        # applying our files again would fail half-way (types already exist). Refuse cleanly.
        if await conn.fetchval("select to_regnamespace('supabase_migrations') is not null"):
            raise MigrationError(
                "this database is managed by the Supabase CLI (schema supabase_migrations "
                "exists); use `supabase migration up` (local) or `supabase db push` instead"
            )

        has_auth = await conn.fetchval("select to_regclass('auth.users') is not null")
        use_shim = apply_shim if apply_shim is not None else not has_auth
        if use_shim:
            if shim_sql is None:
                raise MigrationError("auth schema missing and no shim file available")
            await conn.execute(shim_sql)

        await conn.execute(
            "create table if not exists public.schema_migrations ("
            " version text primary key,"
            " checksum text not null,"
            " applied_at timestamptz not null default now());"
            "alter table public.schema_migrations enable row level security;"
        )
        rows = await conn.fetch("select version, checksum from public.schema_migrations")
        applied = {r["version"]: r["checksum"] for r in rows}

        newly_applied: list[str] = []
        for version, sql in files:
            digest = checksum(sql)
            if version in applied:
                if applied[version] != digest:
                    raise MigrationError(
                        f"migration {version} was modified after being applied; "
                        "add a new migration instead"
                    )
                continue
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "insert into public.schema_migrations (version, checksum) values ($1, $2)",
                    version,
                    digest,
                )
            newly_applied.append(version)
        return newly_applied
    finally:
        try:
            await conn.fetchval("select pg_advisory_unlock($1)", LOCK_KEY)
        finally:
            await conn.close()
