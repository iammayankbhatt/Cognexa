"""Admin graph editor: concepts and edges of the prerequisite graph (reviewer role).

The PREREQUISITE_OF graph must stay a DAG (CLAUDE.md rule 3): an edge that would close a cycle
is refused with 409 `cycle_detected` and the existing chain in error.details.path.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.admin.graph_editor import GraphEditor
from app.auth.deps import CurrentUser, require_role
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.graph.models import ConceptDef, GraphEdge

router = APIRouter(prefix="/admin/graph", tags=["admin"])
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
SUBJECT = r"^[a-z][a-z0-9_]{0,63}$"
CONCEPT = r"^[a-z][a-z0-9_]{1,63}$"
EdgeType = Literal["PREREQUISITE_OF", "RELATED_TO"]
Words = Annotated[list[Annotated[str, Field(min_length=1, max_length=80)]], Field(max_length=40)]


class ConceptIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    cluster: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    difficulty: int = Field(ge=1, le=5)
    description: str = Field(min_length=10, max_length=600)
    aliases: Words = Field(default_factory=list)
    keywords: Words = Field(default_factory=list)
    order_index: int | None = Field(default=None, ge=0, le=100_000)


class ConceptCreate(ConceptIn):
    id: str = Field(pattern=CONCEPT)


class EdgeIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source: str = Field(pattern=CONCEPT)
    target: str = Field(pattern=CONCEPT)
    type: EdgeType
    rationale: str | None = Field(default=None, max_length=1000)
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


def editor(request: Request) -> GraphEditor:
    return GraphEditor.from_request(request)


Editor = Annotated[GraphEditor, Depends(editor)]


def _subject(settings: Settings, subject_id: str | None) -> str:
    return subject_id or settings.default_subject_id


@router.get("")
async def get_graph(
    _: Reviewer,
    ed: Editor,
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Query(pattern=SUBJECT)] = None,
) -> dict[str, Any]:
    """Every concept (all fields) and every edge, any status, for the editor."""
    sid = _subject(settings, subject_id)
    concepts = await ed.repo.list_concepts(sid)
    edges = await ed.repo.list_edges(sid)
    return {
        "subject_id": sid,
        "concepts": [c.model_dump() for c in sorted(concepts, key=lambda c: c.order_index)],
        "edges": [e.model_dump() for e in edges],
    }


@router.post("/concepts", status_code=201)
async def create_concept(
    body: ConceptCreate,
    user: Reviewer,
    ed: Editor,
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Query(pattern=SUBJECT)] = None,
) -> dict[str, Any]:
    concept = ConceptDef(**body.model_dump())
    saved = await ed.save_concept(user.id, _subject(settings, subject_id), concept, create=True)
    return saved.model_dump()


@router.put("/concepts/{concept_id}")
async def update_concept(
    concept_id: Annotated[str, Path(pattern=CONCEPT)],
    body: ConceptIn,
    user: Reviewer,
    ed: Editor,
) -> dict[str, Any]:
    existing = await ed.repo.get_concept(concept_id)
    if existing is None:
        raise AppError("not_found", "Concept not found.", 404)
    concept = ConceptDef(id=concept_id, **body.model_dump())
    saved = await ed.save_concept(user.id, existing.subject_id, concept, create=False)
    return saved.model_dump()


async def _subject_of(ed: GraphEditor, *concept_ids: str) -> str:
    found = [await ed.repo.get_concept(c) for c in concept_ids]
    if any(c is None for c in found):
        raise AppError("not_found", "Both concepts must exist.", 404)
    subjects = {c.subject_id for c in found if c is not None}
    if len(subjects) != 1:
        raise AppError("validation_error", "Both concepts must belong to one subject.", 422)
    return subjects.pop()


@router.post("/edges", status_code=201)
async def add_edge(body: EdgeIn, user: Reviewer, ed: Editor) -> dict[str, Any]:
    sid = await _subject_of(ed, body.source, body.target)
    edge = GraphEdge(
        source=body.source,
        target=body.target,
        type=body.type,
        weight=body.weight,
        source_kind="human",
        status="approved",
        rationale=body.rationale,
    )
    return (await ed.add_edge(user.id, sid, edge)).model_dump()


@router.get("/edges/check")
async def check_edge(
    _: Reviewer,
    ed: Editor,
    source: Annotated[str, Query(pattern=CONCEPT)],
    target: Annotated[str, Query(pattern=CONCEPT)],
) -> dict[str, Any]:
    """Would source -> target (PREREQUISITE_OF) create a cycle? Lets the UI warn before saving."""
    try:
        await ed.check_no_cycle(source, target)
    except AppError as e:
        return {"ok": False, "message": str(e), "path": (e.details or {}).get("path", [])}
    return {"ok": True, "message": None, "path": []}


@router.delete("/edges", status_code=204)
async def remove_edge(
    user: Reviewer,
    ed: Editor,
    source: Annotated[str, Query(pattern=CONCEPT)],
    target: Annotated[str, Query(pattern=CONCEPT)],
    type: Annotated[EdgeType, Query()],
    rationale: Annotated[str | None, Query(max_length=1000)] = None,
) -> Response:
    sid = await _subject_of(ed, source, target)
    await ed.remove_edge(user.id, sid, source, target, type, rationale)
    return Response(status_code=204)


@router.get("/export.yaml")
async def export_yaml(
    _: Reviewer,
    ed: Editor,
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Query(pattern=SUBJECT)] = None,
) -> Response:
    sid = _subject(settings, subject_id)
    text, errors = await ed.export_yaml(sid)
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
    return Response(
        text,
        media_type="application/x-yaml; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="concepts-{sid}-{stamp}.yaml"',
            "X-Validation-Errors": str(len(errors)),
        },
    )
