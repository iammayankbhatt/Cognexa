"""Learn API: the student's mastery and a concept's page (notes, links, mastery)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import func, select

from app.auth.deps import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import Database, get_database
from app.db.tables import content_chunks, questions
from app.graph.provider import GraphProvider
from app.mastery.model import MasteryParams
from app.mastery.repository import MasteryRepository

router = APIRouter(tags=["learn"])
User = Annotated[CurrentUser, Depends(get_current_user)]
ID_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"


@router.get("/me/mastery")
async def my_mastery(
    user: User,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str, Query(pattern=ID_PATTERN)] = "dsa",
) -> dict[str, Any]:
    """Every concept the student has a mastery row for, with time decay applied."""
    params = MasteryParams.from_settings(settings)
    async with db.sessions()() as session:
        rows = await MasteryRepository(session, params).view(user.id, subject_id)
    return {
        "subject_id": subject_id,
        "bands": {"weak_below": params.weak_below, "strong_above": params.strong_above},
        "items": rows,
    }


@router.get("/concepts/{concept_id}")
async def concept_page(
    request: Request,
    user: User,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    concept_id: Annotated[str, Path(pattern=ID_PATTERN)],
) -> dict[str, Any]:
    provider: GraphProvider = request.app.state.graph
    graph = provider.repository()
    concept = await graph.get_concept(concept_id)
    if concept is None or concept.status != "approved":
        raise AppError("not_found", "Concept not found.", 404)
    prereqs = await graph.get_prerequisites(concept_id, 1)
    leads_to = await graph.get_dependents(concept_id, 1)
    related = await graph.get_related(concept_id)
    params = MasteryParams.from_settings(settings)
    async with db.sessions()() as session:
        sections = (
            await session.execute(
                select(
                    content_chunks.c.kind,
                    content_chunks.c.heading,
                    content_chunks.c.text,
                    content_chunks.c.order,
                    content_chunks.c.reviewed,
                )
                .where(content_chunks.c.concept_id == concept_id)
                .order_by(content_chunks.c.order)
            )
        ).all()
        n_questions = (
            await session.execute(
                select(func.count())
                .select_from(questions)
                .where(questions.c.concept_id == concept_id, questions.c.status == "active")
            )
        ).scalar_one()
        mastery_rows = {
            r["concept_id"]: r
            for r in await MasteryRepository(session, params).view(user.id, concept.subject_id)
        }

    def link(c: Any) -> dict[str, Any]:
        m = mastery_rows.get(c.id)
        return {
            "id": c.id,
            "name": c.name,
            "cluster": c.cluster,
            "mastery": m["effective"] if m and m["attempts"] > 0 else None,
        }

    own = mastery_rows.get(concept_id)
    return {
        "id": concept.id,
        "subject_id": concept.subject_id,
        "name": concept.name,
        "cluster": concept.cluster,
        "difficulty": concept.difficulty,
        "description": concept.description,
        "aliases": concept.aliases,
        "sections": [
            {"kind": s.kind, "heading": s.heading, "text": s.text, "reviewed": s.reviewed}
            for s in sections
        ],
        "prerequisites": [link(p.concept) for p in prereqs],
        "leads_to": [link(p.concept) for p in leads_to],
        "related": [link(c) for c in related],
        "question_count": int(n_questions),
        "mastery": own if own and own["attempts"] > 0 else None,
    }
