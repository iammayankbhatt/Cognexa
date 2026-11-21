"""Load data/subjects/<subject>/concepts.yaml into Neo4j. Idempotent (MERGE).

Usage:
  uv run --project apps/api python scripts/seed_neo4j.py [--subject dsa] [--prune] [--wipe] [--allow-remote]

--prune         also delete human-sourced edges that are no longer in the file
--wipe          DELETE EVERYTHING in the database first (asks you to type WIPE to confirm)
--allow-remote  required when NEO4J_URI points at a cloud instance (neo4j+s:// / neo4j+ssc://)
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.content.loader import load_chunks
from app.core.config import Settings
from app.graph.driver import GraphNotConfiguredError, create_driver
from app.graph.loader import is_demo_subject, load_subject
from app.graph.repository import GraphRepository
from app.graph.seed import InvalidGraphError, seed_chunks, seed_subject


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    uri = settings.neo4j_uri or ""
    remote = uri.startswith(("neo4j+s://", "neo4j+ssc://", "bolt+s://"))
    if remote and not args.allow_remote:
        print("Refusing to touch a remote Neo4j instance without --allow-remote.")
        return 2
    if (remote or args.allow_remote) and is_demo_subject(args.subject):
        print(f"Refusing to seed demo subject '{args.subject}' remotely: demo packs are dev-only.")
        return 2
    try:
        driver = create_driver(settings)
    except GraphNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 2
    repo = GraphRepository(driver)
    try:
        if args.wipe:
            print(f"--wipe will delete ALL nodes and relationships in the database at {uri}.")
            if input("Type WIPE to confirm: ").strip() != "WIPE":
                print("Aborted; nothing was deleted.")
                return 1
            await repo.wipe()
            print("Database wiped.")
        doc = load_subject(args.subject)
        result = await seed_subject(repo, doc, prune=args.prune)
        chunks_up, chunks_del = await seed_chunks(repo, load_chunks(args.subject))
    except InvalidGraphError as exc:
        print("ERROR: concepts.yaml is invalid:")
        for err in exc.errors:
            print(f"  - {err}")
        return 1
    finally:
        await driver.close()
    print(
        f"Seeded subject '{args.subject}': {result.concepts} concepts, "
        f"{result.prerequisite_edges} PREREQUISITE_OF, {result.related_edges} RELATED_TO"
        + (f", pruned {result.pruned_edges}" if args.prune else "")
        + f"; {chunks_up} chunks ({chunks_del} stale removed)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--subject", default="dsa")
    parser.add_argument("--prune", action="store_true")
    parser.add_argument("--wipe", action="store_true")
    parser.add_argument("--allow-remote", action="store_true")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
