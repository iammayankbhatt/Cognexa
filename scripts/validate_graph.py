"""Validate data/subjects/<subject>/concepts.yaml. Exits non-zero with clear messages on any problem.

Usage: uv run --project apps/api python scripts/validate_graph.py [path/to/concepts.yaml | subject_id]
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.graph.loader import concepts_path, load_concept_file
from app.graph.validation import validate_concept_file


def resolve(arg: str | None) -> Path:
    if arg is None:
        return concepts_path("dsa")
    p = Path(arg)
    return p if p.suffix in (".yaml", ".yml") else concepts_path(arg)


def main(argv: list[str]) -> int:
    path = resolve(argv[1] if len(argv) > 1 else None)
    try:
        doc = load_concept_file(path)
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}")
        return 2
    except yaml.YAMLError as exc:  # BUG-059: was an unhandled traceback
        print(f"ERROR: {path} is not valid YAML (quote values starting with & * ! | > @):\n{exc}")
        return 1
    except (ValidationError, ValueError) as exc:
        print(f"ERROR: {path} failed schema validation:\n{exc}")
        return 1

    report = validate_concept_file(doc)
    s = report.stats
    print(f"Subject: {doc.subject.id} ({doc.subject.name})   file: {path}")
    print(f"Nodes: {s.nodes}")
    print(f"Edges: {s.prerequisite_edges} PREREQUISITE_OF, {s.related_edges} RELATED_TO (undirected, deduplicated)")
    print(f"Max prerequisite depth: {s.max_depth}")
    print(f"Roots ({len(s.roots)}): {', '.join(s.roots)}")
    print(f"Leaves ({len(s.leaves)}): {', '.join(s.leaves)}")
    print("Clusters: " + ", ".join(f"{k}={v}" for k, v in s.clusters.items()))

    if report.ok:
        print("\nOK: graph is valid.")
        return 0
    print(f"\nFAILED with {len(report.errors)} problem(s):")
    for err in report.errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
