"""Rule-based adaptive recommender (Report Objective 3, §1.8) and its non-adaptive baseline.

Pure, deterministic functions over (graph, learner state). Rules in priority order:
R1 Root-cause repair: for weak concepts W (effective < 0.6 with >= 2 attempts, or asked about >= 3
   times in the last 7 days with effective < 0.75), most recent failure first then most asked,
   walk PREREQUISITE_OF edges backward and recommend the frontier gap: an unmastered prerequisite
   (< 0.6 or never practised) whose own prerequisites are all mastered.
R2 If all of W's prerequisites are mastered: W itself, for focused review.
R3 Due review: concepts whose next_review_at has passed.
R4 Forward progress: the next unlocked concept (all prerequisites >= 0.6, itself < 0.75), lowest
   order_index first.
R5 Brand-new learner: the first concept in topological order that is not yet strong.
BASELINE (user study): fixed syllabus order, the next concept not yet completed (a concept quiz
with >= 60 %), ignoring mastery and questions asked.
"""

from __future__ import annotations

import datetime as dt
import itertools
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

Rule = Literal["R1", "R2", "R3", "R4", "R5", "BASELINE"]
Action = Literal["learn", "practice", "review"]

MASTERED = 0.6  # a prerequisite at or above this is "mastered" for the walk
STRONG = 0.75
WEAK_ATTEMPTS = 2
ASKED_TIMES = 3
EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.UTC)


@dataclass(frozen=True)
class ConceptInfo:
    id: str
    name: str
    order_index: int


@dataclass
class LearnerState:
    effective: dict[str, float] = field(default_factory=dict)  # practised concepts only
    attempts: dict[str, int] = field(default_factory=dict)
    due: list[str] = field(default_factory=list)  # oldest due first
    asked_7d: dict[str, int] = field(default_factory=dict)
    last_failure: dict[str, dt.datetime] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)  # baseline completion

    def practised(self, cid: str) -> bool:
        return cid in self.effective


@dataclass(frozen=True)
class Recommendation:
    concept_id: str
    name: str
    rule: Rule
    reason: str
    action: Action
    path: tuple[tuple[str, str], ...] = ()  # PREREQUISITE_OF edges (source, target), in order


class Graph:
    """Concepts and prerequisite edges: `prereqs[b]` = every a with (a)-[:PREREQUISITE_OF]->(b)."""

    def __init__(self, concepts: Sequence[ConceptInfo], edges: Sequence[tuple[str, str]]) -> None:
        self.concepts = {c.id: c for c in concepts}
        self.prereqs: dict[str, list[str]] = {c.id: [] for c in concepts}
        self.dependents: dict[str, list[str]] = {c.id: [] for c in concepts}
        for a, b in edges:
            if a in self.concepts and b in self.concepts:
                self.prereqs[b].append(a)
                self.dependents[a].append(b)
        for lists in (self.prereqs, self.dependents):
            for k in lists:
                lists[k].sort(key=self.order)

    def order(self, cid: str) -> int:
        c = self.concepts.get(cid)
        return c.order_index if c else 1 << 30

    def name(self, cid: str) -> str:
        c = self.concepts.get(cid)
        return c.name if c else cid

    def topological(self) -> list[str]:
        indeg = {c: len(p) for c, p in self.prereqs.items()}
        ready = sorted((c for c, n in indeg.items() if n == 0), key=self.order)
        out: list[str] = []
        while ready:
            cid = ready.pop(0)
            out.append(cid)
            for d in self.dependents[cid]:
                indeg[d] -= 1
                if indeg[d] == 0:
                    ready.append(d)
                    ready.sort(key=self.order)
        return out


def _mastered(state: LearnerState, cid: str) -> bool:
    return state.effective.get(cid, -1.0) >= MASTERED


def weak_concepts(graph: Graph, state: LearnerState) -> list[str]:
    """W, most important first: most recent failure, then most asked, then syllabus order."""
    weak = []
    for cid in graph.concepts:
        eff = state.effective.get(cid)
        attempts = state.attempts.get(cid, 0)
        by_quiz = eff is not None and eff < MASTERED and attempts >= WEAK_ATTEMPTS
        by_asking = (
            state.asked_7d.get(cid, 0) >= ASKED_TIMES and (eff if eff is not None else 0.0) < STRONG
        )
        if by_quiz or by_asking:
            weak.append(cid)
    return sorted(
        weak,
        key=lambda c: (
            -state.last_failure.get(c, EPOCH).timestamp(),
            -state.asked_7d.get(c, 0),
            graph.order(c),
        ),
    )


def frontier_gap(graph: Graph, state: LearnerState, target: str) -> tuple[str, list[str]] | None:
    """Backward BFS from `target` over prerequisites. Returns (gap, path from gap to target) for
    the best frontier gap, or None when every prerequisite of `target` is mastered.

    A frontier gap is an unmastered ancestor whose own prerequisites are all mastered. When there
    are several, prefer the one with the most practised-but-weak concepts on its path (evidence of
    a real gap, not just an untouched topic), then the nearest, then syllabus order."""
    parent: dict[str, str] = {}
    dist = {target: 0}
    queue = deque([target])
    while queue:
        cur = queue.popleft()
        for p in graph.prereqs.get(cur, []):
            if p not in dist and not _mastered(state, p):
                dist[p] = dist[cur] + 1
                parent[p] = cur
                queue.append(p)
    candidates = [
        c
        for c in dist
        if c != target and all(_mastered(state, p) for p in graph.prereqs.get(c, []))
    ]
    if not candidates:
        return None

    def path_of(c: str) -> list[str]:
        out = [c]
        while out[-1] != target:
            out.append(parent[out[-1]])
        return out

    def evidence(c: str) -> int:
        return sum(1 for x in path_of(c)[:-1] if state.practised(x))

    best = min(candidates, key=lambda c: (-evidence(c), dist[c], graph.order(c)))
    return best, path_of(best)


def _chain_text(graph: Graph, path: Sequence[str]) -> str:
    """'Tree Traversals; it builds on Recursion, which builds on Call Stack'."""
    names = [graph.name(c) for c in reversed(path)]  # target first
    if len(names) == 2:
        return f"{names[0]}; it builds on {names[1]}"
    middle = ", which builds on ".join(names[1:])
    return f"{names[0]}; it builds on {middle}"


def _edges(path: Sequence[str]) -> tuple[tuple[str, str], ...]:
    return tuple(itertools.pairwise(path))


def recommend(graph: Graph, state: LearnerState, limit: int = 3) -> list[Recommendation]:
    out: list[Recommendation] = []
    seen: set[str] = set()

    def add(rec: Recommendation) -> None:
        if rec.concept_id not in seen and len(out) < limit:
            seen.add(rec.concept_id)
            out.append(rec)

    if not state.effective and not state.asked_7d:
        for cid in graph.topological():  # R5: brand-new learner
            add(Recommendation(cid, graph.name(cid), "R5",
                               f"A good place to start: {graph.name(cid)} needs no other concept "
                               "you have not seen yet.", "learn"))  # fmt: skip
            break
        return out

    for w in weak_concepts(graph, state):
        gap = frontier_gap(graph, state, w)
        if gap is not None:  # R1
            cid, path = gap
            struggled = "struggled with" if state.practised(w) else "asked a lot about"
            add(Recommendation(
                cid, graph.name(cid), "R1",
                f"You've {struggled} {_chain_text(graph, path)} — start there.",
                "learn", _edges(path),
            ))  # fmt: skip
        else:  # R2
            add(Recommendation(
                w, graph.name(w), "R2",
                f"You know everything {graph.name(w)} builds on, so a focused review of "
                f"{graph.name(w)} itself is the best next step.",
                "practice",
            ))  # fmt: skip
        if len(out) >= limit:
            return out

    for cid in state.due:  # R3
        if cid in graph.concepts:
            add(Recommendation(cid, graph.name(cid), "R3",
                               f"{graph.name(cid)} is due for review, before you forget it.",
                               "review"))  # fmt: skip

    unlocked = [
        c for c in graph.topological()
        if all(_mastered(state, p) for p in graph.prereqs[c])
        and state.effective.get(c, -1.0) < STRONG
    ]  # fmt: skip
    for cid in sorted(unlocked, key=graph.order):  # R4
        practised = state.practised(cid)
        add(Recommendation(
            cid, graph.name(cid), "R4",
            (f"Next in the syllabus: you have mastered what {graph.name(cid)} builds on."
             if graph.prereqs[cid] else f"{graph.name(cid)} needs no prerequisites."),
            "practice" if practised else "learn",
        ))  # fmt: skip

    if not out:  # R5 also covers a learner who is strong everywhere they practised
        for cid in graph.topological():
            if state.effective.get(cid, -1.0) < STRONG:
                add(Recommendation(cid, graph.name(cid), "R5",
                                   f"{graph.name(cid)} is the first concept you are not yet "
                                   "strong in.", "learn"))  # fmt: skip
                break
    return out


def baseline(graph: Graph, state: LearnerState, limit: int = 3) -> list[Recommendation]:
    """Non-adaptive baseline: fixed syllabus order, skipping completed concepts only."""
    ordered = sorted(graph.concepts, key=graph.order)
    out = []
    for cid in ordered:
        if cid in state.completed:
            continue
        reason = f"Next in the course syllabus: {graph.name(cid)}."
        out.append(Recommendation(cid, graph.name(cid), "BASELINE", reason, "learn"))
        if len(out) >= limit:
            break
    return out


def review_interval(previous_days: int, success: bool) -> int:
    """SM-2-lite ladder: 1 -> 3 -> 7 -> 14 -> 30 days on success, back to 1 on failure."""
    ladder = (1, 3, 7, 14, 30)
    if not success:
        return 1
    for step in ladder:
        if step > previous_days:
            return step
    return ladder[-1]


def updated_ease(ease: float, success: bool) -> float:
    return round(min(3.0, ease + 0.1), 2) if success else round(max(1.3, ease - 0.2), 2)


def completed_concepts(quiz_results: Mapping[str, float]) -> set[str]:
    """Baseline completion: best concept-quiz ratio >= 0.6."""
    return {c for c, ratio in quiz_results.items() if ratio >= MASTERED}
