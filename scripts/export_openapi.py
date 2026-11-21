"""Write the API's OpenAPI schema to apps/web/src/lib/api-contract/openapi.json (Phase 14 contract check).

The web app generates TypeScript types from it (`npm run api:types`); CI regenerates both and
fails when they differ from the committed files, so web and API cannot drift apart silently.

Usage: uv run --project apps/api python scripts/export_openapi.py [--check]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.core.config import Settings
from app.main import create_app

OUT = Path(__file__).resolve().parents[1] / "apps" / "web" / "src" / "lib" / "api-contract" / "openapi.json"


def schema_text() -> str:
    app = create_app(Settings(_env_file=None))  # no secrets needed: the schema is static
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    text = schema_text()
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT} is stale: run scripts/export_openapi.py and npm run api:types")
            return 1
        print("OpenAPI schema is up to date.")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(OUT.parents[5])} ({len(text)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
