"""Public, read-only view of the concept graph (names, clusters and prerequisite edges only).

Nothing here is user data, so it needs no sign-in; the landing and how-it-works pages show it.
The response is cached in memory for a few minutes so public traffic cannot hammer Neo4j.
"""

from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.graph.provider import GraphProvider

router = APIRouter(tags=["graph"])
CACHE_TTL_S = 300.0


class NodeOut(BaseModel):
    id: str
    name: str
    cluster: str
    difficulty: int


class EdgeOut(BaseModel):
    source: str
    target: str
    type: str


class GraphOut(BaseModel):
    subject_id: str
    nodes: list[NodeOut]
    edges: list[EdgeOut]


@router.get("/graph", response_model=GraphOut)
async def public_graph(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Query(max_length=50, pattern=r"^[a-z][a-z0-9_]*$")] = None,
) -> GraphOut:
    sid = subject_id or settings.default_subject_id
    cache: dict[str, tuple[float, GraphOut]] = request.app.state.graph_cache
    hit = cache.get(sid)
    if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
        return hit[1]
    provider: GraphProvider = request.app.state.graph
    repo = provider.repository()
    try:
        concepts = await repo.list_concepts(sid)
        edges = await repo.list_edges(sid)
    except Exception as exc:
        raise AppError("graph_unavailable", "The knowledge graph is unavailable.", 503) from exc
    out = GraphOut(
        subject_id=sid,
        nodes=[
            NodeOut(id=c.id, name=c.name, cluster=c.cluster, difficulty=c.difficulty)
            for c in concepts
            if c.status == "approved"
        ],
        edges=[
            EdgeOut(source=e.source, target=e.target, type=e.type)
            for e in edges
            if e.status == "approved"
        ],
    )
    cache[sid] = (time.monotonic(), out)
    return out
