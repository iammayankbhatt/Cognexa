"""The tutor pipeline: runs the stages for one turn and yields events for the SSE stream.

graphrag:  classify → traverse → gather → [controller ≤ 2 steps] → answer (streamed)
plain_rag: embed → top-k pgvector chunks → answer (streamed), same budget and answer prompt
Events, in order: TraceEvent (before any token, so the UI can show "Looking at: ..."), TokenEvent*,
CitationEvent*, FollowupsEvent, DoneEvent. Every model call made is returned in DoneEvent.calls so
the caller can meter it. Persistence and quotas live in the service layer (app.tutor.service).
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field

from app.cache.keys import cache_key
from app.cache.service import LLMCache
from app.graph.repository import GRAPH_UNAVAILABLE
from app.llm.embeddings import EmbeddingProvider
from app.llm.router import LLMRouter
from app.llm.types import LLMResult, Message, StreamDone, TextDelta
from app.tutor.answer import (
    NO_CONTEXT_REPLY,
    OFF_TOPIC_REPLY,
    TrailerFilter,
    answer_messages,
    citations,
    parse_followups,
    strip_trailer,
)
from app.tutor.catalogue import CatalogueCache
from app.tutor.classify import classify
from app.tutor.controller import EXPANDED_DEPTH, MAX_STEPS, decide
from app.tutor.gather import Gathered, fill_budget, gather
from app.tutor.graph_source import TutorGraph
from app.tutor.plain_rag import VectorSearch
from app.tutor.trace import Mode, RetrievalTrace
from app.tutor.traverse import traverse

log = logging.getLogger(__name__)

DEFAULT_DEPTH = 2
ANSWER_MAX_TOKENS = 900


@dataclass
class Continuation:
    """Resume a turn that ended with a diagnostic question: the stored trace and the question."""

    trace: RetrievalTrace
    asked: str


@dataclass
class TurnInput:
    question: str
    subject_id: str = "dsa"
    mode: Mode = "graphrag"
    history: Sequence[Message] = ()
    mastery: Mapping[str, float] = field(default_factory=dict)
    agentic: bool = True
    continuation: Continuation | None = None
    use_cache: bool = True
    max_tokens: int = ANSWER_MAX_TOKENS
    # Every model call made for this turn is appended here as it completes, so a caller can meter
    # the calls even when the client disconnects before DoneEvent.
    calls: list[LLMResult] = field(default_factory=list)


@dataclass
class TraceEvent:
    trace: RetrievalTrace


@dataclass
class TokenEvent:
    text: str


@dataclass
class CitationEvent:
    concept_id: str
    name: str


@dataclass
class FollowupsEvent:
    items: list[str]


@dataclass
class DoneEvent:
    content: str
    trace: RetrievalTrace
    calls: list[LLMResult]
    answer: LLMResult | None  # the streamed answer call (None for canned replies)
    cached: bool = False
    cache_key: str | None = None


Event = TraceEvent | TokenEvent | CitationEvent | FollowupsEvent | DoneEvent


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


def personal_bucket(trace: RetrievalTrace) -> str:
    """Learners share a cached answer only if the same prerequisites are weak AND each was
    practised (or not) in the same way: a practised weak prerequisite makes the controller ask a
    quick check first, which a cached answer would skip (BUG-045)."""
    weak = sorted(
        f"{c.id}:{'practised' if c.mastery is not None else 'new'}"
        for c in trace.concepts
        if c.role == "prerequisite" and c.weak
    )
    return hashlib.sha256(",".join(weak).encode()).hexdigest()[:16] if weak else ""


class TutorPipeline:
    def __init__(
        self,
        *,
        graph: TutorGraph,
        llm: LLMRouter,
        embedder: EmbeddingProvider | None,
        vectors: VectorSearch | None,
        catalogues: CatalogueCache,
        cache: LLMCache | None = None,
        classify_threshold: float = 0.55,
        context_budget: int = 3000,
        plain_top_k: int = 6,
    ) -> None:
        self.graph = graph
        self.llm = llm
        self.embedder = embedder
        self.vectors = vectors
        self.catalogues = catalogues
        self.cache = cache
        self.classify_threshold = classify_threshold
        self.context_budget = context_budget
        self.plain_top_k = plain_top_k

    # ------------------------------------------------------------------ entry point
    async def run(self, turn: TurnInput) -> AsyncIterator[Event]:
        if turn.mode == "plain_rag":
            async for e in self._plain(turn):
                yield e
            return
        started = False
        try:
            async for e in self._graphrag(turn):
                started = True
                yield e
        except GRAPH_UNAVAILABLE as exc:
            # Classification, traversal and gathering all happen before the first event, so if
            # the graph is down nothing has been sent yet: answer from plain RAG instead, say so
            # in the trace (the UI shows a notice) and log it.
            if started or self.embedder is None or self.vectors is None or turn.continuation:
                raise
            log.warning("graph unavailable, answering with plain RAG: %s", type(exc).__name__)
            async for e in self._plain(turn, degraded="graph_unavailable"):
                yield e

    # ------------------------------------------------------------------ graphrag
    async def _graphrag(self, turn: TurnInput) -> AsyncIterator[Event]:
        calls = turn.calls
        trace = RetrievalTrace(
            mode="graphrag", question=turn.question, budget_tokens=self.context_budget
        )
        diagnostic: tuple[str, str] | None = None
        cont = turn.continuation
        t0 = time.monotonic()
        if cont is not None:
            # The student answered our diagnostic question: same concepts, same traversal.
            prior = cont.trace
            trace.question = prior.question
            trace.intent = prior.intent
            trace.classification_path = "continued"
            trace.matched = [m.model_copy(update={"source": "continued"}) for m in prior.matched]
            trace.depth = prior.depth
            trace.controller = list(prior.controller)
            trace.diagnostic_reply = turn.question
            diagnostic = (cont.asked, turn.question)
        else:
            catalogue = await self.catalogues.get(self.graph, turn.subject_id)
            result = await classify(
                question=turn.question,
                history=turn.history,
                catalogue=catalogue,
                llm=self.llm,
                repo=self.graph,
                embedder=self.embedder,
                threshold=self.classify_threshold,
            )
            calls.extend(result.llm_results)
            trace.is_on_topic = result.is_on_topic
            trace.intent = result.intent
            trace.classification_path = "llm" if result.path == "llm" else "hybrid"
            trace.matched = result.matched
            trace.fallback = result.fallback
        trace.timings_ms["classify"] = _ms(t0)

        if not trace.is_on_topic or not trace.matched:
            if not trace.matched:
                trace.classification_path = "none"
            reply = OFF_TOPIC_REPLY if not trace.is_on_topic else NO_CONTEXT_REPLY
            async for e in self._canned(trace, reply, calls):
                yield e
            return

        t1 = time.monotonic()
        trace.concepts = await traverse(self.graph, trace.matched, turn.mastery, depth=trace.depth)
        trace.timings_ms["traverse"] = _ms(t1)
        t2 = time.monotonic()
        gathered = await gather(self.graph, trace.concepts, trace.intent, self.context_budget)
        trace.timings_ms["gather"] = _ms(t2)

        # Response cache: only for self-contained first questions (no history, no diagnostic).
        key: str | None = None
        if turn.use_cache and self.cache is not None and not turn.history and cont is None:
            key = cache_key(
                "resp",
                turn.question,
                mode="graphrag",
                concept_ids=[m.id for m in trace.matched],
                bucket=personal_bucket(trace),
            )
            hit = await self.cache.get_response(key)
            if hit is not None:
                async for e in self._from_cache(trace, gathered, hit, calls, key):
                    yield e
                return

        if turn.agentic and cont is None:
            t3 = time.monotonic()
            step_count = 0
            while step_count < MAX_STEPS:
                step_count += 1
                step = await decide(
                    self.llm,
                    question=turn.question,
                    intent=trace.intent,
                    concepts=trace.concepts,
                    context_tokens=gathered.used_tokens,
                    depth=trace.depth,
                    step=step_count,
                    allow_diagnostic=True,
                    results=calls,
                )
                trace.controller.append(step)
                if step.action == "expand_traversal":
                    trace.depth = EXPANDED_DEPTH
                    trace.concepts = await traverse(
                        self.graph, trace.matched, turn.mastery, depth=trace.depth
                    )
                    gathered = await gather(
                        self.graph, trace.concepts, trace.intent, self.context_budget
                    )
                    continue  # decide once more with the bigger context (bounded by MAX_STEPS)
                break
            trace.timings_ms["controller"] = _ms(t3)
            last = trace.controller[-1] if trace.controller else None
            if last is not None and last.action == "ask_diagnostic" and last.question:
                trace.diagnostic = last.question
                self._fill_chunks(trace, gathered)
                async for e in self._canned(trace, last.question, calls):
                    yield e
                return

        self._fill_chunks(trace, gathered)
        async for e in self._answer(turn, trace, gathered, calls, diagnostic, key):
            yield e

    # ------------------------------------------------------------------ plain rag
    async def _plain(self, turn: TurnInput, degraded: str | None = None) -> AsyncIterator[Event]:
        calls = turn.calls
        trace = RetrievalTrace(
            mode="plain_rag",
            question=turn.question,
            budget_tokens=self.context_budget,
            classification_path="none",
            depth=0,
            degraded=degraded,
        )
        t0 = time.monotonic()
        if self.embedder is None or self.vectors is None:
            raise RuntimeError("plain_rag needs an embedding provider and a vector search")
        vector = (await self.embedder.embed([turn.question]))[0]
        hits = await self.vectors.search(
            turn.subject_id, vector, self.plain_top_k, self.embedder.model
        )
        trace.timings_ms["retrieve"] = _ms(t0)
        gathered = fill_budget(hits, self.context_budget)
        self._fill_chunks(trace, gathered)
        if not gathered.blocks:
            async for e in self._canned(trace, NO_CONTEXT_REPLY, calls):
                yield e
            return
        key: str | None = None
        if turn.use_cache and self.cache is not None and not turn.history:
            key = cache_key(
                "resp",
                turn.question,
                mode="plain_rag",
                concept_ids=sorted({c.concept_id for c in trace.chunks}),
            )
            hit = await self.cache.get_response(key)
            if hit is not None:
                async for e in self._from_cache(trace, gathered, hit, calls, key):
                    yield e
                return
        async for e in self._answer(turn, trace, gathered, calls, None, key):
            yield e

    # ------------------------------------------------------------------ shared
    @staticmethod
    def _fill_chunks(trace: RetrievalTrace, gathered: Gathered) -> None:
        trace.chunks = gathered.chunks
        trace.used_tokens = gathered.used_tokens

    def _names(self, trace: RetrievalTrace) -> dict[str, str]:
        names = {c.id: c.name for c in trace.concepts}
        names.update({m.id: m.name for m in trace.matched})
        return names

    async def _canned(
        self, trace: RetrievalTrace, reply: str, calls: list[LLMResult]
    ) -> AsyncIterator[Event]:
        """A reply that needs no answer call (off-topic, nothing found, a diagnostic question)."""
        yield TraceEvent(trace)
        yield TokenEvent(reply)
        yield DoneEvent(content=reply, trace=trace, calls=calls, answer=None)

    async def _from_cache(
        self,
        trace: RetrievalTrace,
        gathered: Gathered,
        hit: dict[str, object],
        calls: list[LLMResult],
        key: str,
    ) -> AsyncIterator[Event]:
        self._fill_chunks(trace, gathered)
        trace.cached = True
        trace.cache_key = key
        content = str(hit.get("content", ""))
        raw_followups = hit.get("followups")
        followups = [str(f) for f in raw_followups] if isinstance(raw_followups, list) else []
        trace.citations = citations(content, [c.concept_id for c in trace.chunks])
        trace.followups = followups
        yield TraceEvent(trace)
        yield TokenEvent(content)
        names = self._names(trace)
        for cid in trace.citations:
            yield CitationEvent(cid, names.get(cid, cid))
        if followups:
            yield FollowupsEvent(followups)
        yield DoneEvent(
            content=content, trace=trace, calls=calls, answer=None, cached=True, cache_key=key
        )

    async def _answer(
        self,
        turn: TurnInput,
        trace: RetrievalTrace,
        gathered: Gathered,
        calls: list[LLMResult],
        diagnostic: tuple[str, str] | None,
        key: str | None,
    ) -> AsyncIterator[Event]:
        yield TraceEvent(trace)
        question = trace.question if diagnostic else turn.question
        messages = answer_messages(
            mode=trace.mode,
            question=question,
            context=gathered.blocks,
            concepts=trace.concepts,
            history=turn.history,
            diagnostic=diagnostic,
        )
        t0 = time.monotonic()
        filt = TrailerFilter()
        final: LLMResult | None = None
        async for event in self.llm.stream(messages, max_tokens=turn.max_tokens):
            if isinstance(event, TextDelta):
                visible = filt.feed(event.text)
                if visible:
                    yield TokenEvent(visible)
            elif isinstance(event, StreamDone):
                final = event.result
        tail = filt.flush()
        if tail:
            yield TokenEvent(tail)
        trace.timings_ms["answer"] = _ms(t0)
        content = strip_trailer(filt.raw)
        trace.citations = citations(content, [c.concept_id for c in trace.chunks])
        trace.followups = parse_followups(filt.raw)
        names = self._names(trace)
        for cid in trace.citations:
            yield CitationEvent(cid, names.get(cid, cid))
        if trace.followups:
            yield FollowupsEvent(trace.followups)
        if final is not None:
            calls.append(final)
        if key is not None and self.cache is not None and content:
            trace.cache_key = key
            await self.cache.put_response(
                key,
                {"content": content, "followups": trace.followups},
                [c.id for c in trace.concepts] or [c.concept_id for c in trace.chunks],
            )
        yield DoneEvent(content=content, trace=trace, calls=calls, answer=final, cache_key=key)
