"""Tutor pipeline stages on the real DSA graph (in-memory, from concepts.yaml + notes) with the
FakeProvider. No Neo4j or Postgres needed; the Neo4j-backed queries have their own tests."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pytest

from app.graph.memory import InMemoryGraph
from app.llm.embeddings import FakeEmbeddingProvider
from app.llm.errors import FatalLLMError
from app.llm.fake import FakeProvider
from app.llm.router import LLMRouter
from app.llm.types import CallOptions, Message
from app.tutor.answer import TrailerFilter, citations, parse_followups, strip_trailer
from app.tutor.catalogue import CatalogueCache
from app.tutor.classify import fake_classify, keyword_scores, rrf
from app.tutor.controller import MAX_STEPS
from app.tutor.gather import estimate_tokens, gather
from app.tutor.pipeline import (
    CitationEvent,
    Continuation,
    DoneEvent,
    Event,
    FollowupsEvent,
    TokenEvent,
    TraceEvent,
    TurnInput,
    TutorPipeline,
)
from app.tutor.plain_rag import InMemoryVectorSearch
from app.tutor.trace import ConceptMatch
from app.tutor.traverse import traverse

CANONICAL = (
    "Why does my recursive function crash for big inputs with maximum recursion depth exceeded?"
)


@pytest.fixture(scope="module")
def dsa() -> InMemoryGraph:
    return InMemoryGraph.from_subject("dsa")


def make_pipeline(
    graph: InMemoryGraph,
    provider: FakeProvider | None = None,
    *,
    budget: int = 3000,
    threshold: float = 0.55,
) -> tuple[TutorPipeline, FakeProvider]:
    provider = provider or FakeProvider()
    embedder = FakeEmbeddingProvider(dim=64)
    chunks = [c for cs in graph.chunks.values() for c in cs]
    names = {c.id: c.name for c in graph.concepts.values()}

    async def no_sleep(_: float) -> None:
        return None

    pipeline = TutorPipeline(
        graph=graph,
        llm=LLMRouter([provider], sleep=no_sleep),
        embedder=embedder,
        vectors=InMemoryVectorSearch(chunks, embedder, names),
        catalogues=CatalogueCache(),
        classify_threshold=threshold,
        context_budget=budget,
    )
    return pipeline, provider


async def run(pipeline: TutorPipeline, turn: TurnInput) -> list[Event]:
    return [e async for e in pipeline.run(turn)]


def done(events: Sequence[Event]) -> DoneEvent:
    last = events[-1]
    assert isinstance(last, DoneEvent)
    return last


def classification(
    *picks: tuple[str, float], on_topic: bool = True, intent: str = "explain"
) -> str:
    return json.dumps(
        {
            "is_on_topic": on_topic,
            "concepts": [{"id": c, "confidence": p, "reason": "test"} for c, p in picks],
            "intent": intent,
        }
    )


# ---------------------------------------------------------------- the canonical failure case


async def test_canonical_failure_case_brings_in_call_stack(dsa: InMemoryGraph) -> None:
    """The question never says "stack"; the classifier only picks recursion. The graph walk must
    still put call_stack content in the context (report §1.8)."""
    assert "stack" not in CANONICAL.lower()
    pipeline, _ = make_pipeline(dsa, FakeProvider(script=[classification(("recursion", 0.9))]))
    events = await run(pipeline, TurnInput(question=CANONICAL, agentic=False))
    trace = done(events).trace
    assert [m.id for m in trace.matched] == ["recursion"]
    prereq = {c.id: c for c in trace.concepts if c.role == "prerequisite"}
    assert "call_stack" in prereq and prereq["call_stack"].depth == 1
    assert prereq["call_stack"].path[0].source == "call_stack"
    assert prereq["call_stack"].path[0].target == "recursion"
    assert "call_stack" in {c.concept_id for c in trace.chunks}

    # plain RAG on the same question is recorded for comparison; its result is not asserted
    plain, _ = make_pipeline(dsa)
    plain_trace = done(await run(plain, TurnInput(question=CANONICAL, mode="plain_rag"))).trace
    assert plain_trace.mode == "plain_rag" and len(plain_trace.chunks) > 0


async def test_canonical_case_with_fake_classifier(dsa: InMemoryGraph) -> None:
    """Keyless local mode: the fake classifier's keyword matching gives the same outcome."""
    pipeline, _ = make_pipeline(dsa)
    trace = done(await run(pipeline, TurnInput(question=CANONICAL, agentic=False))).trace
    assert trace.classification_path == "llm"
    assert trace.intent == "debug"
    ids = {m.id for m in trace.matched} | {c.id for c in trace.concepts}
    assert {"recursion", "call_stack"} <= ids
    assert "call_stack" in {c.concept_id for c in trace.chunks}


# ---------------------------------------------------------------- stage 1


async def test_classifier_fallback_when_confidence_low(dsa: InMemoryGraph) -> None:
    pipeline, _ = make_pipeline(dsa, FakeProvider(script=[classification(("heap", 0.2))]))
    trace = done(
        await run(pipeline, TurnInput(question="how does a binary heap insert work", agentic=False))
    ).trace
    assert trace.classification_path == "hybrid"
    assert trace.fallback is not None and trace.fallback.fused
    assert "binary_heap" in trace.fallback.fulltext
    assert trace.matched[0].source == "fusion"


async def test_classifier_fallback_when_json_invalid(dsa: InMemoryGraph) -> None:
    # invalid JSON twice (the router's single repair re-ask fails too)
    provider = FakeProvider(script=["not json", "still not json"])
    pipeline, _ = make_pipeline(dsa, provider)
    trace = done(
        await run(pipeline, TurnInput(question="explain quicksort partitioning", agentic=False))
    ).trace
    assert trace.classification_path == "hybrid"
    assert "quick_sort" in [m.id for m in trace.matched]


async def test_classifier_failure_still_answers_via_fallback(dsa: InMemoryGraph) -> None:
    provider = FakeProvider(script=[FatalLLMError("bad key", status=401)])
    pipeline, _ = make_pipeline(dsa, provider)
    trace = done(
        await run(pipeline, TurnInput(question="what is a hash table", agentic=False))
    ).trace
    assert trace.classification_path == "hybrid" and trace.matched


async def test_invented_concept_ids_are_dropped(dsa: InMemoryGraph) -> None:
    script = [classification(("made_up_concept", 0.99), ("stack", 0.9))]
    pipeline, _ = make_pipeline(dsa, FakeProvider(script=script))
    trace = done(await run(pipeline, TurnInput(question="what is a stack", agentic=False))).trace
    assert [m.id for m in trace.matched] == ["stack"]


async def test_off_topic_costs_no_further_calls(dsa: InMemoryGraph) -> None:
    provider = FakeProvider(script=[classification(on_topic=False, intent="other")])
    pipeline, _ = make_pipeline(dsa, provider)
    events = await run(pipeline, TurnInput(question="what's the best pizza topping?"))
    d = done(events)
    assert d.trace.is_on_topic is False and d.answer is None
    assert "Data Structures & Algorithms" in d.content
    assert len(provider.calls) == 1  # only the classifier
    assert len(d.calls) == 1


async def test_fake_classifier_off_topic_and_follow_up(dsa: InMemoryGraph) -> None:
    pipeline, _provider = make_pipeline(dsa)
    d = done(await run(pipeline, TurnInput(question="what's the weather in Paris tomorrow?")))
    assert d.trace.is_on_topic is False
    # a bare "why?" uses the conversation to find the concept
    history = [Message("user", "explain binary search"), Message("assistant", "Binary search...")]
    d = done(await run(pipeline, TurnInput(question="why?", history=history, agentic=False)))
    assert "binary_search" in [m.id for m in d.trace.matched]


async def test_multi_concept_question(dsa: InMemoryGraph) -> None:
    pipeline, _ = make_pipeline(dsa)
    q = "What is the difference between BFS and DFS?"
    trace = done(await run(pipeline, TurnInput(question=q, agentic=False))).trace
    ids = [m.id for m in trace.matched]
    assert "bfs" in ids and "dfs" in ids and trace.intent == "compare"
    assert {"bfs", "dfs"} <= {c.concept_id for c in trace.chunks}


def test_keyword_scores_and_rrf() -> None:
    rows = [("dijkstra", "Dijkstra's Algorithm", ["shortest path"]), ("bfs", "BFS", ["queue"])]
    assert keyword_scores("what's dijkstra's shortest path?", rows)[0][0] == "dijkstra"
    assert keyword_scores("what's up", rows) == []  # the "s" of what's must not match
    fused = rrf([["a", "b"], ["b", "c"]])
    assert fused[0][0] == "b" and {x for x, _ in fused} == {"a", "b", "c"}


def test_fake_classifier_reads_only_the_catalogue_in_the_prompt() -> None:
    system = "id | name | aliases | keywords | description\nheap | Heap | binary heap | pq | x"
    msgs = [
        Message("system", system),
        Message("user", "<student_question>\nheap?\n</student_question>"),
    ]
    out = fake_classify(msgs, {})
    assert out["concepts"][0]["id"] == "heap" and out["is_on_topic"] is True


# ---------------------------------------------------------------- stages 2 and 3


async def test_personalisation_ranks_weak_prerequisites_first(dsa: InMemoryGraph) -> None:
    matched = [ConceptMatch(id="recursion", name="Recursion", confidence=0.9)]
    # call_stack mastered, functions weak: the weak one must come first despite equal distance
    strong = {"call_stack": 0.9, "stack_heap_memory": 0.95}
    concepts = await traverse(dsa, matched, strong, depth=2)
    prereqs = [c for c in concepts if c.role == "prerequisite"]
    assert prereqs[0].weak is True
    assert [c.id for c in prereqs if not c.weak] == ["call_stack", "stack_heap_memory"]
    first_strong = next(i for i, c in enumerate(prereqs) if not c.weak)
    assert all(c.weak for c in prereqs[:first_strong])
    # never practised counts as weak; nearest first among weak ones
    fresh = await traverse(dsa, matched, {}, depth=2)
    fresh_pre = [c for c in fresh if c.role == "prerequisite"]
    assert all(c.weak for c in fresh_pre) and fresh_pre[0].id == "call_stack"
    assert [c.depth for c in fresh_pre] == sorted(c.depth for c in fresh_pre)
    # related concepts come last
    roles = [c.role for c in fresh]
    assert roles[0] == "matched" and roles[-1] == "related"
    assert "backtracking" in [c.id for c in fresh if c.role == "related"]


async def test_traversal_paths_are_exact_edges(dsa: InMemoryGraph) -> None:
    matched = [ConceptMatch(id="recursion", name="Recursion", confidence=0.9)]
    concepts = await traverse(dsa, matched, {}, depth=2)
    for c in concepts:
        if c.role != "prerequisite":
            continue
        assert len(c.path) == c.depth and c.path[0].source == c.id
        assert c.path[-1].target == "recursion"
        for edge in c.path:  # every edge exists in the source graph
            assert edge.source in dsa.prereqs_of[edge.target]


@pytest.mark.parametrize("budget", [200, 800, 3000])
async def test_token_budget_is_respected(dsa: InMemoryGraph, budget: int) -> None:
    matched = [ConceptMatch(id="dijkstra", name="Dijkstra", confidence=0.9)]
    concepts = await traverse(dsa, matched, {}, depth=2)
    g = await gather(dsa, concepts, "explain", budget)
    assert g.used_tokens <= budget and g.chunks
    assert sum(estimate_tokens(b.text) for b in g.blocks) == g.used_tokens
    assert g.chunks[0].concept_id == "dijkstra"
    assert all(b.title.startswith(f"[{b.concept_id}/") for b in g.blocks)


async def test_intent_chooses_chunk_kinds(dsa: InMemoryGraph) -> None:
    matched = [ConceptMatch(id="merge_sort", name="Merge Sort", confidence=0.9)]
    concepts = await traverse(dsa, matched, {}, depth=1)
    complexity = await gather(dsa, concepts, "complexity", 3000)
    assert complexity.chunks[0].kind == "complexity"
    example = await gather(dsa, concepts, "example", 3000)
    own = [c.kind for c in example.chunks if c.concept_id == "merge_sort"]
    assert set(own) <= {"example", "code"} and own
    debug = await gather(dsa, concepts, "debug", 3000)
    assert debug.chunks[0].kind == "pitfalls"
    support = {c.kind for c in debug.chunks if c.concept_id != "merge_sort"}
    assert support <= {"overview", "pitfalls"}


# ---------------------------------------------------------------- stage 4


async def test_answer_stream_strips_trailer_and_emits_events_in_order(dsa: InMemoryGraph) -> None:
    pipeline, _ = make_pipeline(dsa)
    events = await run(pipeline, TurnInput(question="explain binary search", agentic=False))
    kinds = [type(e).__name__ for e in events]
    assert kinds[0] == "TraceEvent" and kinds[-1] == "DoneEvent"
    first_token = kinds.index("TokenEvent")
    last_token = len(kinds) - 1 - kinds[::-1].index("TokenEvent")
    assert all(k == "TokenEvent" for k in kinds[first_token : last_token + 1])
    assert all(k in ("CitationEvent", "FollowupsEvent") for k in kinds[last_token + 1 : -1])
    streamed = "".join(e.text for e in events if isinstance(e, TokenEvent))
    d = done(events)
    assert "<followups>" not in streamed and "followups>" not in d.content
    assert streamed.strip() == d.content.strip()
    cites = [e.concept_id for e in events if isinstance(e, CitationEvent)]
    assert "binary_search" in cites and cites == d.trace.citations
    fu = [e for e in events if isinstance(e, FollowupsEvent)]
    assert len(fu) == 1 and len(fu[0].items) == 2
    assert d.answer is not None and d.answer.tokens_out > 0


def test_trailer_filter_handles_split_tags() -> None:
    text = 'Answer text [[stack]].\n\n<followups>["a?", "b?"]</followups>'
    for size in (1, 2, 3, 7):
        f = TrailerFilter()
        out = "".join(f.feed(text[i : i + size]) for i in range(0, len(text), size)) + f.flush()
        assert out == "Answer text [[stack]].\n\n", size
        assert parse_followups(f.raw) == ["a?", "b?"]
    f = TrailerFilter()
    assert f.feed("a < b and <foll") == "a < b and "
    assert f.feed("ow the rule") == "<follow the rule"
    assert f.flush() == ""
    g = TrailerFilter()
    assert g.feed("ends with <fo") == "ends with " and g.flush() == "<fo"


def test_followups_parsing_is_lenient_and_bounded() -> None:
    assert parse_followups("x <followups>not json\n- one?\n- two?\n- three?</followups>") == [
        "one?",
        "two?",
    ]
    assert parse_followups('x <followups>["only one"]') == ["only one"]  # unclosed trailer
    assert parse_followups("no trailer") == []
    assert strip_trailer('body\n<followups>["a"]</followups>') == "body"


def test_citations_only_count_concepts_in_context() -> None:
    text = "See [[call_stack]] and [[recursion]], also [[invented]] and [[call_stack]]."
    assert citations(text, ["recursion", "call_stack"]) == ["call_stack", "recursion"]


# ---------------------------------------------------------------- stage 5


async def test_controller_never_exceeds_two_steps(dsa: InMemoryGraph) -> None:
    always_expand = json.dumps({"action": "expand_traversal", "reason": "more"})
    script: list[Any] = [classification(("recursion", 0.9))] + [always_expand] * 5
    provider = FakeProvider(script=script)
    pipeline, _ = make_pipeline(dsa, provider)
    d = done(await run(pipeline, TurnInput(question="explain recursion")))
    steps = d.trace.controller
    assert len(steps) == MAX_STEPS
    assert steps[0].action == "expand_traversal" and steps[1].action == "answer_now"
    assert d.trace.depth == 3
    schemas = [o.json_schema.get("title") for _, o in provider.calls if o.json_schema]
    assert schemas.count("ControllerDecision") == MAX_STEPS
    assert d.answer is not None  # it still answered


async def test_controller_diagnostic_ends_turn_and_reply_resumes_it(dsa: InMemoryGraph) -> None:
    ask = json.dumps(
        {
            "action": "ask_diagnostic",
            "reason": "call stack weak",
            "question": "Quick check: what happens to memory each time a function calls itself?",
            "concept_id": "call_stack",
        }
    )
    provider = FakeProvider(script=[classification(("recursion", 0.9), intent="debug"), ask])
    pipeline, _ = make_pipeline(dsa, provider)
    first = done(await run(pipeline, TurnInput(question=CANONICAL)))
    assert first.trace.diagnostic and first.content.startswith("Quick check:")
    assert first.answer is None and [s.action for s in first.trace.controller] == ["ask_diagnostic"]

    calls_before = len(provider.calls)
    turn = TurnInput(
        question="a new stack frame is added each time",
        continuation=Continuation(trace=first.trace, asked=first.content),
    )
    second = done(await run(pipeline, turn))
    t = second.trace
    assert t.classification_path == "continued" and t.question == CANONICAL
    assert t.diagnostic_reply == "a new stack frame is added each time"
    assert [m.id for m in t.matched] == ["recursion"] and t.diagnostic is None
    assert len(provider.calls) == calls_before + 1  # only the answer: no classify, no controller
    prompt = provider.calls[-1][0][-1].content
    assert "<student_reply>" in prompt and "Quick check:" in prompt


async def test_diagnostic_without_weak_prerequisite_becomes_answer_now(dsa: InMemoryGraph) -> None:
    ask = json.dumps({"action": "ask_diagnostic", "reason": "x", "question": "Quick check: ?"})
    provider = FakeProvider(script=[classification(("recursion", 0.9)), ask])
    pipeline, _ = make_pipeline(dsa, provider)
    all_known = {c: 1.0 for c in dsa.concepts}
    d = done(await run(pipeline, TurnInput(question="explain recursion", mastery=all_known)))
    assert d.trace.controller[0].action == "answer_now" and d.answer is not None


async def test_fake_controller_asks_only_with_evidence(dsa: InMemoryGraph) -> None:
    pick = classification(("recursion", 0.9), intent="debug")
    pipeline, provider = make_pipeline(dsa, FakeProvider(script=[pick]))
    new_student = done(await run(pipeline, TurnInput(question=CANONICAL)))
    assert new_student.trace.diagnostic is None  # never practised: no quiz for new students
    practised_badly = {"call_stack": 0.3}
    provider.push(pick)
    d = done(await run(pipeline, TurnInput(question=CANONICAL, mastery=practised_badly)))
    assert d.trace.diagnostic and "call stack" in d.trace.diagnostic.lower()


async def test_agentic_off_makes_no_controller_call(dsa: InMemoryGraph) -> None:
    pipeline, provider = make_pipeline(dsa)
    d = done(await run(pipeline, TurnInput(question="explain recursion", agentic=False)))
    assert d.trace.controller == []
    titles = [o.json_schema.get("title") for _, o in provider.calls if o.json_schema]
    assert "ControllerDecision" not in titles


# ---------------------------------------------------------------- plain rag


async def test_plain_rag_uses_top_k_and_no_graph(dsa: InMemoryGraph) -> None:
    pipeline, provider = make_pipeline(dsa)
    events = await run(pipeline, TurnInput(question="what is a linked list", mode="plain_rag"))
    d = done(events)
    assert isinstance(events[0], TraceEvent)
    assert d.trace.mode == "plain_rag" and d.trace.concepts == [] and d.trace.matched == []
    assert 0 < len(d.trace.chunks) <= 6
    assert all(c.score is not None for c in d.trace.chunks)
    assert d.trace.used_tokens <= 3000
    system = provider.calls[-1][0][0].content
    assert "prerequisite graph" not in system  # no graph instructions in the baseline
    # only the answer call, no classifier
    assert len(provider.calls) == 1


def test_fake_provider_registered_responders_are_used() -> None:
    from app.llm.fake import FAKE_RESPONDERS

    assert {"Classification", "ControllerDecision"} <= set(FAKE_RESPONDERS)
    opts = CallOptions(json_schema={"title": "Unknown", "type": "object", "properties": {}})
    assert FakeProvider()._default([Message("user", "x")], opts) == "{}"


async def test_fake_classifier_unsure_goes_to_fallback_not_decline(dsa: InMemoryGraph) -> None:
    """BUG-024: no alias phrase matched, so fake mode declined a real DSA question."""
    pipeline, _ = make_pipeline(dsa)
    q = "My recursive factorial in C++ works for small n but segfaults for very large n."
    trace = done(await run(pipeline, TurnInput(question=q, agentic=False))).trace
    assert trace.is_on_topic is True and trace.intent == "debug"
    assert "call_stack" in {c.concept_id for c in trace.chunks}
    pizza = done(await run(pipeline, TurnInput(question="what's the best pizza topping?"))).trace
    assert pizza.is_on_topic is False


async def test_edges_between_matched_concepts_are_recorded(dsa: InMemoryGraph) -> None:
    matched = [
        ConceptMatch(id="recursion", name="Recursion", confidence=0.9),
        ConceptMatch(id="call_stack", name="Call Stack", confidence=0.9),
    ]
    concepts = await traverse(dsa, matched, {}, depth=2)
    call_stack = next(c for c in concepts if c.id == "call_stack")
    assert call_stack.role == "matched"
    assert [(e.source, e.target) for e in call_stack.path] == [("call_stack", "recursion")]
    assert [c.id for c in concepts].count("call_stack") == 1
