"""Tutor API: chat threads, streamed answers (Server-Sent Events), regenerate, compare.

SSE events, in order: `trace` (classification + traversal, before any token), `token`*,
`citation`*, `followups`, then `done` (message id, usage) or `error`.
"""

from __future__ import annotations

import datetime as dt
import json
import uuid
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.auth.deps import CurrentUser, get_current_user, require_role
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.session import Database, get_database
from app.db.tables import content_chunks
from app.graph.provider import GraphProvider
from app.llm.deps import get_usage_guard
from app.tutor.plain_rag import PgVectorSearch
from app.tutor.repository import ChatRepository
from app.tutor.service import DEFAULT_TITLE, SSEEvent, TutorDeps, TutorService
from app.tutor.suggest import STARTERS, next_concept
from app.usage.guard import UsageGuard

router = APIRouter(prefix="/tutor", tags=["tutor"])

User = Annotated[CurrentUser, Depends(get_current_user)]
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
ModeName = Literal["graphrag", "plain_rag"]
SUBJECT_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"


def get_tutor_service(
    request: Request,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    guard: Annotated[UsageGuard, Depends(get_usage_guard)],
) -> TutorService:
    graph: GraphProvider = request.app.state.graph
    deps: TutorDeps = request.app.state.tutor
    return TutorService(
        db=db,
        settings=settings,
        graph=graph.repository(),
        vectors=PgVectorSearch(db),
        deps=deps,
        guard=guard,
    )


Service = Annotated[TutorService, Depends(get_tutor_service)]


# ---------------------------------------------------------------- schemas


class ThreadIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: str = Field(default="dsa", pattern=SUBJECT_PATTERN)
    title: str | None = Field(default=None, min_length=1, max_length=200)


class ThreadPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(default=None, min_length=1, max_length=200)
    archived: bool | None = None


class MessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=8000)  # the quota's max_input_chars is stricter
    mode: ModeName = "graphrag"


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Literal["incorrect", "incomplete", "off_topic", "harmful", "other"]
    comment: str | None = Field(default=None, max_length=2000)


class FeedbackIn(BaseModel):
    """`rating` 1 / -1 sets a thumb, 0 clears it; `report` flags the answer for review."""

    model_config = ConfigDict(extra="forbid")
    rating: Literal[-1, 0, 1] | None = None
    report: ReportIn | None = None


class EditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1, max_length=8000)


class CompareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=8000)
    subject_id: str = Field(default="dsa", pattern=SUBJECT_PATTERN)
    agentic: bool = False


class ThreadOut(BaseModel):
    id: uuid.UUID
    subject_id: str
    title: str
    archived: bool
    created_at: dt.datetime
    updated_at: dt.datetime
    last_message_at: dt.datetime | None = None
    message_count: int | None = None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    mode: str | None
    retrieval_trace: dict[str, Any] | None
    provider: str | None
    model: str | None
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    cached: bool
    truncated: bool
    reply_to: uuid.UUID | None
    created_at: dt.datetime
    feedback: dict[str, Any] | None = None  # {"rating": -1|1|null, "reported": bool}


def _thread(row: dict[str, Any]) -> ThreadOut:
    return ThreadOut.model_validate(row)


def _message(row: dict[str, Any]) -> MessageOut:
    return MessageOut.model_validate(row)


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'), default=str)}\n\n"


def sse_response(events: AsyncIterator[SSEEvent]) -> StreamingResponse:
    async def body() -> AsyncIterator[str]:
        async for name, data in events:
            yield sse(name, data)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------- threads


@router.post("/threads", status_code=201)
async def create_thread(
    body: ThreadIn, user: User, db: Annotated[Database, Depends(get_database)]
) -> ThreadOut:
    async with db.sessions()() as session, session.begin():
        row = await ChatRepository(session).create_thread(
            user.id, body.subject_id, body.title or DEFAULT_TITLE
        )
    return _thread(row)


@router.get("/threads")
async def list_threads(
    user: User,
    db: Annotated[Database, Depends(get_database)],
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    archived: bool = False,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    async with db.sessions()() as session:
        rows, total = await ChatRepository(session).list_threads(
            user.id, archived=archived, limit=page_size, offset=(page - 1) * page_size, q=q
        )
    return {
        "items": [_thread(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: uuid.UUID, user: User, db: Annotated[Database, Depends(get_database)]
) -> dict[str, Any]:
    async with db.sessions()() as session:
        repo = ChatRepository(session)
        thread = await repo.get_thread(user.id, thread_id)
        if thread is None:
            raise AppError("not_found", "Chat thread not found.", 404)
        messages = await repo.list_messages(thread_id)
        feedback = await repo.feedback_for_thread(user.id, thread_id)
    return {
        "thread": _thread(thread),
        "messages": [_message({**m, "feedback": feedback.get(m["id"])}) for m in messages],
    }


@router.patch("/threads/{thread_id}")
async def patch_thread(
    thread_id: uuid.UUID,
    body: ThreadPatch,
    user: User,
    db: Annotated[Database, Depends(get_database)],
) -> ThreadOut:
    values = body.model_dump(exclude_none=True)
    if not values:
        raise AppError("validation_error", "Nothing to update.", 422)
    if "title" in values:
        values["title"] = " ".join(values["title"].split())
    async with db.sessions()() as session, session.begin():
        row = await ChatRepository(session).update_thread(user.id, thread_id, **values)
    if row is None:
        raise AppError("not_found", "Chat thread not found.", 404)
    return _thread(row)


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: uuid.UUID, user: User, db: Annotated[Database, Depends(get_database)]
) -> Response:
    async with db.sessions()() as session, session.begin():
        deleted = await ChatRepository(session).delete_thread(user.id, thread_id)
    if not deleted:
        raise AppError("not_found", "Chat thread not found.", 404)
    return Response(status_code=204)


# ---------------------------------------------------------------- messages


@router.post("/threads/{thread_id}/messages")
async def post_message(
    thread_id: uuid.UUID, body: MessageIn, user: User, service: Service
) -> StreamingResponse:
    prep = await service.prepare(user, thread_id, body.content, body.mode)
    return sse_response(service.stream(prep))


@router.post("/messages/{message_id}/regenerate")
async def regenerate(
    message_id: uuid.UUID,
    user: User,
    service: Service,
    db: Annotated[Database, Depends(get_database)],
) -> StreamingResponse:
    async with db.sessions()() as session:
        repo = ChatRepository(session)
        msg = await repo.get_message(user.id, message_id)
        if msg is None or msg["role"] != "assistant" or msg["superseded_at"] is not None:
            raise AppError("not_found", "Message not found.", 404)
        latest = await repo.last_assistant(msg["thread_id"])
        if latest is None or latest["id"] != message_id or msg["reply_to"] is None:
            raise AppError("conflict", "Only the latest answer can be regenerated.", 409)
        question = await repo.get_message(user.id, msg["reply_to"])
    if question is None:
        raise AppError("not_found", "Message not found.", 404)
    prep = await service.prepare(
        user, msg["thread_id"], question["content"], msg["mode"] or "graphrag",
        regenerate_of=message_id,
    )  # fmt: skip
    return sse_response(service.stream(prep))


@router.post("/messages/{message_id}/edit")
async def edit_and_resend(
    message_id: uuid.UUID,
    body: EditIn,
    user: User,
    service: Service,
    db: Annotated[Database, Depends(get_database)],
) -> StreamingResponse:
    """Replace the latest question with an edited one and answer it (the old turn is hidden)."""
    async with db.sessions()() as session:
        repo = ChatRepository(session)
        msg = await repo.get_message(user.id, message_id)
        if msg is None or msg["role"] != "user" or msg["superseded_at"] is not None:
            raise AppError("not_found", "Message not found.", 404)
        latest = await repo.last_user_message(msg["thread_id"])
        if latest is None or latest["id"] != message_id:
            raise AppError("conflict", "Only the latest question can be edited.", 409)
    prep = await service.prepare(
        user, msg["thread_id"], body.content, msg["mode"] or "graphrag", replaces=message_id
    )
    return sse_response(service.stream(prep))


@router.post("/messages/{message_id}/feedback")
async def feedback(
    message_id: uuid.UUID,
    body: FeedbackIn,
    user: User,
    db: Annotated[Database, Depends(get_database)],
    request: Request,
) -> dict[str, Any]:
    if body.rating is None and body.report is None:
        raise AppError("validation_error", "Send a rating or a report.", 422)
    values: dict[str, Any] = {}
    if body.rating is not None:
        values["rating"] = body.rating or None
    if body.report is not None:
        comment = " ".join(body.report.comment.split()) if body.report.comment else None
        values.update(report_reason=body.report.reason, comment=comment or None, status="open")
    async with db.sessions()() as session, session.begin():
        repo = ChatRepository(session)
        msg = await repo.get_message(user.id, message_id)
        if msg is None or msg["role"] != "assistant":
            raise AppError("not_found", "Message not found.", 404)
        row = await repo.upsert_feedback(message_id, user.id, values)
    key = (msg.get("retrieval_trace") or {}).get("cache_key")
    if body.report is not None and key:
        deps: TutorDeps = request.app.state.tutor
        if deps.cache is not None:
            await deps.cache.invalidate_key(str(key))  # never serve a reported answer again
    return {
        "message_id": str(message_id),
        "rating": row["rating"],
        "reported": row["report_reason"] is not None,
    }


@router.get("/suggestions")
async def suggestions(
    user: User,
    request: Request,
    db: Annotated[Database, Depends(get_database)],
    subject_id: Annotated[str, Query(pattern=SUBJECT_PATTERN)] = "dsa",
) -> dict[str, Any]:
    """Starter prompts and the next concept to learn (empty state of the tutor)."""
    graph: GraphProvider = request.app.state.graph
    async with db.sessions()() as session:
        mastery = await ChatRepository(session).mastery_map(user.id, subject_id)
    return {
        "starters": STARTERS,
        "continue": await next_concept(graph.repository(), subject_id, mastery),
    }


@router.get("/chunks")
async def chunks(
    _: User,
    db: Annotated[Database, Depends(get_database)],
    ids: Annotated[list[str], Query(min_length=1, max_length=20)],
) -> list[dict[str, Any]]:
    """Text of course-note chunks by id (the "chunks used" list of the Why-this-answer panel)."""
    wanted = [i for i in dict.fromkeys(ids) if len(i) <= 200]
    async with db.sessions()() as session:
        rows = await session.execute(
            select(
                content_chunks.c.id,
                content_chunks.c.concept_id,
                content_chunks.c.kind,
                content_chunks.c.heading,
                content_chunks.c.text,
            ).where(content_chunks.c.id.in_(wanted))
        )
        found = {r.id: dict(r._mapping) for r in rows}
    return [found[i] for i in wanted if i in found]


@router.post("/compare")
async def compare(body: CompareIn, user: Reviewer, service: Service) -> dict[str, Any]:
    """Run GraphRAG and plain RAG on one question; return both answers and traces."""
    return await service.compare(user, body.question, body.subject_id, body.agentic)
