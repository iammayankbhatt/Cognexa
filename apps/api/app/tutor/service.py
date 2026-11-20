"""Tutor service: one chat turn end to end, around the pipeline.

`prepare` does everything that can fail with a normal HTTP error (thread lookup, input cleaning,
mode permission, the usage guard, saving the student's message) BEFORE the SSE stream starts.
`stream` then runs the pipeline and yields (event, data) pairs; it saves the answer with its trace,
provider, model, tokens and latency, and meters every model call. If the client disconnects
mid-answer, the partial answer is saved with truncated=true (the save is shielded from the
cancellation that the disconnect causes).
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import anyio

from app.auth.deps import CurrentUser
from app.cache.service import LLMCache
from app.core.config import Settings
from app.core.errors import AppError
from app.core.flags import get_flags
from app.db.session import Database
from app.guardrails.input import clean_user_text
from app.guardrails.output import check_output
from app.llm.embeddings import EmbeddingProvider
from app.llm.errors import LLMError
from app.llm.router import LLMRouter
from app.llm.types import LLMResult
from app.tutor.answer import GRAPHRAG_SYSTEM, PLAIN_RAG_SYSTEM
from app.tutor.catalogue import CatalogueCache
from app.tutor.graph_source import TutorGraph
from app.tutor.pipeline import (
    CitationEvent,
    Continuation,
    DoneEvent,
    FollowupsEvent,
    TokenEvent,
    TraceEvent,
    TurnInput,
    TutorPipeline,
)
from app.tutor.plain_rag import VectorSearch
from app.tutor.repository import ChatRepository
from app.tutor.trace import Mode, RetrievalTrace
from app.usage.guard import Ticket, UsageGuard

logger = logging.getLogger(__name__)

DEFAULT_TITLE = "New chat"
TITLE_MAX = 60
_TITLE_TRIM = re.compile(r"^(hi|hey|hello|please|can you|could you|so)[,!\s]+", re.IGNORECASE)

SSEEvent = tuple[str, dict[str, Any]]


def heuristic_title(question: str) -> str:
    """A thread title from the first question: trimmed, capitalised, cut at a word boundary."""
    t = " ".join(question.split())
    t = _TITLE_TRIM.sub("", t).strip(" ?!.,") or t.strip()
    if len(t) > TITLE_MAX:
        t = t[:TITLE_MAX].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return (t[:1].upper() + t[1:]) if t else DEFAULT_TITLE


def trace_payload(trace: RetrievalTrace) -> dict[str, Any]:
    return {**trace.model_dump(mode="json"), "summary": trace.summary()}


@dataclass
class PreparedTurn:
    user: CurrentUser
    thread_id: uuid.UUID
    user_message_id: uuid.UUID
    turn: TurnInput
    ticket: Ticket
    regenerate_of: uuid.UUID | None = None
    started: float = field(default_factory=time.monotonic)


@dataclass
class TutorDeps:
    """Long-lived pieces shared by all requests of one app instance."""

    llm: LLMRouter
    embedder: EmbeddingProvider | None
    catalogues: CatalogueCache
    cache: LLMCache | None


class TutorService:
    def __init__(
        self,
        *,
        db: Database,
        settings: Settings,
        graph: TutorGraph,
        vectors: VectorSearch | None,
        deps: TutorDeps,
        guard: UsageGuard,
    ) -> None:
        self.db = db
        self.settings = settings
        self.guard = guard
        self.pipeline = TutorPipeline(
            graph=graph,
            llm=deps.llm,
            embedder=deps.embedder,
            vectors=vectors,
            catalogues=deps.catalogues,
            cache=deps.cache,
            classify_threshold=settings.classify_threshold,
            context_budget=settings.context_token_budget,
            plain_top_k=settings.plain_rag_top_k,
        )

    # ---------------------------------------------------------------- permissions
    async def check_mode(self, user: CurrentUser, mode: Mode) -> dict[str, bool]:
        async with self.db.sessions()() as session:
            flags = await get_flags(session, self.settings)
        if (
            mode == "plain_rag"
            and user.role == "student"
            and not flags.get("PLAIN_RAG_VISIBLE_TO_STUDENTS", False)
        ):
            raise AppError("mode_not_allowed", "Plain RAG mode is not available.", 403)
        return flags

    # ---------------------------------------------------------------- prepare
    async def prepare(
        self,
        user: CurrentUser,
        thread_id: uuid.UUID,
        text: str,
        mode: Mode,
        *,
        regenerate_of: uuid.UUID | None = None,
        replaces: uuid.UUID | None = None,
    ) -> PreparedTurn:
        """`regenerate_of`: answer the same question again (the old answer is superseded).
        `replaces`: edit-and-resend; that user message and its answers are superseded."""
        flags = await self.check_mode(user, mode)
        limits = await self.guard.limits_for(user)
        question = clean_user_text(text, limits.max_input_chars)

        async with self.db.sessions()() as session:
            repo = ChatRepository(session)
            thread = await repo.get_thread(user.id, thread_id)
            if thread is None:
                raise AppError("not_found", "Chat thread not found.", 404)
            before = None
            reply_to: uuid.UUID | None = None
            if regenerate_of is not None:
                old = await repo.get_message(user.id, regenerate_of)
                question_row = (
                    await repo.get_message(user.id, old["reply_to"])
                    if old is not None and old["reply_to"] is not None
                    else None
                )
                if question_row is None:
                    raise AppError("not_found", "Message not found.", 404)
                reply_to = question_row["id"]
                before = question_row["created_at"]
            elif replaces is not None:
                edited = await repo.get_message(user.id, replaces)
                if edited is None or edited["thread_id"] != thread_id:
                    raise AppError("not_found", "Message not found.", 404)
                before = edited["created_at"]
            history = await repo.history(thread_id, self.settings.tutor_history_turns, before)
            previous = await repo.last_assistant(thread_id, before)
            mastery = await repo.mastery_map(user.id, thread["subject_id"])

        continuation = None
        if previous is not None and mode == "graphrag" and previous["mode"] == "graphrag":
            prior = previous.get("retrieval_trace") or {}
            if prior.get("diagnostic") and not previous.get("truncated"):
                continuation = Continuation(
                    trace=RetrievalTrace.model_validate(prior), asked=str(prior["diagnostic"])
                )
        if continuation is not None:
            # The model sees the original question and the diagnostic exchange explicitly.
            history = history[:-2] if len(history) >= 2 else []

        ticket = await self.guard.admit(user, question, purpose="tutor")
        try:
            async with self.db.sessions()() as session, session.begin():
                repo = ChatRepository(session)
                if regenerate_of is None:
                    if replaces is not None:
                        await repo.supersede_turn(replaces)
                    row = await repo.add_message(
                        thread_id=thread_id, user_id=user.id, role="user", content=question,
                        mode=mode,
                    )  # fmt: skip
                    user_message_id = row["id"]
                    if thread["title"] == DEFAULT_TITLE and not history:
                        await repo.update_thread(
                            user.id, thread_id, title=heuristic_title(question)
                        )
                else:
                    assert reply_to is not None
                    user_message_id = reply_to
                await repo.touch_thread(thread_id)
        except BaseException:
            await self.guard.refund(ticket)
            raise

        turn = TurnInput(
            question=question,
            subject_id=thread["subject_id"],
            mode=mode,
            history=history,
            mastery=mastery,
            agentic=bool(flags.get("AGENTIC_MODE", True)),
            continuation=continuation,
            use_cache=regenerate_of is None,
            max_tokens=min(limits.max_output_tokens, 2000),
        )
        return PreparedTurn(user, thread_id, user_message_id, turn, ticket, regenerate_of)

    # ---------------------------------------------------------------- stream
    async def stream(self, prep: PreparedTurn) -> AsyncIterator[SSEEvent]:
        turn = prep.turn
        parts: list[str] = []
        trace: RetrievalTrace | None = None
        finished = False
        metered = 0
        try:
            async for event in self.pipeline.run(turn):
                if isinstance(event, TraceEvent):
                    trace = event.trace
                    yield "trace", trace_payload(event.trace)
                elif isinstance(event, TokenEvent):
                    parts.append(event.text)
                    yield "token", {"text": event.text}
                elif isinstance(event, CitationEvent):
                    yield "citation", {"concept_id": event.concept_id, "name": event.name}
                elif isinstance(event, FollowupsEvent):
                    yield "followups", {"items": event.items}
                elif isinstance(event, DoneEvent):
                    metered = await self._meter(prep, turn.calls, metered, event.cached)
                    saved = await self._save_answer(prep, event)
                    finished = True
                    yield "done", saved
        except Exception as e:
            finished = True
            if isinstance(e, LLMError):
                logger.warning("tutor turn failed: %s", e)
                code = "llm_unavailable"
                text = "The AI service is not responding right now. Please try again."
            else:
                logger.exception("tutor turn crashed")
                code = "internal_error"
                text = "Something went wrong while answering. Please try again."
            metered = await self._meter(prep, turn.calls, metered, False)
            partial = "".join(parts)
            message_id = None
            if partial:
                message_id = await self._save_partial(prep, partial, trace)
            elif not prep.ticket.recorded:
                await self.guard.refund(prep.ticket)  # nothing reached the student
            yield (
                "error",
                {
                    "code": code,
                    "message": text,
                    "message_id": str(message_id) if message_id else None,
                },
            )
        finally:
            if not finished:
                # Client went away (generator closed or task cancelled). Shield the writes from
                # the cancellation so the partial answer and the calls made so far are kept.
                with anyio.CancelScope(shield=True):
                    try:
                        await self._meter(prep, turn.calls, metered, False)
                        if parts or trace is not None:
                            await self._save_partial(prep, "".join(parts), trace)
                        elif not prep.ticket.recorded:
                            await self.guard.refund(prep.ticket)  # nothing happened yet
                    except Exception:
                        logger.exception("could not save a truncated tutor answer")

    async def _meter(
        self, prep: PreparedTurn, calls: list[LLMResult], already: int, cached: bool
    ) -> int:
        for call in calls[already:]:
            await prep.ticket.record(call)
        if cached:
            await prep.ticket.mark_cached()  # logged as a cache hit (no tokens)
        return len(calls)

    def _system_prompt(self, mode: Mode) -> str:
        return GRAPHRAG_SYSTEM if mode == "graphrag" else PLAIN_RAG_SYSTEM

    async def _save_answer(self, prep: PreparedTurn, done: DoneEvent) -> dict[str, Any]:
        checked = check_output(done.content, self._system_prompt(prep.turn.mode))
        content = checked.text
        trace = done.trace
        answer = done.answer
        values: dict[str, Any] = {
            "thread_id": prep.thread_id,
            "user_id": prep.user.id,
            "role": "assistant",
            "content": content,
            "mode": prep.turn.mode,
            "matched_concepts": [m.model_dump(mode="json") for m in trace.matched],
            "retrieval_trace": trace.model_dump(mode="json"),
            "provider": answer.provider if answer else ("cache" if done.cached else None),
            "model": answer.model if answer else None,
            "tokens_in": sum(c.tokens_in for c in done.calls),
            "tokens_out": sum(c.tokens_out for c in done.calls),
            "latency_ms": int((time.monotonic() - prep.started) * 1000),
            "cached": done.cached,
            "reply_to": prep.user_message_id,
        }
        async with self.db.sessions()() as session, session.begin():
            repo = ChatRepository(session)
            if prep.regenerate_of is not None:
                await repo.supersede(prep.regenerate_of)
            row = await repo.add_message(**values)
            await repo.touch_thread(prep.thread_id)
        if not checked.ok and done.cache_key and self.pipeline.cache is not None:
            await self.pipeline.cache.invalidate_key(done.cache_key)
        return {
            "message_id": str(row["id"]),
            "thread_id": str(prep.thread_id),
            "content": content,
            "moderated": not checked.ok,
            "cached": done.cached,
            "truncated": False,
            "diagnostic": trace.diagnostic is not None,
            "usage": {
                "provider": values["provider"],
                "model": values["model"],
                "tokens_in": values["tokens_in"],
                "tokens_out": values["tokens_out"],
                "latency_ms": values["latency_ms"],
                "model_calls": len(done.calls),
            },
        }

    async def _save_partial(
        self, prep: PreparedTurn, content: str, trace: RetrievalTrace | None
    ) -> uuid.UUID:
        if trace is not None:
            trace = trace.model_copy(update={"truncated": True})
        values: dict[str, Any] = {
            "thread_id": prep.thread_id,
            "user_id": prep.user.id,
            "role": "assistant",
            "content": content,
            "mode": prep.turn.mode,
            "matched_concepts": [m.model_dump(mode="json") for m in trace.matched]
            if trace
            else None,
            "retrieval_trace": trace.model_dump(mode="json") if trace else None,
            "tokens_in": sum(c.tokens_in for c in prep.turn.calls),
            "tokens_out": sum(c.tokens_out for c in prep.turn.calls),
            "latency_ms": int((time.monotonic() - prep.started) * 1000),
            "truncated": True,
            "reply_to": prep.user_message_id,
        }
        async with self.db.sessions()() as session, session.begin():
            repo = ChatRepository(session)
            if prep.regenerate_of is not None:
                await repo.supersede(prep.regenerate_of)
            row = await repo.add_message(**values)
        message_id: uuid.UUID = row["id"]
        return message_id

    # ---------------------------------------------------------------- compare
    async def compare(
        self, user: CurrentUser, question: str, subject_id: str, agentic: bool
    ) -> dict[str, Any]:
        """Both modes on one question (admin/reviewer evaluation view). One quota request."""
        limits = await self.guard.limits_for(user)
        cleaned = clean_user_text(question, limits.max_input_chars)
        out: dict[str, Any] = {"question": cleaned}
        async with self.guard.request(user, cleaned, purpose="compare") as ticket:
            for mode in ("graphrag", "plain_rag"):
                turn = TurnInput(
                    question=cleaned, subject_id=subject_id, mode=mode, agentic=agentic,
                    use_cache=False, max_tokens=min(limits.max_output_tokens, 2000),
                )  # fmt: skip
                started = time.monotonic()
                done: DoneEvent | None = None
                try:
                    async for event in self.pipeline.run(turn):
                        if isinstance(event, DoneEvent):
                            done = event
                except LLMError as e:
                    for call in turn.calls:
                        await ticket.record(call)
                    raise AppError("llm_unavailable", f"The model call failed: {e}", 502) from e
                for call in turn.calls:
                    await ticket.record(call)
                assert done is not None
                checked = check_output(done.content, self._system_prompt(mode))
                out[mode] = {
                    "content": checked.text,
                    "trace": trace_payload(done.trace),
                    "latency_ms": int((time.monotonic() - started) * 1000),
                    "tokens_in": sum(c.tokens_in for c in done.calls),
                    "tokens_out": sum(c.tokens_out for c in done.calls),
                }
        return out
