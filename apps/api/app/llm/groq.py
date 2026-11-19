"""Groq provider over its OpenAI-compatible Chat Completions HTTP API (plain httpx, no SDK).

Endpoint: POST {GROQ_BASE_URL}/chat/completions. JSON mode uses `response_format: json_object`
(the schema is also given in the system prompt, and the router validates the reply). Streaming
uses Server-Sent Events; usage arrives in the final chunk as `usage` or `x_groq.usage`, and is
estimated if neither is present.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any

import httpx

from app.llm.base import LLMProvider
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


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def _error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("error", {}).get("message") or body)[:300]
    except ValueError:
        return response.text[:300]


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(
        self,
        model: str,
        api_key: str | None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout_s: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self._api_key = api_key
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._client = client or httpx.AsyncClient(timeout=timeout_s)
        self._owns_client = client is None

    def _payload(
        self, messages: Sequence[Message], options: CallOptions, stream: bool
    ) -> dict[str, Any]:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": msgs,
            "temperature": options.temperature,
            "max_completion_tokens": options.max_tokens,
        }
        if options.json_schema is not None:
            payload["response_format"] = {"type": "json_object"}
            schema = json.dumps(options.json_schema, separators=(",", ":"))
            msgs.insert(
                0,
                {
                    "role": "system",
                    "content": "Reply with a single JSON object that matches this JSON Schema: "
                    + schema,
                },
            )
        if stream:
            payload["stream"] = True
        return payload

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderUnavailableError("GROQ_API_KEY is not set", provider=self.name)
        return {"Authorization": f"Bearer {self._api_key}"}

    def _raise_for(self, response: httpx.Response) -> None:
        status = response.status_code
        if status < 400:
            return
        message = f"Groq HTTP {status}: {_error_message(response)}"
        if status == 429 or status >= 500 or status == 408:
            raise RetryableLLMError(
                message, provider=self.name, status=status, retry_after_s=_retry_after(response)
            )
        raise FatalLLMError(message, provider=self.name, status=status)

    async def complete(self, messages: Sequence[Message], options: CallOptions) -> LLMResult:
        headers = self._headers()
        started = time.monotonic()
        try:
            response = await self._client.post(
                self._url, json=self._payload(messages, options, stream=False), headers=headers
            )
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise RetryableLLMError(f"Groq request failed: {e!r}", provider=self.name) from e
        self._raise_for(response)
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise RetryableLLMError("Groq returned an unexpected body", provider=self.name) from e
        usage = body.get("usage") or {}
        prompt = "".join(m.content for m in messages)
        return LLMResult(
            text=text,
            provider=self.name,
            model=str(body.get("model") or self.model),
            tokens_in=int(usage.get("prompt_tokens") or estimate_tokens(prompt)),
            tokens_out=int(usage.get("completion_tokens") or estimate_tokens(text)),
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def stream(
        self, messages: Sequence[Message], options: CallOptions
    ) -> AsyncIterator[StreamEvent]:
        headers = self._headers()
        started = time.monotonic()
        parts: list[str] = []
        usage: dict[str, Any] = {}
        model = self.model
        try:
            async with self._client.stream(
                "POST",
                self._url,
                json=self._payload(messages, options, stream=True),
                headers=headers,
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    self._raise_for(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    model = chunk.get("model") or model
                    usage = chunk.get("usage") or (chunk.get("x_groq") or {}).get("usage") or usage
                    for choice in chunk.get("choices") or []:
                        delta = (choice.get("delta") or {}).get("content")
                        if delta:
                            parts.append(delta)
                            yield TextDelta(delta)
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise RetryableLLMError(f"Groq stream failed: {e!r}", provider=self.name) from e
        text = "".join(parts)
        prompt = "".join(m.content for m in messages)
        yield StreamDone(
            LLMResult(
                text=text,
                provider=self.name,
                model=str(model),
                tokens_in=int(usage.get("prompt_tokens") or estimate_tokens(prompt)),
                tokens_out=int(usage.get("completion_tokens") or estimate_tokens(text)),
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
