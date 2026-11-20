"""Tutor empty-state starter prompts, and the read-only graph queries the recommender needs.

"Continue learning: <concept>" comes from the recommender (app/recommender), which replaced the
Phase 7 temporary syllabus rule (LIM-024).
"""

from __future__ import annotations

from typing import Protocol

from app.graph.models import GraphConcept, GraphEdge

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
