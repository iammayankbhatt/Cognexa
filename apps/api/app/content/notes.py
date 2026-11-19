"""Parsing of concept notes (data/subjects/<subject>/content/<concept_id>.md) into sections, chunks
and code snippets."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

# (H2 heading, chunk kind) in the required order.
REQUIRED_SECTIONS: list[tuple[str, str]] = [
    ("Overview", "overview"),
    ("Intuition", "intuition"),
    ("How It Works", "mechanism"),
    ("Worked Example", "example"),
    ("Code", "code"),
    ("Complexity", "complexity"),
    ("Common Mistakes & Misconceptions", "pitfalls"),
    ("Builds On", "prerequisites"),
    ("Leads To", "next"),
    ("Check Yourself", "self_check"),
]
KIND_BY_HEADING = dict(REQUIRED_SECTIONS)

MIN_WORDS = 450
MAX_WORDS = 1600


class NoteFrontmatter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    cluster: str
    reviewed: bool = False
    sources: list[str] = Field(min_length=1)


@dataclass
class Section:
    heading: str
    kind: str
    text: str
    order: int


@dataclass
class ParsedNote:
    frontmatter: NoteFrontmatter
    sections: list[Section]
    extra_headings: list[str] = field(default_factory=list)
    word_count: int = 0


@dataclass(frozen=True)
class Chunk:
    id: str
    concept_id: str
    subject_id: str
    kind: str
    heading: str
    text: str
    order: int
    reviewed: bool

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(f"{self.heading}\n{self.text}".encode()).hexdigest()


class NoteFormatError(ValueError):
    pass


_FRONT = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_FENCE = re.compile(r"^```(\w*)\s*\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)


def parse_note(text: str) -> ParsedNote:
    text = text.replace("\r\n", "\n")
    m = _FRONT.match(text)
    if not m:
        raise NoteFormatError("missing YAML frontmatter between '---' lines")
    try:
        meta = yaml.safe_load(m.group(1)) or {}
        front = NoteFrontmatter.model_validate(meta)
    except Exception as exc:
        raise NoteFormatError(f"invalid frontmatter: {exc}") from exc

    body = text[m.end() :]
    # H2 headings only outside fenced code blocks.
    parts: list[tuple[str, list[str]]] = []
    in_fence = False
    for line in body.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            parts.append((line[3:].strip(), []))
        elif parts:
            parts[-1][1].append(line)

    sections: list[Section] = []
    extra: list[str] = []
    for i, (heading, lines) in enumerate(parts):
        kind = KIND_BY_HEADING.get(heading)
        if kind is None:
            extra.append(heading)
            continue
        sections.append(Section(heading, kind, "\n".join(lines).strip(), i))
    words = len(re.sub(r"```.*?```", " ", body, flags=re.DOTALL).split())
    return ParsedNote(front, sections, extra, words)


def parse_note_file(path: Path) -> ParsedNote:
    return parse_note(path.read_text(encoding="utf-8"))


def build_chunks(note: ParsedNote, subject_id: str) -> list[Chunk]:
    return [
        Chunk(
            id=f"{note.frontmatter.id}#{s.kind}",
            concept_id=note.frontmatter.id,
            subject_id=subject_id,
            kind=s.kind,
            heading=s.heading,
            text=s.text,
            order=i,
            reviewed=note.frontmatter.reviewed,
        )
        for i, s in enumerate(note.sections)
    ]


def extract_code_blocks(text: str, language: str) -> list[str]:
    """Fenced blocks tagged with `language` (e.g. 'python', 'cpp'), in order."""
    return [m.group(2) for m in _FENCE.finditer(text) if m.group(1) == language]


def self_check_pairs(section_text: str) -> list[tuple[str, str]]:
    """Parse '**Q1.** question' / '**A1.** answer' pairs from the Check Yourself section."""
    qs = dict(re.findall(r"^\*\*Q(\d+)\.\*\*\s+(.+)$", section_text, flags=re.MULTILINE))
    ans = dict(re.findall(r"^\*\*A(\d+)\.\*\*\s+(.+)$", section_text, flags=re.MULTILINE))
    return [(qs[k], ans[k]) for k in sorted(qs) if k in ans]
