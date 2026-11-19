"""The provider interface. Only the router and tests talk to providers directly."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

from app.llm.types import CallOptions, LLMResult, Message, StreamEvent


class LLMProvider(ABC):
    """A chat model behind one API. Implementations raise app.llm.errors classes only."""

    name: str
    model: str

    @abstractmethod
    async def complete(self, messages: Sequence[Message], options: CallOptions) -> LLMResult:
        """Return the whole reply. With `options.json_schema` the reply text must be JSON."""

    @abstractmethod
    def stream(
        self, messages: Sequence[Message], options: CallOptions
    ) -> AsyncIterator[StreamEvent]:
        """Yield TextDelta events, then exactly one StreamDone with the usage record."""

    async def aclose(self) -> None:  # noqa: B027 - optional hook, default no-op
        """Release network resources."""
