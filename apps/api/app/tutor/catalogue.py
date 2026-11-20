"""The concept catalogue: every approved concept of a subject, in a compact prompt format,
plus description embeddings for the hybrid classifier fallback. Cached per subject."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from app.graph.models import GraphConcept
from app.llm.embeddings import EmbeddingProvider
from app.tutor.graph_source import TutorGraph

CATALOGUE_HEADER = "id | name | aliases | keywords | description"
_DESC_CHARS = 90
_MAX_TERMS = 5


def _short(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def catalogue_line(c: GraphConcept) -> str:
    aliases = "; ".join(c.aliases[:_MAX_TERMS])
    keywords = "; ".join(c.keywords[:_MAX_TERMS])
    return f"{c.id} | {c.name} | {aliases} | {keywords} | {_short(c.description, _DESC_CHARS)}"


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


@dataclass
class Catalogue:
    subject_id: str
    concepts: list[GraphConcept]
    text: str  # header + one line per concept
    by_id: dict[str, GraphConcept] = field(default_factory=dict)
    vectors: dict[str, list[float]] | None = None  # description embeddings, built lazily
    vectors_model: str | None = None

    def name(self, concept_id: str) -> str:
        c = self.by_id.get(concept_id)
        return c.name if c else concept_id

    async def ensure_vectors(self, embedder: EmbeddingProvider) -> dict[str, list[float]]:
        key = f"{embedder.model}:{embedder.dim}"
        if self.vectors is None or self.vectors_model != key:
            texts = [
                f"{c.name}. {c.description} {' '.join(c.aliases)} {' '.join(c.keywords)}"
                for c in self.concepts
            ]
            vectors = await embedder.embed(texts)
            self.vectors = {c.id: v for c, v in zip(self.concepts, vectors, strict=True)}
            self.vectors_model = key
        return self.vectors

    async def nearest(
        self, query_vector: list[float], embedder: EmbeddingProvider, k: int = 5
    ) -> list[tuple[str, float]]:
        vectors = await self.ensure_vectors(embedder)
        scored = [(cid, cosine(query_vector, v)) for cid, v in vectors.items()]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:k]


class CatalogueCache:
    """Catalogues per subject, refreshed after `ttl_s` (concept edits show up within minutes)."""

    def __init__(self, ttl_s: float = 300.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_s = ttl_s
        self._clock = clock
        self._items: dict[str, tuple[float, Catalogue]] = {}

    async def get(self, repo: TutorGraph, subject_id: str) -> Catalogue:
        now = self._clock()
        hit = self._items.get(subject_id)
        if hit and now - hit[0] < self.ttl_s:
            return hit[1]
        concepts = [c for c in await repo.list_concepts(subject_id) if c.status == "approved"]
        text = "\n".join([CATALOGUE_HEADER, *(catalogue_line(c) for c in concepts)])
        catalogue = Catalogue(subject_id, concepts, text, {c.id: c for c in concepts})
        if hit and hit[1].vectors is not None and hit[1].text == text:
            # Nothing changed: keep the description embeddings instead of re-embedding.
            catalogue.vectors, catalogue.vectors_model = hit[1].vectors, hit[1].vectors_model
        self._items[subject_id] = (now, catalogue)
        return catalogue

    def invalidate(self, subject_id: str | None = None) -> None:
        if subject_id is None:
            self._items.clear()
        else:
            self._items.pop(subject_id, None)
