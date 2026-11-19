"""LLM router: the single entry point every feature uses to call a model (CLAUDE.md rule 1).

For each configured provider, in order (primary, then fallback):
- skip it while its circuit breaker is open (60 s after repeated failures);
- call it, retrying retryable errors (429 / 5xx / timeouts) with exponential backoff + jitter, up
  to `max_attempts` calls, honouring Retry-After when given;
- fatal errors (bad request, auth, unknown model) move straight to the next provider.
JSON mode validates the reply against a Pydantic model and re-asks once with the validation error
if it does not fit. Streaming retries only before the first token was sent: once text has reached
the user, a failure is reported instead of silently restarting the answer.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any

from pydantic import BaseModel, ValidationError

from app.llm.base import LLMProvider
from app.llm.errors import (
    AllProvidersFailedError,
    FatalLLMError,
    LLMError,
    LLMOutputError,
    RetryableLLMError,
)
from app.llm.pricing import estimate_cost
from app.llm.types import CallOptions, LLMResult, Message, StreamDone, StreamEvent, TextDelta

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class CircuitBreaker:
    """Opens after `threshold` consecutive failures and stays open for `cooldown_s`."""

    def __init__(self, threshold: int, cooldown_s: float, clock: Callable[[], float]) -> None:
        self.threshold = max(1, threshold)
        self.cooldown_s = cooldown_s
        self._clock = clock
        self.failures = 0
        self.open_until = 0.0

    @property
    def is_open(self) -> bool:
        return self._clock() < self.open_until

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = self._clock() + self.cooldown_s
            self.failures = 0


def parse_json_reply[M: BaseModel](text: str, schema: type[M]) -> M:
    """Validate a model reply against `schema`, tolerating a ```json fence around it."""
    match = _FENCE.match(text)
    return schema.model_validate_json(match.group(1) if match else text.strip())


def _repair_prompt(error: Exception) -> str:
    detail = str(error)
    if isinstance(error, ValidationError):
        detail = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or '(root)'}: {e['msg']}"
            for e in error.errors()[:5]
        )
    return (
        "Your previous reply was not valid JSON for the required schema "
        f"({detail[:400]}). Reply again with ONLY the corrected JSON object, no prose."
    )


class LLMRouter:
    def __init__(
        self,
        providers: Sequence[LLMProvider],
        *,
        max_attempts: int = 3,
        backoff_base_s: float = 0.5,
        backoff_max_s: float = 8.0,
        breaker_threshold: int = 3,
        breaker_cooldown_s: float = 60.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        rng: Callable[[], float] = random.random,
    ) -> None:
        if not providers:
            raise ValueError("at least one provider is required")
        self.providers = list(providers)
        self.max_attempts = max(1, max_attempts)
        self.backoff_base_s = backoff_base_s
        self.backoff_max_s = backoff_max_s
        self._sleep = sleep
        self._rng = rng
        self.breakers = {
            self._key(p): CircuitBreaker(breaker_threshold, breaker_cooldown_s, clock)
            for p in self.providers
        }

    @staticmethod
    def _key(p: LLMProvider) -> str:
        return f"{p.name}:{p.model}"

    def breaker(self, p: LLMProvider) -> CircuitBreaker:
        return self.breakers[self._key(p)]

    def backoff_s(self, attempt: int, retry_after_s: float | None = None) -> float:
        """Delay before retry number `attempt + 1`: exponential, capped, with jitter."""
        base = min(self.backoff_max_s, self.backoff_base_s * (2**attempt))
        delay = float(base * (0.5 + self._rng() / 2))
        if retry_after_s is not None:
            delay = max(delay, min(float(retry_after_s), self.backoff_max_s))
        return delay

    def status(self) -> list[dict[str, Any]]:
        return [
            {
                "provider": p.name,
                "model": p.model,
                "circuit_open": self.breaker(p).is_open,
                "consecutive_failures": self.breaker(p).failures,
            }
            for p in self.providers
        ]

    # ------------------------------------------------------------------ complete

    async def _call_with_retries(
        self,
        p: LLMProvider,
        messages: Sequence[Message],
        options: CallOptions,
        causes: list[LLMError],
    ) -> tuple[LLMResult | None, int]:
        """Up to max_attempts calls to one provider. Returns (result or None, calls made)."""
        breaker = self.breaker(p)
        calls = 0
        for attempt in range(self.max_attempts):
            calls += 1
            try:
                result = await p.complete(messages, options)
            except RetryableLLMError as e:
                breaker.record_failure()
                causes.append(e)
                if attempt + 1 < self.max_attempts and not breaker.is_open:
                    await self._sleep(self.backoff_s(attempt, e.retry_after_s))
                    continue
                return None, calls
            except FatalLLMError as e:
                breaker.record_failure()
                causes.append(e)
                return None, calls
            breaker.record_success()
            return result, calls
        return None, calls

    async def complete(
        self,
        messages: Sequence[Message],
        *,
        schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 900,
        pricing: dict[str, Any] | None = None,
    ) -> LLMResult:
        options = CallOptions(
            temperature=temperature,
            max_tokens=max_tokens,
            json_schema=schema.model_json_schema() if schema else None,
        )
        causes: list[LLMError] = []
        total_calls = 0
        for index, p in enumerate(self.providers):
            if self.breaker(p).is_open:
                causes.append(RetryableLLMError("circuit breaker open", provider=p.name))
                continue
            result, calls = await self._call_with_retries(p, messages, options, causes)
            total_calls += calls
            if result is None:
                continue
            if schema is not None:
                try:
                    result, extra = await self._validated(
                        p, messages, options, result, schema, causes
                    )
                except LLMOutputError as e:
                    causes.append(e)
                    total_calls += 1
                    continue
                total_calls += extra
            return result.with_(
                attempts=total_calls,
                fallback_used=index > 0,
                est_cost_usd=estimate_cost(
                    result.model, result.tokens_in, result.tokens_out, pricing
                ),
            )
        summary = "; ".join(f"{c.provider or '?'}: {c}" for c in causes[-4:])
        raise AllProvidersFailedError(f"all LLM providers failed ({summary})", causes=causes)

    async def _validated(
        self,
        p: LLMProvider,
        messages: Sequence[Message],
        options: CallOptions,
        result: LLMResult,
        schema: type[BaseModel],
        causes: list[LLMError],
    ) -> tuple[LLMResult, int]:
        """Validate JSON; on failure re-ask the same provider once. Returns (result, calls)."""
        try:
            return result.with_(data=parse_json_reply(result.text, schema)), 0
        except (ValidationError, ValueError) as first_error:
            repair = [
                *messages,
                Message("assistant", result.text),
                Message("user", _repair_prompt(first_error)),
            ]
            retry_causes: list[LLMError] = []
            second, calls = await self._call_with_retries(p, repair, options, retry_causes)
            causes.extend(retry_causes)
            if second is None:
                raise LLMOutputError(
                    "invalid JSON and the repair call failed", provider=p.name
                ) from first_error
            merged = second.with_(
                tokens_in=result.tokens_in + second.tokens_in,
                tokens_out=result.tokens_out + second.tokens_out,
                latency_ms=result.latency_ms + second.latency_ms,
            )
            try:
                return merged.with_(data=parse_json_reply(second.text, schema)), calls
            except (ValidationError, ValueError) as second_error:
                raise LLMOutputError(
                    f"reply is not valid JSON for {schema.__name__} after one repair",
                    provider=p.name,
                ) from second_error

    # ------------------------------------------------------------------ stream

    async def stream(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 900,
        pricing: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        options = CallOptions(temperature=temperature, max_tokens=max_tokens)
        causes: list[LLMError] = []
        total_calls = 0
        for index, p in enumerate(self.providers):
            breaker = self.breaker(p)
            if breaker.is_open:
                causes.append(RetryableLLMError("circuit breaker open", provider=p.name))
                continue
            for attempt in range(self.max_attempts):
                total_calls += 1
                sent_text = False
                try:
                    async for event in p.stream(messages, options):
                        if isinstance(event, StreamDone):
                            breaker.record_success()
                            r = event.result
                            yield StreamDone(
                                r.with_(
                                    attempts=total_calls,
                                    fallback_used=index > 0,
                                    est_cost_usd=estimate_cost(
                                        r.model, r.tokens_in, r.tokens_out, pricing
                                    ),
                                )
                            )
                            return
                        if isinstance(event, TextDelta) and event.text:
                            sent_text = True
                            yield event
                    raise RetryableLLMError(
                        "stream ended without a final usage record", provider=p.name
                    )
                except LLMError as e:
                    breaker.record_failure()
                    causes.append(e)
                    if sent_text:
                        raise  # never restart an answer the user is already reading
                    retryable = isinstance(e, RetryableLLMError)
                    if retryable and attempt + 1 < self.max_attempts and not breaker.is_open:
                        retry_after = e.retry_after_s if isinstance(e, RetryableLLMError) else None
                        await self._sleep(self.backoff_s(attempt, retry_after))
                        continue
                    break
        summary = "; ".join(f"{c.provider or '?'}: {c}" for c in causes[-4:])
        raise AllProvidersFailedError(f"all LLM providers failed ({summary})", causes=causes)


def dumps_schema(schema: type[BaseModel]) -> str:
    """Compact JSON Schema text, for prompts of providers without native schema support."""
    return json.dumps(schema.model_json_schema(), separators=(",", ":"))
