"""No invisible or bidirectional-control characters in source code (BUG-020, "Trojan Source").

Such characters can make code read differently from how it runs, and they are easy to introduce by
accident (for example when an escape like \\u202e is turned into the real character by a tool).
Write them as escapes instead.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCANNED = [
    ROOT / "apps" / "api" / "app",
    ROOT / "apps" / "api" / "tests",
    ROOT / "scripts",
    ROOT / "apps" / "web" / "src",
    ROOT / "apps" / "web" / "e2e",
]
SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".css", ".sql"}
ALLOWED = {"\n", "\t", "\r", "﻿"}  # BOM at the start of some editor-saved files is harmless


def test_no_invisible_or_bidi_characters_in_source() -> None:
    problems: list[str] = []
    for base in SCANNED:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix not in SUFFIXES or "node_modules" in path.parts or ".next" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(text.splitlines(), 1):
                for ch in line:
                    if ch not in ALLOWED and unicodedata.category(ch) in ("Cf", "Cc"):
                        problems.append(f"{path.relative_to(ROOT)}:{lineno}: U+{ord(ch):04X}")
    assert problems == [], "write these characters as escapes:\n" + "\n".join(problems[:20])
