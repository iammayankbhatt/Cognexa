"""Builders for a tiny synthetic subject (concepts base -> mid -> top) used by content tooling tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.graph import loader

CONCEPTS = """\
subject:
  id: mini
  name: "Mini"
roots: [base]
concepts:
  - id: base
    name: "Base Idea"
    cluster: core
    order_index: 0
    difficulty: 1
    description: "The root concept of the mini subject."
    prerequisites: []
    related: []
  - id: mid
    name: "Middle Idea"
    cluster: core
    order_index: 1
    difficulty: 2
    description: "The middle concept which builds on base."
    prerequisites: [base]
    related: []
  - id: top
    name: "Top Idea"
    cluster: core
    order_index: 2
    difficulty: 3
    description: "The top concept which builds on mid."
    prerequisites: [mid]
    related: []
"""

NAMES = {"base": "Base Idea", "mid": "Middle Idea", "top": "Top Idea"}
PREREQS = {"base": [], "mid": ["base"], "top": ["mid"]}
DEPENDENTS = {"base": ["mid"], "mid": ["top"], "top": []}

PY_OK = "print('hello from python')"
CPP_OK = '#include <iostream>\nint main() { std::cout << "hi\\n"; return 0; }'


def filler(n: int) -> str:
    return " ".join(["word"] * n)


def note_text(
    cid: str,
    *,
    words: int = 520,
    python: str = PY_OK,
    cpp: str = CPP_OK,
    builds_on: str | None = None,
    leads_to: str | None = None,
    checks: int = 3,
    drop_section: str | None = None,
    extra_h2: bool = False,
    name: str | None = None,
) -> str:
    builds = builds_on
    if builds is None:
        names = [NAMES[p] for p in PREREQS[cid]]
        builds = (
            ("This builds on " + " and ".join(names) + ".")
            if names
            else ("This is a foundation concept with no prerequisites.")
        )
    leads = leads_to
    if leads is None:
        deps = [NAMES[d] for d in DEPENDENTS[cid]]
        leads = ("It leads to " + " and ".join(deps) + ".") if deps else "It leads to many things."
    check_lines = "\n".join(
        f"**Q{i}.** What is question {i}?\n**A{i}.** Answer {i}." for i in range(1, checks + 1)
    )
    sections = {
        "Overview": filler(words // 4),
        "Intuition": filler(words // 4),
        "How It Works": filler(words // 4),
        "Worked Example": filler(words // 4),
        "Code": f"```python\n{python}\n```\n\n```cpp\n{cpp}\n```",
        "Complexity": "Constant time and space in all cases here.",
        "Common Mistakes & Misconceptions": "Students often forget the basics and mix things up.",
        "Builds On": builds,
        "Leads To": leads,
        "Check Yourself": check_lines,
    }
    if drop_section:
        sections.pop(drop_section)
    body = "\n\n".join(f"## {h}\n{t}" for h, t in sections.items())
    if extra_h2:
        body += "\n\n## Bonus Round\nSurprise."
    front = (
        f"---\nid: {cid}\nname: {name or NAMES[cid]}\ncluster: core\nreviewed: false\n"
        "sources:\n  - Some Textbook, Chapter 1\n---\n"
    )
    return front + body + "\n"


def mcq(cid: str, n: int, difficulty: int = 1, prereq: str | None = None) -> dict[str, Any]:
    return {
        "id": f"{cid}-q{n:02d}",
        "type": "mcq",
        "difficulty": difficulty,
        "prompt": f"Which statement about {cid} is correct (variant {n})?",
        "options": [
            {"id": "a", "text": "The right one"},
            {
                "id": "b",
                "text": "A plausible mistake",
                "why_wrong": "This confuses it with something else.",
            },
            {"id": "c", "text": "Another mistake", "why_wrong": "This reverses the relationship."},
            {
                "id": "d",
                "text": "A third mistake",
                "why_wrong": "This ignores the base case entirely.",
            },
        ],
        "answer": "a",
        "explanation": "The first option is right because that is how the concept is defined.",
        "misconception_tag": "tag",
        "diagnoses_prereq": prereq,
    }


def valid_questions(cid: str, prereq: str | None = None) -> dict[str, Any]:
    qs = [mcq(cid, i, 1 if i < 3 else 2, prereq) for i in range(1, 5)]
    qs.append(
        {
            "id": f"{cid}-q05",
            "type": "multi_select",
            "difficulty": 2,
            "prompt": f"Select all true statements about {cid}.",
            "options": [
                {"id": "a", "text": "True one"},
                {"id": "b", "text": "True two"},
                {"id": "c", "text": "False one", "why_wrong": "This is simply not the case."},
                {"id": "d", "text": "False two", "why_wrong": "This is also not the case."},
            ],
            "answer": ["a", "b"],
            "explanation": "The first two statements follow from the definition of the concept.",
            "misconception_tag": "tag",
            "diagnoses_prereq": None,
        }
    )
    qs.append(
        {
            "id": f"{cid}-q06",
            "type": "true_false",
            "difficulty": 1,
            "prompt": f"True or false: {cid} always takes constant time.",
            "answer": False,
            "explanation": "It depends on the input, so the statement is false in general.",
            "misconception_tag": "tag",
            "diagnoses_prereq": None,
        }
    )
    qs.append(
        {
            "id": f"{cid}-q07",
            "type": "code_output",
            "difficulty": 2,
            "prompt": "What does this program print?",
            "code": "print(1 + 1)",
            "answer": "2",
            "explanation": "One plus one is two, printed on its own line.",
            "misconception_tag": "tag",
            "diagnoses_prereq": None,
        }
    )
    qs.append(
        {
            "id": f"{cid}-q08",
            "type": "short_answer",
            "difficulty": 3,
            "prompt": f"Explain in one or two sentences what {cid} is for.",
            "answer": "It is for demonstrating how the concept works in a small example.",
            "explanation": "A good answer names the purpose and gives a brief reason.",
            "rubric": {"key_points": ["purpose", "reason"], "max_score": 1, "partial_credit": True},
            "misconception_tag": "tag",
            "diagnoses_prereq": None,
        }
    )
    return {"concept_id": cid, "questions": qs}


def write_subject(
    root: Path, monkeypatch: Any, *, notes: bool = True, questions: bool = True
) -> Path:
    """Create data/subjects/mini under `root` and point the loader at it."""
    base = root / "mini"
    (base / "content").mkdir(parents=True)
    (base / "questions").mkdir()
    (base / "eval").mkdir()
    (base / "concepts.yaml").write_text(CONCEPTS, encoding="utf-8")
    if notes:
        for cid in NAMES:
            (base / "content" / f"{cid}.md").write_text(note_text(cid), encoding="utf-8")
    if questions:
        for cid in NAMES:
            prereq = PREREQS[cid][0] if PREREQS[cid] else None
            data = valid_questions(cid, prereq)
            (base / "questions" / f"{cid}.yaml").write_text(
                yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
            )
    monkeypatch.setattr(loader, "SUBJECTS_DIR", root)
    return base
