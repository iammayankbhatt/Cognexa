"""Regenerate the Content Review Checklist (section 12 of progressfile.md).

Lists every concept with whether its note and questions are written and whether the human has
reviewed them. Ticks, reviewer and date you entered are preserved; new concepts get empty boxes.

Usage: uv run --project apps/api python scripts/update_review_checklist.py [--subject dsa]
"""

from __future__ import annotations

import argparse
import re
import sys

from app.graph.loader import REPO_ROOT, load_subject, subject_dir

PROGRESS = REPO_ROOT / "progressfile.md"
HEADING = "## 12. Content Review Checklist"
INTRO = (
    "> The reviewer is me (the sole developer). I tick a concept only after checking its notes, code "
    "and questions, and then set `reviewed: true` in the note's frontmatter.\n"
    "> `Written` is generated from the files by `scripts/update_review_checklist.py`; the other "
    "columns are mine and are preserved when the table is regenerated.\n"
)
HEADER = "| Cluster | Concept | Written | Notes reviewed | Questions reviewed | Reviewer (me) | Date |"


def existing_state(section: str) -> dict[str, list[str]]:
    state: dict[str, list[str]] = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[1] not in ("Concept", "---") and not cells[0].startswith("-"):
            state[cells[1].strip("_*")] = cells[3:7]
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subject", default="dsa")
    args = parser.parse_args()

    text = PROGRESS.read_text(encoding="utf-8")
    crlf = "\r\n" in text
    text = text.replace("\r\n", "\n")
    start = text.index(HEADING)
    nxt = re.search(r"^## 13\.", text[start:], flags=re.MULTILINE)
    assert nxt, "section 13 heading not found"
    end = start + nxt.start()
    old = text[start:end]
    state = existing_state(old)

    doc = load_subject(args.subject)
    base = subject_dir(args.subject)
    rows = []
    for c in sorted(doc.concepts, key=lambda c: c.order_index or 0):
        has_note = (base / "content" / f"{c.id}.md").exists()
        has_q = (base / "questions" / f"{c.id}.yaml").exists()
        written = "notes + questions" if has_note and has_q else ("notes" if has_note else (
            "questions" if has_q else "pending"))
        keep = state.get(c.id, ["☐", "☐", "", ""])
        rows.append(f"| {c.cluster} | {c.id} | {written} | {' | '.join(keep)} |")

    body = f"{HEADING}\n\n{INTRO}\n{HEADER}\n|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    new_text = text[:start] + body + text[end:]
    if crlf:
        new_text = new_text.replace("\n", "\r\n")
    PROGRESS.write_text(new_text, encoding="utf-8", newline="")
    done = sum(1 for r in rows if "notes + questions" in r)
    print(f"Review checklist updated: {len(rows)} concepts, {done} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
