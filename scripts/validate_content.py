"""Validate notes, question bank, study sets and the eval test set; print a coverage table.

Usage: uv run --project apps/api python scripts/validate_content.py [--subject dsa] [--strict]
Without --strict, missing files are reported as pending (content is written cluster by cluster).
"""

from __future__ import annotations

import argparse
import sys

from app.content.validation import validate_subject_content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="dsa")
    parser.add_argument("--strict", action="store_true", help="require full coverage")
    args = parser.parse_args()

    rep = validate_subject_content(args.subject, strict=args.strict)
    print(f"{'concept':30} {'cluster':17} {'note':8} {'words':>5} {'qs':>3}  mcq ms tf co sa  rev")
    for r in rep.rows:
        t = r.by_type
        print(
            f"{r.concept_id:30} {r.cluster:17} {r.note:8} {r.words:>5} {r.questions:>3}  "
            f"{t.get('mcq', 0):>3} {t.get('multi_select', 0):>2} {t.get('true_false', 0):>2} "
            f"{t.get('code_output', 0):>2} {t.get('short_answer', 0):>2}  {'Y' if r.reviewed else '-'}"
        )
    done = sum(1 for r in rep.rows if r.note == "ok")
    with_q = sum(1 for r in rep.rows if r.questions)
    total_q = sum(r.questions for r in rep.rows)
    print(
        f"\nNotes: {done}/{len(rep.rows)} · question files: {with_q}/{len(rep.rows)} "
        f"({total_q} questions) · study sets: {rep.study_sets} · testset items: {rep.testset_count}"
    )
    for w in rep.warnings:
        print(f"WARNING: {w}")
    if rep.ok:
        print("\nOK: content is valid" + (" (strict)" if args.strict else " (non-strict: pending allowed)"))
        return 0
    print(f"\nFAILED with {len(rep.errors)} problem(s):")
    for e in rep.errors:
        print(f"  - {e}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
