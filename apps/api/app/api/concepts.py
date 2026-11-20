"""Read-only concept listing for the signed-in user (search box, concept library in Phase 8)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.core.ratelimit import limit_by_user
from app.db.session import get_session
from app.db.tables import concepts

router = APIRouter(tags=["concepts"])


class ConceptOut(BaseModel):
    id: str
    name: str
    cluster: str
    difficulty: int
    order_index: int


@router.get(
    "/concepts",
    response_model=list[ConceptOut],
    dependencies=[Depends(limit_by_user("concept_search"))],
)
async def list_concepts(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    subject_id: Annotated[str | None, Query(max_length=50, pattern=r"^[a-z][a-z0-9_]*$")] = None,
) -> list[ConceptOut]:
    sid = subject_id or settings.default_subject_id
    rows = await session.execute(
        select(
            concepts.c.id,
            concepts.c.name,
            concepts.c.cluster,
            concepts.c.difficulty,
            concepts.c.order_index,
        )
        .where(concepts.c.subject_id == sid)
        .order_by(concepts.c.order_index)
    )
    return [
        ConceptOut(id=r[0], name=r[1], cluster=r[2], difficulty=r[3], order_index=r[4])
        for r in rows
    ]
