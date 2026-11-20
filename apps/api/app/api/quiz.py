"""Quiz API: sessions (create, answer, submit, regrade, read) and history."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.auth.deps import CurrentUser, get_current_user
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.flags import get_flags
from app.db.session import Database, get_database
from app.db.tables import profiles
from app.graph.provider import GraphProvider
from app.llm.deps import get_judge_llm, get_usage_guard
from app.llm.router import LLMRouter
from app.quiz.service import QuizService
from app.study import service as study
from app.tutor.service import TutorDeps
from app.usage.guard import UsageGuard

router = APIRouter(prefix="/quiz", tags=["quiz"])
User = Annotated[CurrentUser, Depends(get_current_user)]
SUBJECT_PATTERN = r"^[a-z][a-z0-9_]{0,63}$"


def get_quiz_service(
    request: Request,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
    judge: Annotated[LLMRouter, Depends(get_judge_llm)],
    guard: Annotated[UsageGuard, Depends(get_usage_guard)],
) -> QuizService:
    provider: GraphProvider = request.app.state.graph
    deps: TutorDeps = request.app.state.tutor
    return QuizService(
        db=db,
        settings=settings,
        judge=judge,
        guard=guard,
        cache=deps.cache,
        graph=provider.repository() if provider.configured else None,
    )


Service = Annotated[QuizService, Depends(get_quiz_service)]


class SessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["concept", "adaptive", "review", "diagnostic", "pretest", "posttest"]
    subject_id: str = Field(default="dsa", pattern=SUBJECT_PATTERN)
    concept_id: str | None = Field(default=None, pattern=SUBJECT_PATTERN)
    count: int | None = Field(default=None, ge=3, le=20)
    timed: bool = False
    feedback_mode: Literal["immediate", "exam"] = "immediate"
    # "Retry the wrong ones": a concept-mode quiz made of these questions (any concepts).
    question_ids: list[str] | None = Field(default=None, min_length=1, max_length=20)


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1, max_length=120)
    # mcq: option id | multi_select: list of ids | true_false: bool | code/short: text | null
    response: str | bool | list[str] | None = None
    time_ms: int | None = Field(default=None, ge=0, le=86_400_000)


class SubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    responses: dict[str, str | bool | list[str] | None] = Field(default_factory=dict, max_length=20)


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionIn,
    user: User,
    service: Service,
    db: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    if body.mode in study.TEST_MODES and user.role == "student":
        # Study tests: only at the right step of the study, timed, and resumed (not restarted)
        # if one is already open.
        async with db.sessions()() as session:
            flags = await get_flags(session, settings)
            profile_row = (
                await session.execute(select(profiles).where(profiles.c.id == user.id))
            ).first()
            state = await study.study_state(
                session,
                dict(profile_row._mapping) if profile_row else {},
                bool(flags.get("STUDY_MODE")),
            )
            existing = (await study.test_sessions(session, user.id)).get(body.mode)
        if existing is not None and existing["submitted_at"] is None:
            return await service.get(user, existing["id"])
        if state["step"] != body.mode:
            raise AppError("not_available", f"The {body.mode} is not available right now.", 409)
        body = body.model_copy(update={"timed": True, "feedback_mode": "exam"})
    return await service.create(
        user,
        mode=body.mode,
        subject_id=body.subject_id,
        concept_id=body.concept_id,
        count=body.count,
        timed=body.timed,
        feedback_mode=body.feedback_mode,
        question_ids=body.question_ids,
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: uuid.UUID, user: User, service: Service) -> dict[str, Any]:
    return await service.get(user, session_id)


@router.post("/sessions/{session_id}/answers")
async def answer(
    session_id: uuid.UUID, body: AnswerIn, user: User, service: Service
) -> dict[str, Any]:
    return await service.answer(user, session_id, body.question_id, body.response, body.time_ms)


@router.post("/sessions/{session_id}/submit")
async def submit(
    session_id: uuid.UUID, body: SubmitIn, user: User, service: Service
) -> dict[str, Any]:
    return await service.submit(user, session_id, body.responses)


@router.post("/sessions/{session_id}/regrade")
async def regrade(session_id: uuid.UUID, user: User, service: Service) -> dict[str, Any]:
    return await service.regrade(user, session_id)


@router.get("/history")
async def history(
    user: User,
    service: Service,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    return await service.history(user, page, page_size)
