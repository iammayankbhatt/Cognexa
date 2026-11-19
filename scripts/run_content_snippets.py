"""Extract every Python/C++ snippet from the concept notes into apps/api/tests/content_snippets/
(gitignored) and run them. Exits non-zero if any snippet fails.

Usage: uv run --project apps/api python scripts/run_content_snippets.py [--subject dsa] [concept_id ...]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.content.snippets import collect_snippets, gpp, run_all, verify_code_questions
from app.graph.loader import REPO_ROOT

OUT = REPO_ROOT / "apps" / "api" / "tests" / "content_snippets"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="dsa")
    parser.add_argument("concepts", nargs="*")
    args = parser.parse_args()

    snippets = collect_snippets(args.subject, set(args.concepts) or None)
    if gpp() is None:
        print("NOTE: g++ not found; C++ snippets will be skipped.")
    results = run_all(snippets, Path(OUT))
    failed = [r for r in results if r.status == "failed"]
    skipped = [r for r in results if r.status == "skipped"]
    for r in results:
        if r.status != "passed":
            print(f"{r.status.upper():8} {r.snippet.filename}: {r.detail}")
    print(
        f"\n{len(results) - len(failed) - len(skipped)} passed, {len(failed)} failed, "
        f"{len(skipped)} skipped, of {len(results)} snippets"
    )
    q_results = verify_code_questions(args.subject, Path(OUT), set(args.concepts) or None)
    q_failed = [r for r in q_results if r.status == "failed"]
    for r in q_results:
        if r.status != "passed":
            print(f"{r.status.upper():8} question {r.question_id}: {r.detail}")
    print(
        f"{len(q_results) - len(q_failed)} of {len(q_results)} code_output questions match their answer"
    )
    return 1 if (failed or q_failed) else 0


if __name__ == "__main__":
    sys.exit(main())
