"""Review queue for LLM proposals, "Suggest edges", and lecture-notes ingestion (reviewer role).

Ingestion: POST the raw file bytes (`?filename=notes.pdf`, max 10 MB). Text extraction and
splitting happen in the request (so a scanned or broken file is reported at once); tagging the
sections with the LLM runs in a background task and the document row shows its progress.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, insert, select, update

from app.admin.graph_editor import GraphEditor
from app.admin.llm_proposals import (
    MAX_UPLOAD_BYTES,
    extract_text,
    media_type_for,
    split_sections,
    suggest_edges,
    tag_sections,
)
from app.admin.proposals import ProposalRepository, ProposalService
from app.auth.deps import CurrentUser, require_role
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import Database
from app.db.tables import ingest_documents
from app.llm.deps import get_llm, get_usage_guard
from app.llm.router import LLMRouter
from app.usage.guard import UsageGuard

router = APIRouter(prefix="/admin", tags=["admin"])
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
SUBJECT = r"^[a-z][a-z0-9_]{0,63}$"
CONCEPT = r"^[a-z][a-z0-9_]{1,63}$"
Kind = Literal["add_edge", "remove_edge", "tag_chunk", "new_concept"]


def service(request: Request) -> ProposalService:
    return ProposalService(GraphEditor.from_request(request), request.app.state.tutor.embedder)


Service = Annotated[ProposalService, Depends(service)]
LLM = Annotated[LLMRouter, Depends(get_llm)]
Guard = Annotated[UsageGuard, Depends(get_usage_guard)]


class DecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note: str | None = Field(default=None, max_length=1000)
    edits: dict[str, Any] | None = None


class BulkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min_confidence: float = Field(ge=0.5, le=1.0)
    type: Kind | None = None
    document_id: str | None = Field(default=None, max_length=64)
    expected_count: int = Field(ge=1, le=500)
    note: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------- queue
@router.get("/proposals")
async def list_proposals(
    _: Reviewer,
    svc: Service,
    status: Annotated[Literal["pending", "approved", "rejected"] | None, Query()] = "pending",
    type: Annotated[Kind | None, Query()] = None,
    min_confidence: Annotated[float | None, Query(ge=0, le=1)] = None,
    document_id: Annotated[str | None, Query(max_length=64)] = None,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict[str, Any]:
    async with svc.db.sessions()() as session:
        items, total = await ProposalRepository(session).list_page(
            status=status,
            kind=type,
            min_confidence=min_confidence,
            document_id=document_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    names: dict[str, str] = {}
    for sid in {it["payload"].get("subject_id") for it in items} - {None}:
        names |= {c.id: c.name for c in await svc.editor.repo.list_concepts(str(sid))}
    for it in items:
        it["names"] = {k: names.get(k) for k in _concepts_of(it["payload"]) if k in names}
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _concepts_of(payload: dict[str, Any]) -> list[str]:
    ids = [payload.get(k) for k in ("source", "target", "concept_id")]
    ids += list(payload.get("prerequisites") or [])
    return [i for i in ids if isinstance(i, str)]


@router.get("/proposals/stats")
async def proposal_stats(_: Reviewer, svc: Service) -> dict[str, Any]:
    async with svc.db.sessions()() as session:
        return await ProposalRepository(session).stats()


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: uuid.UUID, _: Reviewer, svc: Service) -> dict[str, Any]:
    """The proposal plus a preview of the affected subgraph (the nodes and their neighbours)."""
    async with svc.db.sessions()() as session:
        item = await ProposalRepository(session).get(proposal_id)
    if item is None:
        raise AppError("not_found", "Proposal not found.", 404)
    ids = [i for i in _concepts_of(item["payload"]) if await svc.editor.repo.get_concept(i)]
    sub = await svc.editor.repo.get_subgraph(ids, depth=1) if ids else None
    cycle: dict[str, Any] | None = None
    p = item["payload"]
    if (
        item["type"] == "add_edge"
        and p.get("edge_type") == "PREREQUISITE_OF"
        and item["status"] == "pending"
    ):
        try:
            await svc.editor.check_no_cycle(p["source"], p["target"])
        except AppError as e:
            cycle = {"message": str(e), "path": (e.details or {}).get("path", [])}
    return {
        **item,
        "cycle": cycle,
        "preview": {
            "concepts": [c.model_dump() for c in sub.concepts] if sub else [],
            "edges": [e.model_dump() for e in sub.edges] if sub else [],
        },
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve(
    proposal_id: uuid.UUID, body: DecisionIn, user: Reviewer, svc: Service
) -> dict[str, Any]:
    result = await svc.approve(proposal_id, user.id, body.note, body.edits)
    return {"proposal": result.proposal, "applied": result.applied}


@router.post("/proposals/{proposal_id}/reject")
async def reject(
    proposal_id: uuid.UUID, body: DecisionIn, user: Reviewer, svc: Service
) -> dict[str, Any]:
    if body.edits:
        raise AppError("validation_error", "Edits only apply to approvals.", 422)
    return {"proposal": await svc.reject(proposal_id, user.id, body.note)}


@router.post("/proposals/bulk-approve")
async def bulk_approve(body: BulkIn, user: Reviewer, svc: Service) -> dict[str, Any]:
    """Approve every pending proposal at or above the threshold. `expected_count` must equal the
    number the reviewer confirmed, so a queue that changed in between is not approved blindly."""
    async with svc.db.sessions()() as session:
        ids = await ProposalRepository(session).ids_matching(
            body.type, body.min_confidence, body.document_id
        )
    if len(ids) != body.expected_count:
        raise AppError(
            "conflict",
            f"{len(ids)} proposals match now (you confirmed {body.expected_count}). Review again.",
            409,
            details={"matching": len(ids)},
        )
    return await svc.bulk_approve(ids, user.id, body.note)


@router.get("/proposals-count")
async def count_matching(
    _: Reviewer,
    svc: Service,
    min_confidence: Annotated[float, Query(ge=0.5, le=1)],
    type: Annotated[Kind | None, Query()] = None,
    document_id: Annotated[str | None, Query(max_length=64)] = None,
) -> dict[str, int]:
    async with svc.db.sessions()() as session:
        ids = await ProposalRepository(session).ids_matching(type, min_confidence, document_id)
    return {"matching": len(ids)}


# ---------------------------------------------------------------------- suggest edges
@router.post("/graph/concepts/{concept_id}/suggest-edges")
async def suggest(
    concept_id: str,
    user: Reviewer,
    svc: Service,
    llm: LLM,
    guard: Guard,
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Query(pattern=SUBJECT)] = None,
) -> dict[str, Any]:
    result = await suggest_edges(
        service=svc,
        llm=llm,
        guard=guard,
        user=user,
        subject_id=subject_id or settings.default_subject_id,
        concept_id=concept_id,
    )
    return {"created": result.created, "skipped": result.skipped}


# ---------------------------------------------------------------------- ingestion
def _doc(r: Any) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "subject_id": r.subject_id,
        "filename": r.filename,
        "media_type": r.media_type,
        "size_bytes": r.size_bytes,
        "pages": r.pages,
        "sections": r.sections,
        "proposals": r.proposals,
        "status": r.status,
        "error": r.error,
        "created_at": r.created_at,
    }


async def _read_body(request: Request) -> bytes:
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
        raise AppError("file_too_large", "Files must be 10 MB or smaller.", 413)
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > MAX_UPLOAD_BYTES:
            raise AppError("file_too_large", "Files must be 10 MB or smaller.", 413)
    return bytes(buf)


async def _run_tagging(
    db: Database,
    svc: ProposalService,
    llm: LLMRouter,
    guard: UsageGuard,
    user: CurrentUser,
    subject_id: str,
    doc_id: uuid.UUID,
    filename: str,
    text: str,
) -> None:
    status, error, made = "done", None, 0
    try:
        result = await tag_sections(
            service=svc,
            llm=llm,
            guard=guard,
            user=user,
            subject_id=subject_id,
            sections=split_sections(text),
            document_id=str(doc_id),
            document_name=filename,
        )
        made = result.proposals
        notes = []
        if result.truncated:
            notes.append("only the first 40 sections were tagged")
        if result.stopped:
            notes.append(result.stopped)
        error = "; ".join(notes) or None
    except Exception as e:  # the background task must always leave a final status
        status, error = "failed", f"tagging failed: {type(e).__name__}"
    async with db.sessions()() as session, session.begin():
        await session.execute(
            update(ingest_documents)
            .where(ingest_documents.c.id == doc_id)
            .values(status=status, error=error, proposals=made, updated_at=func.now())
        )


@router.post("/ingest", status_code=202)
async def ingest(
    request: Request,
    background: BackgroundTasks,
    user: Reviewer,
    svc: Service,
    llm: LLM,
    guard: Guard,
    settings: Annotated[Settings, Depends(get_settings)],
    filename: Annotated[str, Query(min_length=1, max_length=255)],
    subject_id: Annotated[str | None, Query(pattern=SUBJECT)] = None,
) -> dict[str, Any]:
    sid = subject_id or settings.default_subject_id
    media_type_for(filename)  # reject unsupported types before reading the body
    data = await _read_body(request)
    db: Database = svc.db
    extracted = extract_text(filename, data)
    sections = split_sections(extracted.text)
    if not sections:
        raise AppError("empty_file", "No text sections were found in this file.", 422)
    async with db.sessions()() as session, session.begin():
        row = (
            await session.execute(
                insert(ingest_documents)
                .values(
                    subject_id=sid,
                    filename=filename,
                    media_type=extracted.media_type,
                    size_bytes=len(data),
                    pages=extracted.pages,
                    sections=len(sections),
                    uploaded_by=user.id,
                )
                .returning(ingest_documents)
            )
        ).one()
    background.add_task(
        _run_tagging, db, svc, llm, guard, user, sid, row.id, filename, extracted.text
    )
    return _doc(row)


@router.get("/ingest")
async def list_documents(
    _: Reviewer, svc: Service, limit: Annotated[int, Query(ge=1, le=100)] = 20
) -> dict[str, Any]:
    async with svc.db.sessions()() as session:
        rows = (
            await session.execute(
                select(ingest_documents).order_by(ingest_documents.c.created_at.desc()).limit(limit)
            )
        ).all()
    return {"items": [_doc(r) for r in rows]}


@router.get("/ingest/{document_id}")
async def get_document(document_id: uuid.UUID, _: Reviewer, svc: Service) -> dict[str, Any]:
    async with svc.db.sessions()() as session:
        row = (
            await session.execute(
                select(ingest_documents).where(ingest_documents.c.id == document_id)
            )
        ).first()
    if row is None:
        raise AppError("not_found", "Document not found.", 404)
    return _doc(row)
