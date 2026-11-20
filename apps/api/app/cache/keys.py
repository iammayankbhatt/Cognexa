"""Cache keys: sha256 over normalised inputs, prefixed by kind so kinds never collide."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable

KINDS = ("resp", "cls", "emb", "grade")
_SPACE = re.compile(r"\s+")
_EDGE_PUNCT = re.compile(r"^[\s\W_]+|[\s\W_]+$")


def normalize_text(text: str) -> str:
    """Case-folded, NFKC, single spaces, no leading/trailing punctuation.

    "  What is a Heap?? " and "what is a heap" share a key; inner punctuation is kept because it
    can change meaning in code ("a[i]" vs "a i").
    """
    t = unicodedata.normalize("NFKC", text).casefold()
    t = _SPACE.sub(" ", t).strip()
    return _EDGE_PUNCT.sub("", t)


def cache_key(
    kind: str,
    text: str,
    *,
    mode: str = "",
    concept_ids: Iterable[str] = (),
    bucket: str = "",
    model: str = "",
) -> str:
    """`resp:<sha256>` etc. `bucket` is the personalisation bucket (e.g. a hash of the student's
    weak concepts), so personalised answers are only shared between students in the same bucket."""
    if kind not in KINDS:
        raise ValueError(f"unknown cache kind {kind!r}")
    parts = [
        normalize_text(text),
        mode,
        ",".join(sorted(set(concept_ids))),
        bucket,
        model,
    ]
    digest = hashlib.sha256("\x1f".join(parts).encode()).hexdigest()
    return f"{kind}:{digest}"
