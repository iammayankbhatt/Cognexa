"""Google Gemini provider (official google-genai SDK, checked against version 3.6.1).

- complete: `client.aio.models.generate_content(model=, contents=, config=GenerateContentConfig)`
- stream:   `await client.aio.models.generate_content_stream(...)` -> async iterator of chunks
- JSON:     `response_mime_type="application/json"` + `response_json_schema`
- embed:    `client.aio.models.embed_content(model=, contents=[...], config=EmbedContentConfig)`
The SDK's own retries are disabled (attempts=1): the router owns retries and fallback.
"""

from __future__ import annotations

import math
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.llm.base import LLMProvider
from app.llm.embeddings import EmbeddingProvider
from app.llm.errors import FatalLLMError, ProviderUnavailableError, RetryableLLMError
from app.llm.types import (
    CallOptions,
    LLMResult,
    Message,
    StreamDone,
    StreamEvent,
    TextDelta,
    estimate_tokens,
)

EMBED_BATCH = 100  # the API accepts at most 100 texts per batch request


def make_client(
    api_key: str | None,
    timeout_s: float,
    http_client: httpx.AsyncClient | None = None,
    api_version: str | None = None,
) -> genai.Client:
    if not api_key:
        raise ProviderUnavailableError("GEMINI_API_KEY is not set", provider="gemini")
    options = types.HttpOptions(
        timeout=int(timeout_s * 1000),  # milliseconds
        retry_options=types.HttpRetryOptions(attempts=1),
        httpx_async_client=http_client,
    )
    if api_version:
        options.api_version = api_version
    return genai.Client(api_key=api_key, http_options=options)


def _translate(e: Exception, provider: str = "gemini") -> Exception:
    if isinstance(e, genai_errors.APIError):
        code = int(getattr(e, "code", 0) or 0)
        message = f"Gemini HTTP {code}: {str(getattr(e, 'message', '') or e)[:300]}"
        if code == 429 or code >= 500 or code == 408:
            return RetryableLLMError(message, provider=provider, status=code)
        return FatalLLMError(message, provider=provider, status=code)
    if isinstance(e, httpx.TimeoutException | httpx.TransportError):
        return RetryableLLMError(f"Gemini request failed: {e!r}", provider=provider)
    return e


def _contents(messages: Sequence[Message]) -> tuple[str | None, list[types.Content]]:
    system = "\n\n".join(m.content for m in messages if m.role == "system") or None
    contents = [
        types.Content(
            role="model" if m.role == "assistant" else "user", parts=[types.Part(text=m.content)]
        )
        for m in messages
        if m.role != "system"
    ]
    return system, contents


def _usage(meta: Any, prompt: str, text: str) -> tuple[int, int]:
    tokens_in = getattr(meta, "prompt_token_count", None) if meta else None
    tokens_out = getattr(meta, "candidates_token_count", None) if meta else None
    return int(tokens_in or estimate_tokens(prompt)), int(tokens_out or estimate_tokens(text))


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(
        self,
        model: str,
        api_key: str | None,
        timeout_s: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
        api_version: str | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._http_client = http_client
        self._api_version = api_version
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = make_client(
                self._api_key, self._timeout_s, self._http_client, self._api_version
            )
        return self._client

    def _config(self, system: str | None, options: CallOptions) -> types.GenerateContentConfig:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=options.temperature,
            max_output_tokens=options.max_tokens,
        )
        if options.json_schema is not None:
            config.response_mime_type = "application/json"
            config.response_json_schema = options.json_schema
        return config

    async def complete(self, messages: Sequence[Message], options: CallOptions) -> LLMResult:
        system, contents = _contents(messages)
        started = time.monotonic()
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model, contents=contents, config=self._config(system, options)
            )
        except Exception as e:
            raise _translate(e) from e
        text = response.text or ""
        tokens_in, tokens_out = _usage(
            response.usage_metadata, "".join(m.content for m in messages), text
        )
        return LLMResult(
            text=text,
            provider=self.name,
            model=self.model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def stream(
        self, messages: Sequence[Message], options: CallOptions
    ) -> AsyncIterator[StreamEvent]:
        system, contents = _contents(messages)
        started = time.monotonic()
        parts: list[str] = []
        meta: Any = None
        try:
            chunks = await self.client.aio.models.generate_content_stream(
                model=self.model, contents=contents, config=self._config(system, options)
            )
            async for chunk in chunks:
                meta = chunk.usage_metadata or meta
                piece = chunk.text
                if piece:
                    parts.append(piece)
                    yield TextDelta(piece)
        except Exception as e:
            raise _translate(e) from e
        text = "".join(parts)
        tokens_in, tokens_out = _usage(meta, "".join(m.content for m in messages), text)
        yield StreamDone(
            LLMResult(
                text=text,
                provider=self.name,
                model=self.model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini embeddings, truncated to `dim` (output_dimensionality) and L2-normalised."""

    def __init__(
        self,
        model: str,
        dim: int,
        api_key: str | None,
        timeout_s: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
        task_type: str = "RETRIEVAL_DOCUMENT",
        api_version: str | None = None,
    ) -> None:
        self.model = model
        self.dim = dim
        self.task_type = task_type
        self._api_key = api_key
        self._timeout_s = timeout_s
        self._http_client = http_client
        self._api_version = api_version
        self._client: genai.Client | None = None

    def for_queries(self) -> GeminiEmbeddingProvider:
        """Same model, tuned for search queries instead of documents."""
        clone = GeminiEmbeddingProvider(
            self.model,
            self.dim,
            self._api_key,
            self._timeout_s,
            self._http_client,
            "RETRIEVAL_QUERY",
            self._api_version,
        )
        clone._client = self._client
        return clone

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = make_client(
                self._api_key, self._timeout_s, self._http_client, self._api_version
            )
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        config = types.EmbedContentConfig(task_type=self.task_type, output_dimensionality=self.dim)
        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start : start + EMBED_BATCH]
            try:
                response = await self.client.aio.models.embed_content(
                    model=self.model, contents=list(batch), config=config
                )
            except Exception as e:
                raise _translate(e) from e
            embeddings = response.embeddings or []
            if len(embeddings) != len(batch):
                raise RetryableLLMError(
                    f"Gemini returned {len(embeddings)} embeddings for {len(batch)} texts",
                    provider="gemini",
                )
            for item in embeddings:
                values = [float(v) for v in (item.values or [])]
                if len(values) != self.dim:
                    raise FatalLLMError(
                        f"embedding has {len(values)} dimensions, "
                        f"expected EMBEDDING_DIM={self.dim}",
                        provider="gemini",
                    )
                norm = math.sqrt(sum(v * v for v in values)) or 1.0
                vectors.append([v / norm for v in values])
        return vectors
