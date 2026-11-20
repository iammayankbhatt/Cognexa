"""Stage 3: fetch content chunks for the ranked concepts and fill a token budget.

Matched concepts get the chunk kinds that suit the question's intent; prerequisites and related
concepts get their overview and pitfalls. Chunks are added in rank order until the budget is used;
each one is labelled [concept_id/kind] in the prompt. Plain RAG reuses `fill_budget`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.graph.repository import ChunkRecord
from app.guardrails.prompts import ContextBlock
from app.tutor.graph_source import TutorGraph
from app.tutor.trace import Intent, TraceChunk, TraceConcept

KINDS_BY_INTENT: dict[str, list[str]] = {
    "debug": ["pitfalls", "mechanism", "prerequisites"],
    "complexity": ["complexity", "overview"],
    "example": ["example", "code"],
    "compare": ["overview", "complexity", "pitfalls"],
    "explain": ["overview", "intuition", "mechanism", "prerequisites"],
    "other": ["overview", "intuition", "mechanism", "prerequisites"],
}
SUPPORT_KINDS = ["overview", "pitfalls"]
MIN_CHUNK_TOKENS = 60  # a chunk cut shorter than this is useless; skip it instead


def estimate_tokens(text: str) -> int:
    """About 4 characters per token for English prose and code (no tokenizer dependency)."""
    return max(1, math.ceil(len(text) / 4))


def label(chunk: ChunkRecord) -> str:
    return f"[{chunk.concept_id}/{chunk.kind}]"


@dataclass
class Gathered:
    blocks: list[ContextBlock]
    chunks: list[TraceChunk]
    used_tokens: int


def fill_budget(candidates: Sequence[tuple[ChunkRecord, float | None]], budget: int) -> Gathered:
    """Add chunks in order until `budget` tokens are used. A chunk that does not fit is cut at a
    paragraph boundary when enough of it fits, otherwise skipped (a later short one may fit)."""
    blocks: list[ContextBlock] = []
    traced: list[TraceChunk] = []
    used = 0
    for chunk, score in candidates:
        body = f"{chunk.heading}\n{chunk.text}".strip()
        tokens = estimate_tokens(body)
        if used + tokens > budget:
            room = budget - used
            if room < MIN_CHUNK_TOKENS:
                continue
            body = _cut(body, room)
            tokens = estimate_tokens(body)
            if tokens < MIN_CHUNK_TOKENS or used + tokens > budget:
                continue
        blocks.append(ContextBlock(chunk.concept_id, f"{label(chunk)} {chunk.heading}", body))
        traced.append(
            TraceChunk(
                id=chunk.id, concept_id=chunk.concept_id, kind=chunk.kind, tokens=tokens,
                score=score,
            )
        )  # fmt: skip
        used += tokens
    return Gathered(blocks, traced, used)


def _cut(body: str, room_tokens: int) -> str:
    limit = room_tokens * 4
    paras = body.split("\n\n")
    kept: list[str] = []
    size = 0
    for p in paras:
        if size + len(p) + 2 > limit:
            break
        kept.append(p)
        size += len(p) + 2
    return "\n\n".join(kept).strip()


async def gather(
    graph: TutorGraph, concepts: Sequence[TraceConcept], intent: Intent, budget: int
) -> Gathered:
    matched = [c.id for c in concepts if c.role == "matched"]
    support = [c.id for c in concepts if c.role != "matched"]
    want = KINDS_BY_INTENT.get(intent, KINDS_BY_INTENT["explain"])
    by_concept: dict[str, list[ChunkRecord]] = {}
    for ch in await graph.get_chunks(matched, want, limit=200):
        by_concept.setdefault(ch.concept_id, []).append(ch)
    if support:
        for ch in await graph.get_chunks(support, SUPPORT_KINDS, limit=200):
            by_concept.setdefault(ch.concept_id, []).append(ch)

    def ordered(cid: str, kinds: list[str]) -> list[ChunkRecord]:
        rank = {k: i for i, k in enumerate(kinds)}
        return sorted(
            (c for c in by_concept.get(cid, []) if c.kind in rank),
            key=lambda c: (rank[c.kind], c.order),
        )

    candidates: list[tuple[ChunkRecord, float | None]] = []
    # Each matched concept's first (most relevant) kind, then a prerequisite overview, so a small
    # budget still shows the graph's contribution; then everything else in rank order.
    first_pass: list[ChunkRecord] = []
    for cid in matched:
        first_pass.extend(ordered(cid, want)[:1])
    weak_or_near = [c.id for c in concepts if c.role == "prerequisite"][:2]
    for cid in weak_or_near:
        first_pass.extend(ordered(cid, SUPPORT_KINDS)[:1])
    seen = {c.id for c in first_pass}
    rest: list[ChunkRecord] = []
    for c in concepts:
        kinds = want if c.role == "matched" else SUPPORT_KINDS
        rest.extend(ch for ch in ordered(c.id, kinds) if ch.id not in seen)
    candidates = [(c, None) for c in [*first_pass, *rest]]
    return fill_budget(candidates, budget)
