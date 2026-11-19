"""Report which environment variables are SET, MISSING or PLACEHOLDER.

Prints only the variable name, the phase that needs it and a status. Never prints values.
Usage: uv run --project apps/api python scripts/check_env.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (variable, file, phase that needs it, required for local fake-mode work?)
VARS: list[tuple[str, str, int, bool]] = [
    ("DATABASE_URL", "apps/api/.env", 2, True),
    ("NEO4J_URI", "apps/api/.env", 2, True),
    ("NEO4J_USER", "apps/api/.env", 2, True),
    ("NEO4J_PASSWORD", "apps/api/.env", 2, True),
    ("EMBEDDING_PROVIDER", "apps/api/.env", 3, True),
    ("EMBEDDING_DIM", "apps/api/.env", 2, True),
    ("EMBEDDING_MODEL", "apps/api/.env", 3, False),
    ("SUPABASE_URL", "apps/api/.env", 4, False),
    ("SUPABASE_SERVICE_ROLE_KEY", "apps/api/.env", 4, False),
    ("SUPABASE_JWKS_URL", "apps/api/.env", 4, False),
    ("SUPABASE_JWT_SECRET", "apps/api/.env", 4, False),
    ("LLM_PRIMARY_PROVIDER", "apps/api/.env", 5, True),
    ("LLM_PRIMARY_MODEL", "apps/api/.env", 5, True),
    ("LLM_FALLBACK_PROVIDER", "apps/api/.env", 5, True),
    ("LLM_FALLBACK_MODEL", "apps/api/.env", 5, True),
    ("LLM_JUDGE_PROVIDER", "apps/api/.env", 5, True),
    ("LLM_JUDGE_MODEL", "apps/api/.env", 5, True),
    ("GROQ_API_KEY", "apps/api/.env", 5, False),
    ("GEMINI_API_KEY", "apps/api/.env", 5, False),
    ("AGENTIC_MODE", "apps/api/.env", 6, False),
    ("STUDY_MODE", "apps/api/.env", 12, False),
    ("NEXT_PUBLIC_API_URL", "apps/web/.env.local", 4, True),
    ("NEXT_PUBLIC_SUPABASE_URL", "apps/web/.env.local", 4, False),
    ("NEXT_PUBLIC_SUPABASE_ANON_KEY", "apps/web/.env.local", 4, False),
]

PLACEHOLDER = "REPLACE_ME"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def classify(values: dict[str, str], name: str) -> str:
    if name not in values or values[name] == "":
        return "MISSING"
    if values[name] == PLACEHOLDER:
        return "PLACEHOLDER"
    return "SET"


def main() -> int:
    cache: dict[str, dict[str, str]] = {}
    print(f"{'VARIABLE':34} {'FILE':22} {'PHASE':>5}  STATUS")
    blocking_missing = False
    for name, rel, phase, needed_locally in VARS:
        if rel not in cache:
            cache[rel] = parse_env(ROOT / rel)
        status = classify(cache[rel], name)
        print(f"{name:34} {rel:22} {phase:>5}  {status}")
        if needed_locally and status == "MISSING":
            blocking_missing = True
    if blocking_missing:
        print("\nSome variables needed for local (fake-mode) work are MISSING.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
