"""Input cleaning (CLAUDE.md rule 8: user text is untrusted).

- strip control characters (keep newlines and tabs), normalise Unicode (NFKC), trim,
  cap blank lines;
- neutralise our own delimiter tags inside user text, so a student cannot close
  `<student_question>` early and write "system" text after it;
- enforce the maximum length (the usage guard reports it as INPUT_TOO_LONG).
`injection_signals` flags common prompt-injection phrasing for logging and metrics; it never blocks
on its own, because the prompt template is the real defence.
"""

from __future__ import annotations

import re
import unicodedata

from app.core.errors import AppError

# Marker in every system prompt; seeing it in a reply means the prompt leaked (guardrails.output).
CANARY = "CGX-7f3a-SYS"

PROTECTED_TAGS = (
    "student_question",
    "student_reply",
    "context",
    "chunk",
    "system",
    "instructions",
    "history",
    "catalogue",
    "plan_input",
    "followups",
    "question",
    "rubric",
    "reference_answer",
    "section",
)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")
_BLANKS = re.compile(r"\n{3,}")
_TAGS = re.compile(r"<\s*(/?)\s*(" + "|".join(PROTECTED_TAGS) + r")\b[^>]*>", re.IGNORECASE)

_INJECTION = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bignore\b.{0,40}\b(previous|above|prior|all)\b.{0,20}\b(instructions?|rules|prompts?)",
        r"\bdisregard\b.{0,40}\b(instructions?|rules|system)",
        r"\b(reveal|show|print|repeat|leak)\b.{0,40}\b(system prompt|instructions|your prompt)",
        r"\byou are now\b|\bact as\b.{0,30}\b(dan|developer mode|jailbreak)",
        r"\bnew instructions?\b\s*:",
        r"</?\s*(system|student_question|context)\s*>",
        re.escape(CANARY),  # asking the model to repeat the hidden marker
    )
]


def clean_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    t = _CONTROL.sub("", t)
    t = _TAGS.sub(lambda m: f"[{m.group(1)}{m.group(2).lower()}]", t)
    t = _BLANKS.sub("\n\n", t)
    return t.strip()


def clean_user_text(text: str, max_chars: int) -> str:
    """Cleaned text, or AppError 413/422 when it is too long or empty after cleaning."""
    cleaned = clean_text(text)
    if len(cleaned) > max_chars:
        raise AppError(
            "INPUT_TOO_LONG",
            f"Please keep your message under {max_chars} characters.",
            413,
            details={"max_input_chars": max_chars},
        )
    if not cleaned:
        raise AppError("EMPTY_INPUT", "Please type a question.", 422)
    return cleaned


def injection_signals(text: str) -> list[str]:
    """Which injection patterns matched (empty list when none). For logs/metrics only.

    Matched on the normalised text (NFKC, invisible characters removed), so look-alike tags such
    as fullwidth brackets or tags split by zero-width spaces are flagged too."""
    t = _CONTROL.sub("", unicodedata.normalize("NFKC", text))
    return [p.pattern for p in _INJECTION if p.search(t)]
