"""LLM-proposed graph changes with human review (report Gap I: "an LLM proposes, a human verifies").

Proposal types (graph_proposals.type) and their payloads:
- add_edge / remove_edge: {subject_id, source, target, edge_type}
- tag_chunk: a section of an uploaded document (or other text) attached to a concept
  {subject_id, concept_id, kind, heading, text, document_id?, document_name?}
- new_concept: {subject_id, concept: {id, name, cluster, difficulty, description, aliases,
  keywords}, prerequisites: [...], heading?, text?, document_id?, document_name?}

Approving applies the change. Neo4j and Postgres cannot share a transaction, so the order is
fixed (DEC-058): validate and embed first (nothing written if that fails) → Neo4j (idempotent
MERGE) → ONE Postgres transaction that writes the chunk row (if any) AND marks the proposal
approved. If the Postgres step fails after the graph write, the API answers 503
`partial_apply`; retrying the same approval re-runs the idempotent graph write and completes.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import Select, and_, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.graph_editor import GraphEditor
from app.content.notes import KIND_BY_HEADING
from app.core.errors import AppError
from app.db.tables import content_chunks, graph_proposals
from app.graph.models import ConceptDef, GraphEdge
from app.graph.repository import PREREQUISITE, ChunkRecord
from app.llm.embeddings import EmbeddingProvider

ProposalType = Literal["add_edge", "remove_edge", "tag_chunk", "new_concept"]
CHUNK_KINDS = sorted(set(KIND_BY_HEADING.values()))
ID = r"^[a-z][a-z0-9_]{1,63}$"
LLM_CHUNK_ORDER = 100  # after the note's own sections


class EdgePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subject_id: str = Field(pattern=ID)
    source: str = Field(pattern=ID)
    target: str = Field(pattern=ID)
    edge_type: Literal["PREREQUISITE_OF", "RELATED_TO"]


class ChunkPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subject_id: str = Field(pattern=ID)
    concept_id: str = Field(pattern=ID)
    kind: str = Field(default="overview")
    heading: str = Field(default="", max_length=200)
    text: str = Field(min_length=20, max_length=12_000)
    document_id: str | None = None
    document_name: str | None = Field(default=None, max_length=255)


class ConceptFields(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(pattern=ID)
    name: str = Field(min_length=1, max_length=200)
    cluster: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    difficulty: int = Field(default=2, ge=1, le=5)
    description: str = Field(min_length=10, max_length=600)
    aliases: list[str] = Field(default_factory=list, max_length=40)
    keywords: list[str] = Field(default_factory=list, max_length=40)


class ConceptPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    subject_id: str = Field(pattern=ID)
    concept: ConceptFields
    prerequisites: list[str] = Field(default_factory=list, max_length=10)
    heading: str = Field(default="", max_length=200)
    text: str | None = Field(default=None, max_length=12_000)
    document_id: str | None = None
    document_name: str | None = Field(default=None, max_length=255)


PAYLOADS: dict[str, type[BaseModel]] = {
    "add_edge": EdgePayload,
    "remove_edge": EdgePayload,
    "tag_chunk": ChunkPayload,
    "new_concept": ConceptPayload,
}


def parse_payload(kind: str, payload: dict[str, Any]) -> BaseModel:
    model = PAYLOADS.get(kind)
    if model is None:
        raise AppError("validation_error", f"Unknown proposal type '{kind}'.", 422)
    try:
        parsed = model.model_validate(payload)
    except ValidationError as e:
        first = e.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise AppError("validation_error", f"Invalid proposal: {where}: {first['msg']}", 422) from e
    if isinstance(parsed, ChunkPayload) and parsed.kind not in CHUNK_KINDS:
        raise AppError("validation_error", f"Unknown chunk kind '{parsed.kind}'.", 422)
    return parsed


def text_hash(heading: str, text: str) -> str:
    return hashlib.sha256(f"{heading}\n{text}".encode()).hexdigest()


def _row(r: Any) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "type": r.type,
        "payload": r.payload,
        "rationale": r.rationale,
        "confidence": float(r.confidence) if r.confidence is not None else None,
        "status": r.status,
        "proposed_by": r.proposed_by,
        "reviewer_id": str(r.reviewer_id) if r.reviewer_id else None,
        "decided_at": r.decided_at,
        "note": r.note,
        "created_at": r.created_at,
    }


# ---------------------------------------------------------------------- repository
class ProposalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self,
        kind: str,
        payload: dict[str, Any],
        rationale: str | None,
        confidence: float | None,
        proposed_by: Literal["llm", "user"] = "llm",
    ) -> uuid.UUID:
        conf = None if confidence is None else round(min(1.0, max(0.0, float(confidence))), 3)
        row = await self._s.execute(
            insert(graph_proposals)
            .values(
                type=kind,
                payload=payload,
                rationale=(rationale or "")[:2000] or None,
                confidence=conf,
                proposed_by=proposed_by,
            )
            .returning(graph_proposals.c.id)
        )
        return uuid.UUID(str(row.scalar_one()))

    async def exists_pending_edge(
        self, kind: str, source: str, target: str, edge_type: str
    ) -> bool:
        p = graph_proposals.c.payload
        q = select(func.count()).where(
            graph_proposals.c.type == kind,
            graph_proposals.c.status == "pending",
            p["source"].astext == source,
            p["target"].astext == target,
            p["edge_type"].astext == edge_type,
        )
        return int((await self._s.execute(q)).scalar_one()) > 0

    async def exists_text(self, digest: str) -> bool:
        """A chunk/concept proposal with this text exists (any status but rejected)."""
        q = select(func.count()).where(
            graph_proposals.c.payload["text_hash"].astext == digest,
            graph_proposals.c.status != "rejected",
        )
        return int((await self._s.execute(q)).scalar_one()) > 0

    async def get(self, proposal_id: uuid.UUID, *, lock: bool = False) -> dict[str, Any] | None:
        q: Select[Any] = select(graph_proposals).where(graph_proposals.c.id == proposal_id)
        if lock:
            q = q.with_for_update()
        r = (await self._s.execute(q)).first()
        return _row(r) if r else None

    def _filtered(
        self,
        status: str | None,
        kind: str | None,
        min_confidence: float | None,
        document_id: str | None,
    ) -> list[Any]:
        conds: list[Any] = []
        if status:
            conds.append(graph_proposals.c.status == status)
        if kind:
            conds.append(graph_proposals.c.type == kind)
        if min_confidence is not None:
            conds.append(graph_proposals.c.confidence >= min_confidence)
        if document_id:
            conds.append(graph_proposals.c.payload["document_id"].astext == document_id)
        return conds

    async def list_page(
        self,
        *,
        status: str | None,
        kind: str | None,
        min_confidence: float | None,
        document_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict[str, Any]], int]:
        conds = self._filtered(status, kind, min_confidence, document_id)
        where = and_(*conds) if conds else None
        q = select(graph_proposals)
        c = select(func.count()).select_from(graph_proposals)
        if where is not None:
            q, c = q.where(where), c.where(where)
        rows = (
            await self._s.execute(
                q.order_by(
                    graph_proposals.c.confidence.desc().nulls_last(),
                    graph_proposals.c.created_at.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
        ).all()
        total = int((await self._s.execute(c)).scalar_one())
        return [_row(r) for r in rows], total

    async def ids_matching(
        self, kind: str | None, min_confidence: float, document_id: str | None
    ) -> list[uuid.UUID]:
        conds = self._filtered("pending", kind, min_confidence, document_id)
        q = (
            select(graph_proposals.c.id)
            .where(and_(*conds))
            .order_by(graph_proposals.c.confidence.desc(), graph_proposals.c.created_at)
        )
        return [uuid.UUID(str(r[0])) for r in await self._s.execute(q)]

    async def decide(
        self,
        proposal_id: uuid.UUID,
        status: Literal["approved", "rejected"],
        reviewer: uuid.UUID | None,
        note: str | None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        values: dict[str, Any] = {
            "status": status,
            "reviewer_id": reviewer,
            "decided_at": dt.datetime.now(dt.UTC),
            "note": note,
            "updated_at": func.now(),
        }
        if payload is not None:
            values["payload"] = payload
        res = await self._s.execute(
            update(graph_proposals)
            .where(graph_proposals.c.id == proposal_id, graph_proposals.c.status == "pending")
            .values(**values)
            .returning(graph_proposals.c.id)
        )
        return res.first() is not None

    async def stats(self) -> dict[str, Any]:
        rows = (
            await self._s.execute(
                select(
                    graph_proposals.c.type,
                    graph_proposals.c.status,
                    graph_proposals.c.proposed_by,
                    func.count().label("n"),
                    func.count()
                    .filter(graph_proposals.c.payload["edited"].astext == "true")
                    .label("edited"),
                ).group_by(
                    graph_proposals.c.type, graph_proposals.c.status, graph_proposals.c.proposed_by
                )
            )
        ).all()
        by_type: dict[str, dict[str, int]] = {}
        edited = 0
        for r in rows:
            if r.proposed_by != "llm":
                continue
            t = by_type.setdefault(r.type, {"pending": 0, "approved": 0, "rejected": 0})
            t[r.status] += int(r.n)
            if r.status == "approved":
                edited += int(r.edited)

        def rate(d: dict[str, int]) -> float | None:
            decided = d["approved"] + d["rejected"]
            return round(d["approved"] / decided, 4) if decided else None

        total = {
            k: sum(v[k] for v in by_type.values()) for k in ("pending", "approved", "rejected")
        }
        return {
            "by_type": {k: {**v, "acceptance_rate": rate(v)} for k, v in sorted(by_type.items())},
            "total": {**total, "acceptance_rate": rate(total)},
            "approved_after_edit": edited,
        }


# ---------------------------------------------------------------------- service
@dataclass
class ApplyResult:
    proposal: dict[str, Any]
    applied: dict[str, Any]


class ProposalService:
    def __init__(self, editor: GraphEditor, embedder: EmbeddingProvider | None) -> None:
        self.editor = editor
        self.embedder = embedder
        self.db = editor.db

    # ---- creation (used by the suggest/ingest pipelines) ----
    async def propose(
        self,
        kind: str,
        payload: dict[str, Any],
        rationale: str | None,
        confidence: float | None,
        proposed_by: Literal["llm", "user"] = "llm",
    ) -> uuid.UUID | None:
        """Store a pending proposal; None when it duplicates a pending one or the current graph."""
        parsed = parse_payload(kind, payload)
        data = parsed.model_dump(mode="json")
        async with self.db.sessions()() as session, session.begin():
            repo = ProposalRepository(session)
            if isinstance(parsed, EdgePayload) and await repo.exists_pending_edge(
                kind, parsed.source, parsed.target, parsed.edge_type
            ):
                return None
            if isinstance(parsed, ChunkPayload | ConceptPayload):
                text = parsed.text or ""
                if text:
                    data["text_hash"] = text_hash(parsed.heading, text)
                    if await repo.exists_text(data["text_hash"]):
                        return None
            return await repo.create(kind, data, rationale, confidence, proposed_by)

    # ---- decisions ----
    async def reject(
        self, proposal_id: uuid.UUID, reviewer: uuid.UUID, note: str | None
    ) -> dict[str, Any]:
        async with self.db.sessions()() as session, session.begin():
            repo = ProposalRepository(session)
            current = await repo.get(proposal_id)
            if current is None:
                raise AppError("not_found", "Proposal not found.", 404)
            if not await repo.decide(proposal_id, "rejected", reviewer, note):
                raise AppError("conflict", f"This proposal is already {current['status']}.", 409)
            done = await repo.get(proposal_id)
        await self.editor._after_change(
            reviewer,
            current["payload"].get("subject_id", ""),
            "proposal.reject",
            str(proposal_id),
            {"type": current["type"], "note": note},
            [],
        )
        assert done is not None
        return done

    async def approve(
        self,
        proposal_id: uuid.UUID,
        reviewer: uuid.UUID,
        note: str | None = None,
        edits: dict[str, Any] | None = None,
    ) -> ApplyResult:
        async with self.db.sessions()() as session:
            current = await ProposalRepository(session).get(proposal_id)
        if current is None:
            raise AppError("not_found", "Proposal not found.", 404)
        if current["status"] != "pending":
            raise AppError("conflict", f"This proposal is already {current['status']}.", 409)
        payload = dict(current["payload"])
        if edits:
            merged = {**payload, **edits}
            if "concept" in edits and isinstance(payload.get("concept"), dict):
                merged["concept"] = {**payload["concept"], **edits["concept"]}
            parsed = parse_payload(current["type"], merged)
            stored = parsed.model_dump(mode="json")
            stored.update({"edited": True, "original": {k: payload.get(k) for k in edits}})
            if "text_hash" in payload:
                stored["text_hash"] = payload["text_hash"]
        else:
            parsed = parse_payload(current["type"], payload)
            stored = None

        applied: dict[str, Any]
        chunk_row: dict[str, Any] | None = None
        if isinstance(parsed, EdgePayload):
            applied = await self._apply_edge(current["type"], parsed, reviewer)
        elif isinstance(parsed, ChunkPayload):
            chunk_row, applied = await self._prepare_chunk(proposal_id, parsed)
        else:
            assert isinstance(parsed, ConceptPayload)
            chunk_row, applied = await self._apply_concept(proposal_id, parsed, reviewer)

        try:
            async with self.db.sessions()() as session, session.begin():
                if chunk_row is not None:
                    await self._write_chunk_row(session, chunk_row)
                ok = await ProposalRepository(session).decide(
                    proposal_id, "approved", reviewer, note, stored
                )
                done = await ProposalRepository(session).get(proposal_id)
        except Exception as e:
            raise AppError(
                "partial_apply",
                "The graph was updated but the database step failed. Approve again to finish.",
                503,
            ) from e
        if not ok:
            raise AppError("conflict", "Another reviewer decided this proposal first.", 409)
        concepts = [
            c
            for c in (applied.get("concept_id"), applied.get("source"), applied.get("target"))
            if c
        ]
        await self.editor._after_change(
            reviewer,
            parsed.subject_id,
            "proposal.approve",
            str(proposal_id),
            {"type": current["type"], "applied": applied, "edited": bool(edits), "note": note},
            concepts,
        )
        assert done is not None
        return ApplyResult(done, applied)

    async def _apply_edge(self, kind: str, p: EdgePayload, reviewer: uuid.UUID) -> dict[str, Any]:
        if kind == "add_edge":
            await self.editor.add_edge(
                reviewer,
                p.subject_id,
                GraphEdge(
                    source=p.source,
                    target=p.target,
                    type=p.edge_type,
                    source_kind="llm",
                    status="approved",
                ),
                audit_action="graph.add_edge_from_proposal",
            )
        else:
            try:
                await self.editor.remove_edge(
                    reviewer, p.subject_id, p.source, p.target, p.edge_type, "approved proposal"
                )
            except AppError as e:
                if e.code != "not_found":  # already gone: idempotent
                    raise
        return {"source": p.source, "target": p.target, "edge_type": p.edge_type}

    async def _embed(self, concept_name: str, heading: str, text: str) -> list[float]:
        if self.embedder is None:
            raise AppError(
                "embeddings_unavailable",
                "The embedding provider is not available, so the chunk cannot be indexed.",
                503,
            )
        try:
            return (await self.embedder.embed([f"{concept_name} - {heading}\n{text}"]))[0]
        except Exception as e:
            raise AppError(
                "embeddings_unavailable", "Embedding the chunk failed; try again.", 503
            ) from e

    async def _prepare_chunk(
        self, proposal_id: uuid.UUID, p: ChunkPayload
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        concept = await self.editor.repo.get_concept(p.concept_id)
        if concept is None:
            raise AppError("not_found", f"Concept '{p.concept_id}' does not exist.", 404)
        heading = p.heading or (p.document_name or "Imported notes")
        return await self._chunk(
            proposal_id, concept.name, p.subject_id, p.concept_id, p.kind, heading, p.text
        )

    async def _chunk(
        self,
        proposal_id: uuid.UUID,
        concept_name: str,
        subject_id: str,
        concept_id: str,
        kind: str,
        heading: str,
        text: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        vector = await self._embed(concept_name, heading, text)
        chunk_id = f"llm-{proposal_id.hex[:16]}"
        digest = text_hash(heading, text)
        await self.editor.repo.upsert_chunk(
            ChunkRecord(
                id=chunk_id,
                concept_id=concept_id,
                subject_id=subject_id,
                kind=kind,
                heading=heading,
                text=text,
                order=LLM_CHUNK_ORDER,
                reviewed=True,
                source="llm",
            )
        )
        row = {
            "id": chunk_id,
            "concept_id": concept_id,
            "subject_id": subject_id,
            "kind": kind,
            "heading": heading,
            "text": text,
            "order": LLM_CHUNK_ORDER,
            "reviewed": True,
            "source": "llm",
            "content_hash": digest,
            "embedding": vector,
            "embedding_hash": digest,
            "embedding_model": self.embedder.model if self.embedder else None,
        }
        return row, {"chunk_id": chunk_id, "concept_id": concept_id, "kind": kind}

    async def _write_chunk_row(self, session: AsyncSession, row: dict[str, Any]) -> None:
        stmt = pg_insert(content_chunks).values(**row)
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[content_chunks.c.id],
                set_={k: stmt.excluded[k] for k in row if k != "id"} | {"updated_at": func.now()},
            )
        )

    async def _apply_concept(
        self, proposal_id: uuid.UUID, p: ConceptPayload, reviewer: uuid.UUID
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        concept = ConceptDef(**p.concept.model_dump())
        existing = await self.editor.repo.get_concept(concept.id)
        await self.editor.save_concept(reviewer, p.subject_id, concept, create=existing is None)
        added: list[str] = []
        skipped: list[dict[str, str]] = []
        for pre in dict.fromkeys(p.prerequisites):
            try:
                await self.editor.add_edge(
                    reviewer,
                    p.subject_id,
                    GraphEdge(
                        source=pre,
                        target=concept.id,
                        type=PREREQUISITE,
                        source_kind="llm",
                        status="approved",
                    ),
                    audit_action="graph.add_edge_from_proposal",
                )
                added.append(pre)
            except AppError as e:  # unknown or cyclic prerequisite: keep the concept, report it
                skipped.append({"prerequisite": pre, "reason": e.code})
        applied: dict[str, Any] = {
            "concept_id": concept.id,
            "prerequisites_added": added,
            "prerequisites_skipped": skipped,
        }
        row = None
        if p.text:
            heading = p.heading or concept.name
            row, chunk = await self._chunk(
                proposal_id, concept.name, p.subject_id, concept.id, "overview", heading, p.text
            )
            applied["chunk_id"] = chunk["chunk_id"]
        return row, applied

    async def bulk_approve(
        self, ids: list[uuid.UUID], reviewer: uuid.UUID, note: str | None
    ) -> dict[str, Any]:
        approved: list[str] = []
        failed: list[dict[str, str]] = []
        for pid in ids:
            try:
                await self.approve(pid, reviewer, note)
                approved.append(str(pid))
            except AppError as e:
                failed.append({"id": str(pid), "code": e.code, "message": str(e)})
        return {"approved": approved, "failed": failed}
