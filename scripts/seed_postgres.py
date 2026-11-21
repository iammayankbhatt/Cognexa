"""Seed Postgres: subjects + concepts mirror from concepts.yaml, plus default app_settings.

Idempotent: re-running updates the mirror and never overwrites settings an admin has edited.
Run `scripts/migrate.py` first (plain Postgres) or apply migrations with the Supabase CLI.
Refuses a non-local host without --allow-remote.

Usage: uv run --project apps/api python scripts/seed_postgres.py [--subject dsa] [--allow-remote]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

from app.cache.repository import CacheRepository
from app.content.loader import load_chunks, load_questions
from app.core.config import Settings
from app.db.engine import engine_from_settings, session_factory
from app.db.repositories import (
    AppSettingsRepository,
    ConceptMirrorRepository,
    ContentRepository,
)
from app.graph.loader import is_demo_subject, load_subject
from app.graph.validation import validate_concept_file

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    url = settings.database_url or ""
    host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname or ""
    if not url or "REPLACE_ME" in url:
        print("ERROR: DATABASE_URL is not set.")
        return 2
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"Refusing to seed non-local host '{host}' without --allow-remote.")
        return 2
    if (host not in LOCAL_HOSTS or args.allow_remote) and is_demo_subject(args.subject):
        print(f"Refusing to seed demo subject '{args.subject}' remotely: demo packs are dev-only.")
        return 2

    doc = load_subject(args.subject)
    report = validate_concept_file(doc)
    if not report.ok:
        print("ERROR: concepts.yaml is invalid; run scripts/validate_graph.py")
        return 1

    engine = engine_from_settings(settings)
    try:
        async with session_factory(engine)() as session, session.begin():
            _, n_concepts = await ConceptMirrorRepository(session).upsert_from_file(doc)
            inserted = await AppSettingsRepository(session).ensure_defaults()
            content = ContentRepository(session)
            chunks = load_chunks(args.subject)
            changed = await content.changed_concepts(chunks)
            n_chunks = await content.upsert_chunks(chunks)
            # Cached answers/classifications built from old content must not be served again.
            n_invalidated = await CacheRepository(session).invalidate_concepts(
                changed, ("resp", "cls", "grade")
            )
            n_questions = await content.upsert_questions(
                [(doc.subject.id, cid, q) for cid, q in load_questions(args.subject)]
            )
    finally:
        await engine.dispose()
    print(
        f"Seeded Postgres: subject '{doc.subject.id}', {n_concepts} concepts, "
        f"{inserted} default setting(s) inserted, {n_chunks} chunks, {n_questions} questions; "
        f"{len(changed)} concept(s) with changed content, {n_invalidated} cache entries invalidated"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="dsa")
    parser.add_argument("--allow-remote", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
