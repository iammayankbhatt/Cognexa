"""Manual backups for the free tiers, which have none (Phase 13; docs/DEPLOYMENT.md "Backups").

Usage:
  uv run --project apps/api python scripts/backup.py create [--out backups] [--subject dsa] [--allow-remote]
  uv run --project apps/api python scripts/backup.py restore-graph <backup-dir> [--allow-remote]

create writes a timestamped folder with
  postgres.dump          pg_dump custom format of the public schema (restore with pg_restore), or
  postgres/<table>.jsonl one JSON object per row when pg_dump is not installed;
  concepts-<subject>.yaml the live graph (approved edges) in the concepts.yaml format;
  chunks-<subject>.json  every Neo4j Chunk, including approved LLM and admin-edited chunks;
  manifest.json          what was written, row counts and tool versions (never credentials).

restore-graph upserts the chunks from a backup into Neo4j (concepts come back with
`cp concepts-<subject>.yaml data/subjects/<subject>/concepts.yaml` + `scripts/seed_neo4j.py`).

Credentials come from apps/api/.env, or COGNEXA_ENV_FILE for production. They are passed to
pg_dump through PG* environment variables, so they never appear on a command line or in output.
--allow-remote is required for anything that is not localhost.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import asyncpg
from app.admin.graph_editor import GraphEditor
from app.core.config import Settings
from app.db.engine import to_asyncpg_dsn
from app.db.session import Database
from app.graph.driver import GraphNotConfiguredError, create_driver
from app.graph.repository import ChunkRecord, GraphRepository

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "host.docker.internal"}
CHUNK_BATCH = 20  # concepts per query (Neo4j queries return at most 500 chunks)


def is_local_pg(url: str) -> bool:
    return (urlparse(to_asyncpg_dsn(url)).hostname or "") in LOCAL_HOSTS


def is_local_neo4j(uri: str) -> bool:
    return not uri.startswith(
        ("neo4j+s://", "neo4j+ssc://", "bolt+s://", "bolt+ssc://")
    )


def pg_env(url: str) -> dict[str, str]:
    """PG* variables for pg_dump; the password is only ever in the child's environment."""
    u = urlparse(to_asyncpg_dsn(url))
    env = {**os.environ, "PGHOST": u.hostname or "localhost", "PGPORT": str(u.port or 5432),
           "PGDATABASE": (u.path or "/postgres").lstrip("/") or "postgres"}  # fmt: skip
    if u.username:
        env["PGUSER"] = unquote(u.username)
    if u.password:
        env["PGPASSWORD"] = unquote(u.password)
    return env


async def public_tables(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        "select tablename from pg_tables where schemaname = 'public' order by tablename"
    )
    return [r["tablename"] for r in rows]


async def export_jsonl(url: str, target: Path) -> dict[str, int]:
    target.mkdir(parents=True, exist_ok=True)
    conn = await asyncpg.connect(to_asyncpg_dsn(url), statement_cache_size=0)
    counts: dict[str, int] = {}
    try:
        for table in await public_tables(conn):
            # identifiers cannot be bound as parameters: the name comes from pg_tables and
            # must also be a plain lower-case identifier before it is quoted into the query
            if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", table):
                print(f"skipping table with an unusual name: {table!r}")
                continue
            table_ident = f'"{table}"'
            rows = await conn.fetch(f"select * from public.{table_ident}")
            with (target / f"{table}.jsonl").open("w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(
                        json.dumps(dict(r), default=str, ensure_ascii=False) + "\n"
                    )
            counts[table] = len(rows)
    finally:
        await conn.close()
    return counts


def pg_dump(url: str, target: Path) -> str:
    exe = shutil.which("pg_dump")
    assert exe is not None
    subprocess.run(
        [exe, "--format=custom", "--schema=public", "--no-owner", "--no-privileges",
         f"--file={target}"],
        env=pg_env(url), check=True, capture_output=True, text=True,
    )  # fmt: skip
    version = subprocess.run(
        [exe, "--version"], check=False, capture_output=True, text=True
    )
    return version.stdout.strip()


async def all_chunks(
    repo: GraphRepository, concept_ids: list[str]
) -> list[ChunkRecord]:
    out: list[ChunkRecord] = []
    for i in range(0, len(concept_ids), CHUNK_BATCH):
        out += await repo.get_chunks(concept_ids[i : i + CHUNK_BATCH], None, limit=500)
    return out


async def create(args: argparse.Namespace) -> int:
    settings = Settings()
    if not settings.database_url:
        print("ERROR: DATABASE_URL is not set.")
        return 2
    neo4j_uri = settings.neo4j_uri or ""
    remote = not is_local_pg(settings.database_url) or not is_local_neo4j(neo4j_uri)
    if remote and not args.allow_remote:
        print("Refusing to read a remote database without --allow-remote.")
        return 2
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d-%H%M%S")
    folder = Path(args.out) / f"cognexa-{stamp}"
    folder.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "created_at": stamp,
        "subject": args.subject,
        "files": [],
    }

    if shutil.which("pg_dump"):
        try:
            manifest["pg_dump"] = pg_dump(
                settings.database_url, folder / "postgres.dump"
            )
            manifest["files"].append("postgres.dump")
        except subprocess.CalledProcessError as exc:
            # pg_dump must not be older than the server; fall back to the portable export
            print(
                f"pg_dump failed ({(exc.stderr or '').strip().splitlines()[-1:]}); using JSONL"
            )
    if "postgres.dump" not in manifest["files"]:
        manifest["tables"] = await export_jsonl(
            settings.database_url, folder / "postgres"
        )
        manifest["files"].append("postgres/*.jsonl")

    try:
        driver = create_driver(settings)
    except GraphNotConfiguredError as exc:
        print(f"ERROR: {exc}")
        return 2
    try:
        repo = GraphRepository(driver)
        editor = GraphEditor(repo, Database(settings), None)
        text, errors = await editor.export_yaml(args.subject)
        (folder / f"concepts-{args.subject}.yaml").write_text(text, encoding="utf-8")
        ids = [c.id for c in await repo.list_concepts(args.subject)]
        chunks = await all_chunks(repo, ids)
        (folder / f"chunks-{args.subject}.json").write_text(
            json.dumps([c.model_dump() for c in chunks], indent=1, ensure_ascii=False),
            encoding="utf-8",
        )
    finally:
        await driver.close()
    manifest["files"] += [
        f"concepts-{args.subject}.yaml",
        f"chunks-{args.subject}.json",
    ]
    manifest["concepts"] = len(ids)
    manifest["chunks"] = len(chunks)
    manifest["graph_validation_errors"] = errors
    (folder / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Backup written to {folder}")
    print(
        f"  {len(ids)} concepts, {len(chunks)} chunks; postgres: {manifest['files'][0]}"
    )
    return 0


async def restore_graph(args: argparse.Namespace) -> int:
    settings = Settings()
    if not is_local_neo4j(settings.neo4j_uri or "") and not args.allow_remote:
        print("Refusing to write to a remote Neo4j instance without --allow-remote.")
        return 2
    files = sorted(Path(args.backup).glob("chunks-*.json"))
    if not files:
        print(f"No chunks-*.json in {args.backup}")
        return 1
    driver = create_driver(settings)
    try:
        repo = GraphRepository(driver)
        restored = 0
        for f in files:
            for item in json.loads(f.read_text(encoding="utf-8")):
                await repo.upsert_chunk(ChunkRecord(**item))
                restored += 1
    finally:
        await driver.close()
    print(
        f"Restored {restored} chunks into Neo4j (existing chunks are updated in place)."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("create")
    c.add_argument("--out", default="backups")
    c.add_argument("--subject", default="dsa")
    c.add_argument("--allow-remote", action="store_true")
    r = sub.add_parser("restore-graph")
    r.add_argument("backup")
    r.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()
    return asyncio.run(
        create(args) if args.command == "create" else restore_graph(args)
    )


if __name__ == "__main__":
    sys.exit(main())
