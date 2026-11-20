"""Tutor empty-state suggestions: starter prompts and "Continue learning: <concept>".

The concept is chosen by a simple syllabus rule: the first concept in topological order that the
student has not mastered and whose prerequisites are all mastered. Phase 9's adaptive recommender
replaces this rule (it walks prerequisites backward from weak concepts); see progressfile.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from app.graph.models import GraphConcept, GraphEdge
from app.tutor.traverse import WEAK_THRESHOLD

STARTERS: list[dict[str, str]] = [
    {
        "title": "Debug a crash",
        "prompt": "Why does my recursive function crash for big inputs with maximum recursion "
        "depth exceeded?",
    },
    {
        "title": "Compare",
        "prompt": "What is the difference between BFS and DFS, and when do I use each?",
    },
    {"title": "Complexity", "prompt": "Why is binary search O(log n)?"},
    {"title": "Explain", "prompt": "How does a hash table handle collisions?"},
]


class SyllabusGraph(Protocol):
    async def list_concepts(self, subject_id: str) -> list[GraphConcept]: ...

    async def topological_order(self, subject_id: str) -> list[str]: ...

    async def list_edges(self, subject_id: str) -> list[GraphEdge]: ...


def mastered(concept_id: str, mastery: Mapping[str, float]) -> bool:
    score = mastery.get(concept_id)
    return score is not None and score >= WEAK_THRESHOLD


async def next_concept(
    graph: SyllabusGraph, subject_id: str, mastery: Mapping[str, float]
) -> dict[str, Any] | None:
    concepts = {c.id: c for c in await graph.list_concepts(subject_id) if c.status == "approved"}
    prereqs: dict[str, list[str]] = {cid: [] for cid in concepts}
    for e in await graph.list_edges(subject_id):
        if e.type == "PREREQUISITE_OF" and e.status == "approved" and e.target in prereqs:
            prereqs[e.target].append(e.source)
    for cid in await graph.topological_order(subject_id):
        if cid not in concepts or mastered(cid, mastery):
            continue
        if all(mastered(p, mastery) for p in prereqs[cid]):
            c = concepts[cid]
            practised = cid in mastery
            reason = (
                "You have practised this but not mastered it yet."
                if practised
                else (
                    "Next in the syllabus: you have mastered everything it builds on."
                    if prereqs[cid]
                    else "A good place to start: it needs no other concept first."
                )
            )
            return {"concept_id": cid, "name": c.name, "cluster": c.cluster, "reason": reason}
    return None
