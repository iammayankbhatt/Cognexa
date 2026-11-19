"""Apply supabase/migrations/*.sql to a PLAIN Postgres (local docker or CI).

For Supabase projects use the Supabase CLI instead: `supabase db push`.
Refuses to run against a non-local host unless --allow-remote is given.

Usage: uv run --project apps/api python scripts/migrate.py [--allow-remote] [--no-shim]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

from app.core.config import Settings
from app.db.migrate import MigrationError, apply_migrations

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


async def run(args: argparse.Namespace) -> int:
    url = Settings().database_url
    if not url or "REPLACE_ME" in url:
        print("ERROR: DATABASE_URL is not set.")
        return 2
    host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname or ""
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"Refusing to migrate non-local host '{host}' without --allow-remote.")
        print("Supabase projects: use `supabase db push` instead.")
        return 2
    try:
        applied = await apply_migrations(url, apply_shim=False if args.no_shim else None)
    except MigrationError as exc:
        print(f"ERROR: {exc}")
        return 1
    if applied:
        print("Applied: " + ", ".join(applied))
    else:
        print("Database is up to date; nothing to apply.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--no-shim", action="store_true", help="never apply the auth shim")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
