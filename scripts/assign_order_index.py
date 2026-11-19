"""Compute order_index (a topological teaching order) and write it into concepts.yaml.

Text-level edit: inserts or updates the `order_index:` line right after each concept's `cluster:` line,
so comments and formatting in the file are preserved. Run after adding or changing concepts.

Usage: uv run --project apps/api python scripts/assign_order_index.py [subject_id] [--check]
"""

from __future__ import annotations

import re
import sys

from app.graph.loader import concepts_path, load_concept_file
from app.graph.validation import topological_order


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("--")]
    check = "--check" in argv
    path = concepts_path(args[0] if args else "dsa")
    doc = load_concept_file(path)
    order = {cid: i for i, cid in enumerate(topological_order(doc.concepts))}

    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    current: str | None = None
    changed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^  - id: (\S+)\s*$", line)
        if m:
            current = m.group(1)
        out.append(line)
        if current and re.match(r"^    cluster: ", line):
            want = f"    order_index: {order[current]}"
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if re.match(r"^    order_index: ", nxt):
                if nxt != want:
                    changed += 1
                i += 1  # drop the old line, replaced below
            else:
                changed += 1
            out.append(want)
        i += 1

    if check:
        print("order_index up to date" if changed == 0 else f"{changed} order_index values are stale")
        return 0 if changed == 0 else 1
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"order_index written for {len(order)} concepts ({changed} changed) in {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
