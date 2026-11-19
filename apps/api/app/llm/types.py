"""Value types shared by every LLM provider and the router."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class LLMResult:
    """One completed model call (or a cache hit, then `cached` is True and tokens are 0)."""

    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    data: Any = None  # parsed and validated JSON when a schema was requested
    est_cost_usd: float = 0.0
    cached: bool = False
    attempts: int = 1  # provider calls made, including retries, repairs and fallback
    fallback_used: bool = False

    def with_(self, **changes: Any) -> LLMResult:
        return replace(self, **changes)


@dataclass(frozen=True)
class TextDelta:
    """A piece of streamed text."""

    text: str


@dataclass(frozen=True)
class StreamDone:
    """Final stream event: the whole text plus usage (same shape as a non-streamed call)."""

    result: LLMResult


StreamEvent = TextDelta | StreamDone


@dataclass
class CallOptions:
    temperature: float = 0.2
    max_tokens: int = 900
    json_schema: dict[str, Any] | None = None  # JSON Schema the reply must follow
    extra: dict[str, Any] = field(default_factory=dict)


def estimate_tokens(text: str) -> int:
    """Rough token count (about 4 characters per token) for providers that report no usage."""
    return max(1, (len(text) + 3) // 4) if text else 0
