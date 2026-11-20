"""Recommender rules over a small synthetic graph (pure, no services)."""

from __future__ import annotations

import datetime as dt

import pytest

from app.graph.memory import InMemoryGraph
from app.recommender.engine import (
    ConceptInfo,
    Graph,
    LearnerState,
    baseline,
    completed_concepts,
    frontier_gap,
    recommend,
    review_interval,
    updated_ease,
    weak_concepts,
)

NOW = dt.datetime(2026, 11, 20, 12, tzinfo=dt.UTC)

#  variables → functions → call_stack → recursion → tree_traversal
#  variables → arrays → linked_list
#  arrays → sorting ; recursion → sorting
NAMES = {
    "variables": "Variables",
    "functions": "Functions",
    "call_stack": "Call Stack",
    "recursion": "Recursion",
    "tree_traversal": "Tree Traversals",
    "arrays": "Arrays",
    "linked_list": "Linked List",
    "sorting": "Sorting",
}
EDGES = [
    ("variables", "functions"),
    ("functions", "call_stack"),
    ("call_stack", "recursion"),
    ("recursion", "tree_traversal"),
    ("variables", "arrays"),
    ("arrays", "linked_list"),
    ("arrays", "sorting"),
    ("recursion", "sorting"),
]


def graph() -> Graph:
    return Graph([ConceptInfo(c, n, i) for i, (c, n) in enumerate(NAMES.items())], EDGES)


def state(scores: dict[str, tuple[float, int]] | None = None, **kw: object) -> LearnerState:
    scores = scores or {}
    return LearnerState(
        effective={c: s for c, (s, _) in scores.items()},
        attempts={c: a for c, (_, a) in scores.items()},
        **kw,  # type: ignore[arg-type]
    )


def test_canonical_chain_recommends_call_stack() -> None:
    """Failing tree traversal + weak recursion + weak call_stack (functions mastered) →
    start at Call Stack, with the full path as the explanation."""
    s = state(
        {"variables": (0.9, 4), "functions": (0.8, 4), "call_stack": (0.3, 3),
         "recursion": (0.35, 3), "tree_traversal": (0.2, 4)},
        last_failure={"tree_traversal": NOW, "recursion": NOW - dt.timedelta(days=1)},
    )  # fmt: skip
    recs = recommend(graph(), s)
    top = recs[0]
    assert (top.concept_id, top.rule, top.action) == ("call_stack", "R1", "learn")
    assert top.path == (("call_stack", "recursion"), ("recursion", "tree_traversal"))
    assert top.reason == (
        "You've struggled with Tree Traversals; it builds on Recursion, which builds on "
        "Call Stack — start there."
    )
    assert len({r.concept_id for r in recs}) == len(recs) <= 3


@pytest.mark.parametrize(
    ("scores", "extra", "expected_rule", "expected_concept"),
    [
        # R2: weak concept whose prerequisites are all mastered → review it
        ({"variables": (0.9, 3), "arrays": (0.4, 3)}, {}, "R2", "arrays"),
        # weak by asking (3+ questions, mastery < 0.75) → root cause among unmastered prereqs
        (
            {"variables": (0.9, 3), "functions": (0.9, 3)},
            {"asked_7d": {"recursion": 3}},
            "R1",
            "call_stack",
        ),
        # one attempt only is not enough evidence for R1/R2 → forward progress
        ({"variables": (0.9, 3), "arrays": (0.2, 1)}, {}, "R4", "functions"),
        # due review comes before forward progress
        ({"variables": (0.9, 3), "functions": (0.8, 3)}, {"due": ["functions"]}, "R3", "functions"),
        # R4: lowest order_index unlocked concept that is not yet strong
        (
            {"variables": (0.9, 3), "functions": (0.8, 3), "arrays": (0.8, 3)},
            {},
            "R4",
            "call_stack",
        ),
    ],
)
def test_rules_in_priority_order(
    scores: dict[str, tuple[float, int]],
    extra: dict[str, object],
    expected_rule: str,
    expected_concept: str,
) -> None:
    recs = recommend(graph(), state(scores, **extra))
    assert (recs[0].rule, recs[0].concept_id) == (expected_rule, expected_concept)


def test_new_learner_gets_r5_first_topological_concept() -> None:
    recs = recommend(graph(), LearnerState())
    assert [(r.rule, r.concept_id, r.action) for r in recs] == [("R5", "variables", "learn")]


def test_strong_everywhere_falls_back_to_r5_first_not_strong() -> None:
    s = state({c: (0.95, 5) for c in NAMES if c != "sorting"})
    s.effective["sorting"] = 0.9
    s.attempts["sorting"] = 3
    assert recommend(graph(), s) == []  # nothing left to recommend
    s.effective["sorting"] = 0.7
    recs = recommend(graph(), s)
    assert recs[0].concept_id == "sorting" and recs[0].rule in ("R4", "R5")


def test_weak_ordering_most_recent_failure_then_most_asked() -> None:
    s = state(
        {"variables": (0.9, 3), "arrays": (0.3, 3), "functions": (0.3, 3)},
        last_failure={"arrays": NOW - dt.timedelta(days=2), "functions": NOW},
        asked_7d={"linked_list": 5},
    )
    assert weak_concepts(graph(), s)[:2] == ["functions", "arrays"]
    s2 = state({"variables": (0.9, 3)}, asked_7d={"arrays": 3, "functions": 4})
    assert weak_concepts(graph(), s2) == ["functions", "arrays"]


def test_frontier_prefers_evidence_then_distance() -> None:
    # sorting needs arrays and recursion; recursion's chain was practised badly, arrays untouched
    s = state({"variables": (0.9, 3), "functions": (0.9, 3), "call_stack": (0.2, 3),
               "recursion": (0.3, 3), "sorting": (0.1, 3)})  # fmt: skip
    gap = frontier_gap(graph(), s, "sorting")
    assert gap is not None and gap[0] == "call_stack"
    assert gap[1] == ["call_stack", "recursion", "sorting"]
    all_known = state({c: (0.9, 3) for c in NAMES if c != "sorting"})
    assert frontier_gap(graph(), all_known, "sorting") is None


def test_ties_are_broken_deterministically() -> None:
    s = state({"variables": (0.9, 3), "functions": (0.3, 3), "arrays": (0.3, 3)})
    assert [r.concept_id for r in recommend(graph(), s)] == [
        r.concept_id for r in recommend(graph(), s)
    ]
    assert recommend(graph(), s)[0].concept_id == "functions"  # lower order_index


def test_baseline_ignores_mastery_and_questions() -> None:
    s = state(
        {"variables": (0.1, 9)}, asked_7d={"recursion": 10}, completed={"variables", "functions"}
    )
    recs = baseline(graph(), s)
    assert [r.concept_id for r in recs] == ["call_stack", "recursion", "tree_traversal"]
    assert {r.rule for r in recs} == {"BASELINE"}
    assert completed_concepts({"a": 0.6, "b": 0.59}) == {"a"}


@pytest.mark.parametrize(
    ("previous", "success", "expected"),
    [(0, True, 1), (1, True, 3), (3, True, 7), (7, True, 14), (14, True, 30), (30, True, 30),
     (14, False, 1), (0, False, 1)],
)  # fmt: skip
def test_spaced_review_ladder(previous: int, success: bool, expected: int) -> None:
    assert review_interval(previous, success) == expected


def test_ease_moves_within_bounds() -> None:
    assert updated_ease(2.5, True) == 2.6 and updated_ease(3.0, True) == 3.0
    assert updated_ease(2.5, False) == 2.3 and updated_ease(1.4, False) == 1.3


def test_real_dsa_graph_canonical_chain() -> None:
    """The same rule on the real 69-concept graph: a student failing tree traversals with weak
    recursion and call stack (and solid earlier foundations) is sent to the call stack."""
    mem = InMemoryGraph.from_subject("dsa", with_chunks=False)
    g = Graph(
        [ConceptInfo(c.id, c.name, c.order_index) for c in mem.concepts.values()],
        [(a, b) for b, pres in mem.prereqs_of.items() for a in pres],
    )
    order = g.topological()
    strong = {c: (0.9, 4) for c in order[: order.index("call_stack")]}
    s = state(
        {**strong, "call_stack": (0.3, 3), "recursion": (0.3, 3), "dfs_tree_traversals": (0.2, 4)},
        last_failure={"dfs_tree_traversals": NOW},
    )
    top = recommend(g, s)[0]
    assert top.rule == "R1" and top.concept_id == "call_stack"
    assert top.path[-1][1] == "dfs_tree_traversals"
