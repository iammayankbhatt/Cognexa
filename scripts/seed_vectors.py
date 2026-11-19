"""Embed content_chunks with the configured embedding provider.

Batched, retrying and resumable: only chunks whose embedding is missing or was computed from older
text are embedded (tracked by content hash), so re-running is cheap and safe. Refuses to run when the
provider, EMBEDDING_DIM, the code and the database column disagree about the vector size.
Refuses a non-local database without --allow-remote.

Usage: uv run --project apps/api python scripts/seed_vectors.py [--limit N] [--allow-remote]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from urllib.parse import urlparse

from app.content.vectors import DimensionMismatchError, check_dimensions, embed_pending
from app.core.config import Settings
from app.db.engine import engine_from_settings, session_factory
from app.llm.embeddings import EmbeddingProviderUnavailableError, get_embedding_provider

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres"}


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    url = settings.database_url or ""
    host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname or ""
    if not url or "REPLACE_ME" in url:
        print("ERROR: DATABASE_URL is not set.")
        return 2
    if host not in LOCAL_HOSTS and not args.allow_remote:
        print(f"Refusing to embed into non-local host '{host}' without --allow-remote.")
        return 2
    try:
        provider = get_embedding_provider(settings)
    except EmbeddingProviderUnavailableError as exc:
        print(f"ERROR: {exc}")
        return 2

    engine = engine_from_settings(settings)
    try:
        async with session_factory(engine)() as session:
            try:
                await check_dimensions(session, provider, settings.embedding_dim)
            except DimensionMismatchError as exc:
                print(f"ERROR: {exc}")
                return 2
            result = await embed_pending(session, provider, limit=args.limit)
    finally:
        await engine.dispose()
    print(
        f"Embedded {result.embedded} chunk(s) in {result.batches} batch(es) with "
        f"'{provider.model}' (dim {provider.dim}); {result.skipped_unchanged} unchanged/skipped"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="embed at most N chunks")
    parser.add_argument("--allow-remote", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
