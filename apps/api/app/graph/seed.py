"""Idempotent loading of a concepts.yaml document into Neo4j (MERGE everywhere)."""

from __future__ import annotations

from dataclasses import dataclass

from app.content.notes import Chunk
from app.graph.models import ConceptFile, GraphEdge
from app.graph.repository import PREREQUISITE, RELATED, ChunkRecord, GraphRepository
from app.graph.validation import validate_concept_file


class InvalidGraphError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("concepts file is invalid: " + "; ".join(errors[:5]))
        self.errors = errors


@dataclass
class SeedResult:
    concepts: int
    prerequisite_edges: int
    related_edges: int
    pruned_edges: int = 0


def desired_edges(doc: ConceptFile) -> list[GraphEdge]:
    """Edges the file declares. RELATED_TO pairs are deduplicated, stored smaller id first."""
    edges: list[GraphEdge] = []
    related_seen: set[tuple[str, str]] = set()
    for c in doc.concepts:
        for p in c.prerequisites:
            edges.append(GraphEdge(source=p, target=c.id, type=PREREQUISITE))
        for r in c.related:
            lo, hi = sorted((c.id, r))
            if (lo, hi) not in related_seen:
                related_seen.add((lo, hi))
                edges.append(GraphEdge(source=lo, target=hi, type=RELATED))
    return edges


async def seed_subject(
    repo: GraphRepository, doc: ConceptFile, *, prune: bool = False
) -> SeedResult:
    """Validate then load a subject. Safe to run repeatedly. With prune=True, human-sourced edges
    that are no longer in the file are removed (LLM-proposed edges are never pruned)."""
    report = validate_concept_file(doc)
    if not report.ok:
        raise InvalidGraphError(report.errors)

    subject_id = doc.subject.id
    await repo.ensure_schema()
    await repo.upsert_subject(subject_id, doc.subject.name)
    for concept in doc.concepts:
        await repo.upsert_concept(subject_id, concept)

    edges = desired_edges(doc)
    # Prerequisite edges are inserted in teaching order so the per-edge cycle check stays cheap.
    for edge in edges:
        await repo.upsert_edge(edge)

    pruned = 0
    if prune:
        wanted = {(e.source, e.target, e.type) for e in edges}
        for existing in await repo.list_edges(subject_id):
            key = (existing.source, existing.target, existing.type)
            if key in wanted or existing.source_kind != "human":
                continue
            if await repo.delete_edge(existing.source, existing.target, existing.type):
                pruned += 1

    return SeedResult(
        concepts=len(doc.concepts),
        prerequisite_edges=sum(1 for e in edges if e.type == PREREQUISITE),
        related_edges=sum(1 for e in edges if e.type == RELATED),
        pruned_edges=pruned,
    )


async def seed_chunks(repo: GraphRepository, chunks: list[Chunk]) -> tuple[int, int]:
    """Create/update Chunk nodes (HAS_CHUNK) and remove stale ones of the same concepts.
    Returns (upserted, deleted)."""
    keep: dict[str, list[str]] = {}
    for c in chunks:
        await repo.upsert_chunk(
            ChunkRecord(
                id=c.id,
                concept_id=c.concept_id,
                subject_id=c.subject_id,
                kind=c.kind,
                heading=c.heading,
                text=c.text,
                order=c.order,
                reviewed=c.reviewed,
            )
        )
        keep.setdefault(c.concept_id, []).append(c.id)
    deleted = await repo.delete_stale_chunks(keep)
    return len(chunks), deleted
