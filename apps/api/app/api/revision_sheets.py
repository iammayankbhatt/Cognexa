"""Personalised revision sheets, grounded in the concept graph.

POST composes a 1-2 page Markdown sheet from the chosen concepts' notes (default: the student's
weak concepts) plus the overviews of their weak prerequisites, through the usage guard and the
LLM router, with [[concept_id]] citations. Sheets are saved and can be listed, read and deleted.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, insert, select

from app.auth.deps import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import Database, get_database
from app.db.tables import revision_sheets
from app.graph.provider import GraphProvider
from app.guardrails.output import check_output
from app.guardrails.prompts import GUARD_RULES, ContextBlock, render_context
from app.llm.deps import get_llm, get_usage_guard
from app.llm.errors import LLMError
from app.llm.router import LLMRouter
from app.llm.types import Message
from app.mastery.model import MasteryParams
from app.recommender.engine import weak_concepts
from app.recommender.service import build_graph, learner_state
from app.tutor.answer import citations
from app.tutor.gather import fill_budget
from app.tutor.trace import ConceptMatch
from app.tutor.traverse import traverse
from app.usage.guard import UsageGuard

router = APIRouter(prefix="/revision-sheets", tags=["revision"])
User = Annotated[CurrentUser, Depends(get_current_user)]
MAX_CONCEPTS = 5
SHEET_BUDGET = 3500
MAIN_KINDS = ["overview", "mechanism", "complexity", "pitfalls", "example"]
SUPPORT_KINDS = ["overview"]

SHEET_SYSTEM = f"""\
You are Cognexa, writing a personal revision sheet for a Data Structures & Algorithms student.
Use ONLY the course material inside <context>; never add facts that are not there.
Write Markdown, at most about two printed pages: a one-line title, then one section per concept
(## heading) with 3-5 key points, the most common mistakes, the complexity where the material
gives it, and a tiny example when useful. When a concept builds on a weak prerequisite that is in
the context, add a short "Remember first" note about it. Cite concepts inline as [[concept_id]]
using only ids from the context labels. End with "## Test yourself": three short questions
(no answers).

{GUARD_RULES}"""


class SheetIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: str = Field(default="dsa", pattern=r"^[a-z][a-z0-9_]{0,63}$")
    concept_ids: list[str] | None = Field(default=None, min_length=1, max_length=MAX_CONCEPTS)


def _view(r: Any) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "subject_id": r.subject_id,
        "concept_ids": list(r.concept_ids),
        "content": r.content,
        "created_at": r.created_at,
    }


@router.post("", status_code=201)
async def create_sheet(
    body: SheetIn,
    request: Request,
    user: User,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    llm: Annotated[LLMRouter, Depends(get_llm)],
    guard: Annotated[UsageGuard, Depends(get_usage_guard)],
) -> dict[str, Any]:
    provider: GraphProvider = request.app.state.graph
    repo = provider.repository()
    graph = await build_graph(repo, body.subject_id)
    params = MasteryParams.from_settings(settings)
    async with db.sessions()() as session:
        state = await learner_state(
            session, user.id, body.subject_id, params, dt.datetime.now(dt.UTC)
        )
    if body.concept_ids:
        chosen = [c for c in dict.fromkeys(body.concept_ids) if c in graph.concepts]
        if not chosen:
            raise AppError("not_found", "None of those concepts exist.", 404)
    else:
        chosen = weak_concepts(graph, state)[:3]
        if not chosen:
            practised = sorted(state.effective, key=lambda c: state.effective[c])
            chosen = practised[:3]
        if not chosen:
            raise AppError(
                "nothing_to_revise",
                "Take a quiz or the diagnostic first, or choose concepts for the sheet.",
                409,
            )

    matched = [ConceptMatch(id=c, name=graph.name(c), confidence=1.0) for c in chosen]
    trace_concepts = await traverse(repo, matched, state.effective, depth=1)
    weak_prereqs = [c.id for c in trace_concepts if c.role == "prerequisite" and c.weak][:4]
    main = await repo.get_chunks(chosen, MAIN_KINDS, limit=200)
    support = await repo.get_chunks(weak_prereqs, SUPPORT_KINDS, limit=50) if weak_prereqs else []
    rank = {k: i for i, k in enumerate(MAIN_KINDS)}
    main.sort(key=lambda c: (chosen.index(c.concept_id), rank.get(c.kind, 9), c.order))
    gathered = fill_budget([(c, None) for c in [*main, *support]], SHEET_BUDGET)
    if not gathered.blocks:
        raise AppError("not_found", "No course notes are available for those concepts.", 404)

    names = ", ".join(f"{graph.name(c)} [{c}]" for c in chosen)
    weak_names = ", ".join(f"{graph.name(c)} [{c}]" for c in weak_prereqs) or "none"
    blocks: list[ContextBlock] = gathered.blocks
    user_msg = (
        f"{render_context(blocks)}\n\nConcepts for this sheet: {names}\n"
        f"Weak prerequisites to remind about: {weak_names}"
    )
    messages = [Message("system", SHEET_SYSTEM), Message("user", user_msg)]
    async with guard.request(user, user_msg[:2000], purpose="revision") as ticket:
        try:
            result = await llm.complete(messages, max_tokens=1500, temperature=0.2)
        except LLMError as e:
            raise AppError("llm_unavailable", f"The model call failed: {e}", 502) from e
        await ticket.record(result)
    content = check_output(result.text, SHEET_SYSTEM).text.strip()
    async with db.sessions()() as session, session.begin():
        row = (
            await session.execute(
                insert(revision_sheets)
                .values(
                    user_id=user.id, subject_id=body.subject_id, concept_ids=chosen, content=content
                )
                .returning(revision_sheets)
            )
        ).one()
    out = _view(row)
    out["citations"] = citations(content, [c.concept_id for c in gathered.chunks])
    out["names"] = {c: graph.name(c) for c in {*chosen, *weak_prereqs}}
    return out


@router.get("")
async def list_sheets(user: User, db: Annotated[Database, Depends(get_database)]) -> dict[str, Any]:
    async with db.sessions()() as session:
        rows = await session.execute(
            select(revision_sheets)
            .where(revision_sheets.c.user_id == user.id)
            .order_by(revision_sheets.c.created_at.desc())
            .limit(100)
        )
        items = [_view(r) for r in rows]
    return {"items": items, "total": len(items)}


@router.get("/{sheet_id}")
async def get_sheet(
    sheet_id: uuid.UUID, user: User, db: Annotated[Database, Depends(get_database)]
) -> dict[str, Any]:
    async with db.sessions()() as session:
        row = (
            await session.execute(
                select(revision_sheets).where(
                    revision_sheets.c.id == sheet_id, revision_sheets.c.user_id == user.id
                )
            )
        ).first()
    if row is None:
        raise AppError("not_found", "Revision sheet not found.", 404)
    return _view(row)


@router.delete("/{sheet_id}", status_code=204)
async def delete_sheet(
    sheet_id: uuid.UUID, user: User, db: Annotated[Database, Depends(get_database)]
) -> Response:
    async with db.sessions()() as session, session.begin():
        result = await session.execute(
            delete(revision_sheets)
            .where(revision_sheets.c.id == sheet_id, revision_sheets.c.user_id == user.id)
            .returning(revision_sheets.c.id)
        )
        if result.first() is None:
            raise AppError("not_found", "Revision sheet not found.", 404)
    return Response(status_code=204)
