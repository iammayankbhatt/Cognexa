"""Embedding providers (part of the LLM provider layer, CLAUDE.md rule 1).

Phase 3 ships the interface and the deterministic FakeEmbeddingProvider so content can be embedded
and plain RAG works locally without keys. The real Gemini provider (with retries, fallback and
metering) is added to this layer in Phase 5.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod

from app.core.config import Settings

_TOKEN = re.compile(r"[a-z0-9_]+")


class EmbeddingProviderUnavailableError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    """Turns texts into fixed-size vectors."""

    model: str
    dim: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector of length `dim` per input text, in order."""


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashed bag-of-words vectors, L2-normalised.

    Texts that share words get a high cosine similarity, so retrieval over fake embeddings behaves
    sensibly in local development and tests. Not semantic: it knows nothing about synonyms.
    """

    def __init__(self, dim: int = 768, model: str = "fake-embedding") -> None:
        if dim < 8:
            raise ValueError("dim must be at least 8")
        self.dim = dim
        self.model = model

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN.findall(text.lower()):
            digest = hashlib.sha256(token.encode()).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0.0:
            vec[0] = 1.0  # empty / symbol-only text still gets a valid unit vector
            return vec
        return [v / norm for v in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(settings.embedding_dim, settings.embedding_model)
    raise EmbeddingProviderUnavailableError(
        f"embedding provider '{settings.embedding_provider}' is not available yet: "
        "real providers are added to app/llm in Phase 5. Use EMBEDDING_PROVIDER=fake for now."
    )
