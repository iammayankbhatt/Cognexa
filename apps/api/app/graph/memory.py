"""An in-memory concept graph built straight from a subject's source files.

It answers the same read queries the tutor pipeline makes against Neo4j (`TutorGraph`), from
`concepts.yaml` and the concept notes. Used by offline evaluation scripts and by tests that need
the real DSA graph without a seeded Neo4j (CI's Neo4j starts empty). Every edge in the source file
counts as approved, as it does after `seed_neo4j.py`.
"""

from __future__ import annotations

import heapq
import re
from collections import deque
from collections.abc import Iterable

from app.content.loader import load_chunks
from app.content.notes import Chunk
from app.graph.loader import load_subject
from app.graph.models import ConceptFile, GraphConcept, GraphEdge
from app.graph.repository import STOPWORDS, ChunkRecord, PathConcept, _depth

_WORD = re.compile(r"[a-z0-9]+")


class InMemoryGraph:
    def __init__(self, concept_file: ConceptFile, chunks: Iterable[Chunk] = ()) -> None:
        sid = concept_file.subject.id
        self.subject_id = sid
        self.concepts: dict[str, GraphConcept] = {
            c.id: GraphConcept(
                id=c.id,
                subject_id=sid,
                name=c.name,
                cluster=c.cluster,
                difficulty=c.difficulty,
                order_index=c.order_index if c.order_index is not None else i,
                description=c.description,
                aliases=list(c.aliases),
                keywords=list(c.keywords),
            )
            for i, c in enumerate(concept_file.concepts)
        }
        # prereqs_of[b] = [a, ...] for (a)-[:PREREQUISITE_OF]->(b)
        self.prereqs_of: dict[str, list[str]] = {
            c.id: list(c.prerequisites) for c in concept_file.concepts
        }
        self.dependents_of: dict[str, list[str]] = {cid: [] for cid in self.concepts}
        for b, pres in self.prereqs_of.items():
            for a in pres:
                self.dependents_of.setdefault(a, []).append(b)
        self.related: dict[str, set[str]] = {cid: set() for cid in self.concepts}
        for c in concept_file.concepts:
            for r in c.related:
                self.related[c.id].add(r)
                self.related.setdefault(r, set()).add(c.id)
        self.chunks: dict[str, list[ChunkRecord]] = {}
        for ch in chunks:
            self.chunks.setdefault(ch.concept_id, []).append(
                ChunkRecord(
                    id=ch.id,
                    concept_id=ch.concept_id,
                    subject_id=ch.subject_id,
                    kind=ch.kind,
                    heading=ch.heading,
                    text=ch.text,
                    order=ch.order,
                    reviewed=ch.reviewed,
                )
            )

    @classmethod
    def from_subject(cls, subject_id: str = "dsa", *, with_chunks: bool = True) -> InMemoryGraph:
        return cls(load_subject(subject_id), load_chunks(subject_id) if with_chunks else ())

    def _order(self, cid: str) -> int:
        c = self.concepts.get(cid)
        return c.order_index if c else 0

    # ------------------------------------------------------------------ TutorGraph
    async def list_concepts(self, subject_id: str) -> list[GraphConcept]:
        if subject_id != self.subject_id:
            return []
        return sorted(self.concepts.values(), key=lambda c: c.order_index)

    async def search_concepts(
        self, subject_id: str, text: str, limit: int = 10
    ) -> list[tuple[str, float]]:
        """Word overlap with name/aliases/keywords: a stand-in for the Neo4j fulltext index."""
        if subject_id != self.subject_id:
            return []
        words = {w for w in _WORD.findall(text.lower()) if len(w) > 2 and w not in STOPWORDS}
        if not words:
            return []
        scored: list[tuple[str, float]] = []
        for c in self.concepts.values():
            terms = set(_WORD.findall(" ".join([c.name, *c.aliases, *c.keywords]).lower()))
            hits = len(words & terms)
            if hits:
                scored.append((c.id, float(hits)))
        scored.sort(key=lambda t: (-t[1], self._order(t[0])))
        return scored[: max(1, limit)]

    def _bfs(self, start: str, depth: int, neighbours: dict[str, list[str]]) -> list[PathConcept]:
        d = _depth(depth)
        seen = {start: [start]}
        queue = deque([start])
        while queue:
            cur = queue.popleft()
            if len(seen[cur]) - 1 >= d:
                continue
            for nxt in sorted(neighbours.get(cur, []), key=self._order):
                if nxt not in seen and nxt in self.concepts:
                    seen[nxt] = [*seen[cur], nxt]
                    queue.append(nxt)
        out = [
            PathConcept(concept=self.concepts[cid], depth=len(path) - 1, path_ids=path)
            for cid, path in seen.items()
            if cid != start
        ]
        out.sort(key=lambda p: (p.depth, p.concept.order_index))
        return out

    async def get_prerequisites(self, concept_id: str, depth: int = 2) -> list[PathConcept]:
        found = self._bfs(concept_id, depth, self.prereqs_of)
        # BFS walked backwards (target → prerequisite); report paths in edge direction.
        for p in found:
            p.path_ids = list(reversed(p.path_ids))
        return found

    async def get_dependents(self, concept_id: str, depth: int = 1) -> list[PathConcept]:
        return self._bfs(concept_id, depth, self.dependents_of)

    async def get_related(self, concept_id: str) -> list[GraphConcept]:
        ids = sorted(self.related.get(concept_id, set()), key=self._order)
        return [self.concepts[i] for i in ids if i in self.concepts]

    async def get_chunks(
        self, concept_ids: Iterable[str], kinds: Iterable[str] | None = None, limit: int = 50
    ) -> list[ChunkRecord]:
        wanted = set(kinds) if kinds is not None else None
        ids = sorted(set(concept_ids), key=self._order)
        out = [
            ch
            for cid in ids
            for ch in sorted(self.chunks.get(cid, []), key=lambda c: c.order)
            if wanted is None or ch.kind in wanted
        ]
        return out[: max(1, limit)]

    async def list_edges(self, subject_id: str) -> list[GraphEdge]:
        if subject_id != self.subject_id:
            return []
        edges = [
            GraphEdge(source=a, target=b, type="PREREQUISITE_OF")
            for b, pres in self.prereqs_of.items()
            for a in pres
        ]
        # RELATED_TO is undirected; stored smaller id first, as seeding does (app.graph.seed)
        pairs = {tuple(sorted((a, b))) for a, others in self.related.items() for b in others}
        edges.extend(GraphEdge(source=a, target=b, type="RELATED_TO") for a, b in sorted(pairs))
        return edges

    async def topological_order(self, subject_id: str) -> list[str]:
        """Every prerequisite before its dependents; ties broken by order_index (as in Neo4j)."""
        if subject_id != self.subject_id:
            return []
        indeg = {cid: len([p for p in self.prereqs_of.get(cid, []) if p in self.concepts])
                 for cid in self.concepts}  # fmt: skip
        heap = [(self._order(c), c) for c, n in indeg.items() if n == 0]
        heapq.heapify(heap)
        out: list[str] = []
        while heap:
            _, cid = heapq.heappop(heap)
            out.append(cid)
            for nxt in self.dependents_of.get(cid, []):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    heapq.heappush(heap, (self._order(nxt), nxt))
        return out
