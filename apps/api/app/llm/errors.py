"""Errors raised by the LLM layer. The router decides what to do based on the class."""

from __future__ import annotations


class LLMError(Exception):
    """Base class. `provider` names the provider that failed (if any)."""

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class RetryableLLMError(LLMError):
    """Rate limit (429), server error (5xx), timeout or connection problem: worth retrying."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status: int | None = None,
        retry_after_s: float | None = None,
    ) -> None:
        super().__init__(message, provider=provider)
        self.status = status
        self.retry_after_s = retry_after_s


class FatalLLMError(LLMError):
    """Bad request, auth failure, unknown model: retrying the same provider will not help."""

    def __init__(self, message: str, *, provider: str | None = None, status: int | None = None):
        super().__init__(message, provider=provider)
        self.status = status


class ProviderUnavailableError(FatalLLMError):
    """The provider is not configured (missing API key or unknown provider id)."""


class LLMOutputError(LLMError):
    """The model's reply could not be used (invalid JSON after one repair, or blocked output)."""


class AllProvidersFailedError(LLMError):
    """Every configured provider failed or was skipped by its circuit breaker."""

    def __init__(self, message: str, *, causes: list[LLMError]) -> None:
        super().__init__(message)
        self.causes = causes
