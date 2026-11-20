"""Edits to the concept graph made from the admin console (and by approved proposals).

Every change goes through `GraphEditor`, which
1. writes Neo4j (the source the tutor and recommender read),
2. mirrors concepts into Postgres (foreign keys for chunks, questions, mastery),
3. writes audit_log,
4. invalidates what depends on the graph: the tutor's concept catalogue, the public /graph cache
   and response/classification cache entries that touched the affected concepts.

Neo4j and Postgres cannot share a transaction. Writes are ordered graph first, Postgres second,
and both are idempotent (MERGE / upsert), so a failure part-way is reported to the caller and
simply retried (DEC-058).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import yaml
from fastapi import Request

from app.cache.service import LLMCache
from app.core.errors import AppError
from app.db.profiles import ProfileRepository
from app.db.repositories import ConceptMirrorRepository
from app.db.session import Database
from app.graph.models import ConceptDef, ConceptFile, GraphConcept, GraphEdge, SubjectDef
from app.graph.repository import (
    PREREQUISITE,
    RELATED,
    CycleError,
    GraphRepository,
    UnknownConceptError,
)
from app.graph.validation import topological_order, validate_concept_file

EDGE_TYPES = (PREREQUISITE, RELATED)


@dataclass
class GraphEditor:
    repo: GraphRepository
    db: Database
    cache: LLMCache | None
    request: Request | None = None

    @classmethod
    def from_request(cls, request: Request) -> GraphEditor:
        state = request.app.state
        return cls(state.graph.repository(), state.db, state.tutor.cache, request)

    # ------------------------------------------------------------------ effects
    async def _after_change(
        self,
        actor: uuid.UUID | None,
        subject_id: str,
        action: str,
        target: str,
        details: dict[str, Any],
        concept_ids: list[str],
    ) -> None:
        async with self.db.sessions()() as session, session.begin():
            await ProfileRepository(session).audit(actor, action, target, details)
        if self.request is not None:
            state = self.request.app.state
            state.tutor.catalogues.invalidate(subject_id)
            state.graph_cache.pop(subject_id, None)
        if self.cache is not None and concept_ids:
            await self.cache.invalidate_concepts(concept_ids)

    # ------------------------------------------------------------------ concepts
    async def save_concept(
        self, actor: uuid.UUID | None, subject_id: str, concept: ConceptDef, *, create: bool
    ) -> GraphConcept:
        existing = await self.repo.get_concept(concept.id)
        if create and existing is not None:
            raise AppError("conflict", f"A concept with id '{concept.id}' already exists.", 409)
        if not create and existing is None:
            raise AppError("not_found", "Concept not found.", 404)
        if existing is not None and existing.subject_id != subject_id:
            raise AppError("conflict", "That concept belongs to another subject.", 409)
        if concept.order_index is None:
            if existing is not None:
                concept = concept.model_copy(update={"order_index": existing.order_index})
            else:
                peers = await self.repo.list_concepts(subject_id)
                nxt = max((c.order_index for c in peers), default=-1) + 1
                concept = concept.model_copy(update={"order_index": nxt})
        await self.repo.upsert_concept(subject_id, concept)
        async with self.db.sessions()() as session, session.begin():
            await ConceptMirrorRepository(session).upsert_one(subject_id, concept)
        before = existing.model_dump() if existing else None
        await self._after_change(
            actor,
            subject_id,
            "graph.create_concept" if create else "graph.update_concept",
            concept.id,
            {"before": before, "after": concept.model_dump(exclude={"prerequisites", "related"})},
            [concept.id],
        )
        saved = await self.repo.get_concept(concept.id)
        assert saved is not None
        return saved

    # ------------------------------------------------------------------ edges
    async def add_edge(
        self,
        actor: uuid.UUID | None,
        subject_id: str,
        edge: GraphEdge,
        *,
        audit_action: str = "graph.add_edge",
    ) -> GraphEdge:
        if edge.type not in EDGE_TYPES:
            raise AppError("validation_error", "Unknown edge type.", 422)
        if edge.source == edge.target:
            raise AppError("validation_error", "A concept cannot be linked to itself.", 422)
        if edge.type == PREREQUISITE:
            await self.check_no_cycle(edge.source, edge.target)
            # one relation per pair: a prerequisite replaces a related link
            await self.repo.delete_edge(edge.source, edge.target, RELATED)
        else:
            if await self._has_prerequisite_between(edge.source, edge.target):
                raise AppError(
                    "conflict",
                    "These concepts already have a prerequisite edge; remove it first.",
                    409,
                )
        try:
            await self.repo.upsert_edge(edge)
        except CycleError:  # raced with another edit
            await self.check_no_cycle(edge.source, edge.target)
            raise
        except UnknownConceptError as e:
            raise AppError("not_found", "Both concepts must exist.", 404) from e
        await self._after_change(
            actor,
            subject_id,
            audit_action,
            f"{edge.source}->{edge.target}",
            edge.model_dump(),
            [edge.source, edge.target],
        )
        return edge

    async def check_no_cycle(self, before: str, after: str) -> None:
        """Raise 409 `cycle_detected` with the chain that the new edge would close."""
        if before == after:
            raise AppError("validation_error", "A concept cannot be its own prerequisite.", 422)
        if not await self.repo.would_create_cycle(before, after):
            return
        path = await self.repo.prerequisite_path(after, before)
        chain = " → ".join(path) if path else f"{after} → … → {before}"
        raise AppError(
            "cycle_detected",
            f"'{before}' cannot be a prerequisite of '{after}': {after} already leads to "
            f"{before} ({chain}), so the new edge would create a cycle.",
            409,
            details={"path": path, "source": before, "target": after},
        )

    async def _has_prerequisite_between(self, a: str, b: str) -> bool:
        for s, t in ((a, b), (b, a)):
            if await self.repo.prerequisite_path(s, t) == [s, t]:
                return True
        return False

    async def remove_edge(
        self,
        actor: uuid.UUID | None,
        subject_id: str,
        source: str,
        target: str,
        edge_type: str,
        rationale: str | None,
    ) -> None:
        if edge_type not in EDGE_TYPES:
            raise AppError("validation_error", "Unknown edge type.", 422)
        if not await self.repo.delete_edge(source, target, edge_type):
            raise AppError("not_found", "Edge not found.", 404)
        await self._after_change(
            actor,
            subject_id,
            "graph.remove_edge",
            f"{source}->{target}",
            {"type": edge_type, "rationale": rationale},
            [source, target],
        )

    # ------------------------------------------------------------------ export
    async def export_yaml(self, subject_id: str) -> tuple[str, list[str]]:
        """concepts.yaml text for the current graph (approved edges only) and validation errors."""
        nodes = await self.repo.list_concepts(subject_id)
        if not nodes:
            raise AppError("not_found", "That subject has no concepts.", 404)
        edges = [e for e in await self.repo.list_edges(subject_id) if e.status == "approved"]
        prereqs: dict[str, list[str]] = defaultdict(list)
        related: dict[str, list[str]] = defaultdict(list)
        for e in edges:
            if e.type == PREREQUISITE:
                prereqs[e.target].append(e.source)
            else:
                lo, hi = sorted((e.source, e.target))
                related[hi].append(lo)
        ordered = sorted(nodes, key=lambda c: (c.order_index, c.id))
        defs = [
            ConceptDef(
                id=c.id,
                name=c.name,
                cluster=c.cluster,
                difficulty=c.difficulty,
                order_index=c.order_index,
                description=c.description,
                aliases=c.aliases,
                keywords=c.keywords,
                prerequisites=sorted(prereqs[c.id]),
                related=sorted(related[c.id]),
            )
            for c in ordered
        ]
        try:
            order = topological_order(defs)
        except ValueError:
            order = [d.id for d in defs]
        rank = {cid: i for i, cid in enumerate(order)}
        defs = sorted(
            (d.model_copy(update={"order_index": rank[d.id]}) for d in defs),
            key=lambda d: rank[d.id],
        )
        name = await self.repo.subject_name(subject_id) or subject_id
        doc = ConceptFile(
            subject=SubjectDef(id=subject_id, name=name),
            roots=[d.id for d in defs if not d.prerequisites],
            concepts=defs,
        )
        report = validate_concept_file(doc)
        header = [
            f"# {name} concept graph, exported from the Cognexa admin console.",
            "# Edge convention: `prerequisites: [A]` on B means A -[:PREREQUISITE_OF]-> B.",
            "# order_index was recomputed (topological). Replace data/subjects/"
            f"{subject_id}/concepts.yaml with this file, run scripts/validate_graph.py, commit.",
        ]
        header += [f"# VALIDATION: {err}" for err in report.errors]
        body = yaml.safe_dump(
            doc.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=100
        )
        return "\n".join(header) + "\n" + body, list(report.errors)
