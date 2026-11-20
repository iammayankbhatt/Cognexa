"""Per-concept note and bookmark for the signed-in student (the concept page uses it; Phase 10
adds the notes list and revision sheets)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
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
