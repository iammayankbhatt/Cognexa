"""Output checks run on every model reply before it reaches the student.

- system-prompt leak: the canary marker, or a long verbatim stretch of the system prompt;
- harmful content: a small, conservative pattern list (a DSA tutor has no reason to produce any of
  it); anything matched is replaced by a short refusal.
These are a last line of defence; the prompt rules (guardrails.prompts) do most of the work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.guardrails.prompts import CANARY

LEAK_REPLY = "I can't share my instructions, but I'm happy to help with your DSA question."
HARMFUL_REPLY = (
    "I can't help with that. I can help you with Data Structures & Algorithms, though: "
    "what are you working on?"
)

_HARMFUL = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(build|make|assemble)\b.{0,40}\b(bomb|explosive|nerve agent|bioweapon)",
        r"\b(keylogger|ransomware|credential stealer)\b.{0,60}\b(code|script|install|deploy)",
        r"\bhow to\b.{0,30}\b(hack into|break into)\b.{0,40}\b(account|server|network)",
    )
]
_WORD = re.compile(r"\w+")


@dataclass(frozen=True)
class OutputCheck:
    ok: bool
    text: str
    reason: str | None = None


def _shingles(text: str, n: int) -> set[tuple[str, ...]]:
    words = _WORD.findall(text.lower())
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def leaks_system_prompt(reply: str, system_prompt: str, n: int = 12) -> bool:
    """True if the canary appears, or any run of `n` consecutive words of the system prompt is
    repeated verbatim (normal answers never repeat 12 words of our instructions)."""
    if CANARY.lower() in reply.lower():
        return True
    return bool(_shingles(system_prompt, n) & _shingles(reply, n))


def check_output(reply: str, system_prompt: str) -> OutputCheck:
    if leaks_system_prompt(reply, system_prompt):
        return OutputCheck(False, LEAK_REPLY, "system_prompt_leak")
    if any(p.search(reply) for p in _HARMFUL):
        return OutputCheck(False, HARMFUL_REPLY, "harmful_content")
    return OutputCheck(True, reply)
