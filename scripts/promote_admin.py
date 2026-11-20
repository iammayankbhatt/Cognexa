"""Give an existing account a role by e-mail (default: admin). Creates the first production admin.

The person must have signed up (and confirmed the e-mail) first. Idempotent; the change is
written to audit_log. Like the seed scripts it refuses a non-local database unless
--allow-remote is given, and it reads DATABASE_URL from apps/api/.env or, for production,
from the file named by COGNEXA_ENV_FILE.

Usage:
  uv run --project apps/api python scripts/promote_admin.py you@example.com
  COGNEXA_ENV_FILE=apps/api/.env.production \
    uv run --project apps/api python scripts/promote_admin.py you@example.com --allow-remote
  ... --role student            # demote again
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

from app.auth.promote import ROLES, UserNotFoundError, set_role_by_email
from app.core.config import Settings
from app.db.engine import create_engine

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


async def run(args: argparse.Namespace) -> int:
    url = Settings().database_url
    if not url:
        print("ERROR: DATABASE_URL is not set.")
        return 2
    host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname or ""
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"Refusing to change roles on non-local host '{host}' without --allow-remote.")
        return 2
    engine = create_engine(url, pool_size=1, max_overflow=0)
    try:
        change = await set_role_by_email(engine, args.email, args.role)
    except UserNotFoundError:
        print("No account with that e-mail. Sign up on the site (and confirm the e-mail) first.")
        return 1
    finally:
        await engine.dispose()
    if change.changed:
        print(f"Role changed: {change.old_role} -> {change.new_role} (user {change.user_id}).")
        print("It takes effect within 30 s (the API's role cache); reload the page.")
    else:
        print(f"Already {change.new_role}; nothing changed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("email")
    parser.add_argument("--role", choices=ROLES, default="admin")
    parser.add_argument("--allow-remote", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
