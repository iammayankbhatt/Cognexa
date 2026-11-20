"""Per-concept note and bookmark for the signed-in student (the concept page uses it; Phase 10
adds the notes list and revision sheets)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.auth.deps import CurrentUser, get_current_user
from app.core.errors import AppError
from app.db.session import Database, get_database
from app.db.tables import concepts, notes

router = APIRouter(prefix="/notes", tags=["notes"])
User = Annotated[CurrentUser, Depends(get_current_user)]
ConceptId = Annotated[str, Path(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


class NoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str | None = Field(default=None, max_length=20000)
    bookmarked: bool | None = None


def _view(concept_id: str, row: Any | None) -> dict[str, Any]:
    if row is None:
        return {"concept_id": concept_id, "body": "", "bookmarked": False, "updated_at": None}
    return {
        "concept_id": concept_id,
        "body": row.body,
        "bookmarked": row.bookmarked,
        "updated_at": row.updated_at,
    }


def _escape_like(text: str) -> str:
    """Make user text literal inside an ILIKE pattern (escape character "!")."""
    return text.replace("!", "!!").replace("%", "!%").replace("_", "!_")


@router.get("")
async def list_notes(
    user: User,
    db: Annotated[Database, Depends(get_database)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    cluster: Annotated[str | None, Query(pattern=r"^[a-z][a-z0-9_]{0,63}$")] = None,
    bookmarked: bool | None = None,
) -> dict[str, Any]:
    """The student's notes and bookmarks, newest first, with concept name and cluster."""
    cond = notes.c.user_id == user.id
    if bookmarked is not None:
        cond = cond & (notes.c.bookmarked.is_(bookmarked))
    if cluster:
        cond = cond & (concepts.c.cluster == cluster)
    if q and q.strip():
        term = "%" + _escape_like(q.strip()) + "%"
        cond = cond & (
            notes.c.body.ilike(term, escape="!") | concepts.c.name.ilike(term, escape="!")
        )
    async with db.sessions()() as session:
        rows = await session.execute(
            select(notes, concepts.c.name, concepts.c.cluster)
            .select_from(notes.join(concepts, concepts.c.id == notes.c.concept_id))
            .where(cond)
            .order_by(notes.c.updated_at.desc())
            .limit(200)
        )
        items = [
            {
                "concept_id": r.concept_id,
                "name": r.name,
                "cluster": r.cluster,
                "body": r.body,
                "bookmarked": r.bookmarked,
                "updated_at": r.updated_at,
            }
            for r in rows
        ]
    return {"items": items, "total": len(items)}


@router.delete("/{concept_id}", status_code=204)
async def delete_note(
    concept_id: ConceptId, user: User, db: Annotated[Database, Depends(get_database)]
) -> Response:
    async with db.sessions()() as session, session.begin():
        result = await session.execute(
            delete(notes)
            .where(notes.c.user_id == user.id, notes.c.concept_id == concept_id)
            .returning(notes.c.id)
        )
        if result.first() is None:
            raise AppError("not_found", "Note not found.", 404)
    return Response(status_code=204)


@router.get("/{concept_id}")
async def get_note(
    concept_id: ConceptId, user: User, db: Annotated[Database, Depends(get_database)]
) -> dict[str, Any]:
    async with db.sessions()() as session:
        row = (
            await session.execute(
                select(notes).where(notes.c.user_id == user.id, notes.c.concept_id == concept_id)
            )
        ).first()
    return _view(concept_id, row)


@router.put("/{concept_id}")
async def put_note(
    concept_id: ConceptId,
    body: NoteIn,
    user: User,
    db: Annotated[Database, Depends(get_database)],
) -> dict[str, Any]:
    values = body.model_dump(exclude_none=True)
    if not values:
        raise AppError("validation_error", "Send a body or a bookmark flag.", 422)
    async with db.sessions()() as session, session.begin():
        subject = (
            await session.execute(select(concepts.c.subject_id).where(concepts.c.id == concept_id))
        ).scalar_one_or_none()
        if subject is None:
            raise AppError("not_found", "Concept not found.", 404)
        stmt = pg_insert(notes).values(
            user_id=user.id, concept_id=concept_id, subject_id=subject, **values
        )
        row = (
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[notes.c.user_id, notes.c.concept_id],
                    set_={**values, "updated_at": func.now()},
                ).returning(notes)
            )
        ).one()
    return _view(concept_id, row)
