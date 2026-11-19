"""Builds providers and routers from settings. Model ids come only from env (CLAUDE.md §3)."""

from __future__ import annotations

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.errors import ProviderUnavailableError
from app.llm.fake import FakeProvider
from app.llm.router import LLMRouter

PROVIDER_IDS = ("fake", "groq", "gemini")


def build_provider(provider_id: str, model: str, settings: Settings) -> LLMProvider:
    """Construct a provider. A missing API key does not fail here: the provider raises
    ProviderUnavailableError when called, so the router can fall back and the app still starts."""
    if provider_id == "fake":
        return FakeProvider(model=model)
    if provider_id == "groq":
        from app.llm.groq import GroqProvider

        return GroqProvider(
            model, settings.groq_api_key, settings.groq_base_url, settings.llm_timeout_s
        )
    if provider_id == "gemini":
        from app.llm.gemini import GeminiProvider

        return GeminiProvider(
            model,
            settings.gemini_api_key,
            settings.llm_timeout_s,
            api_version=settings.gemini_api_version,
        )
    raise ProviderUnavailableError(
        f"unknown LLM provider '{provider_id}' (expected one of {', '.join(PROVIDER_IDS)})"
    )


def _router(providers: list[LLMProvider], settings: Settings) -> LLMRouter:
    return LLMRouter(
        providers,
        max_attempts=settings.llm_max_attempts,
        backoff_base_s=settings.llm_backoff_base_s,
        backoff_max_s=settings.llm_backoff_max_s,
        breaker_threshold=settings.llm_breaker_threshold,
        breaker_cooldown_s=settings.llm_breaker_cooldown_s,
    )


def build_router(settings: Settings) -> LLMRouter:
    """Primary + fallback router used by the tutor and the classifier."""
    providers = [
        build_provider(settings.llm_primary_provider, settings.llm_primary_model, settings)
    ]
    fb_id, fb_model = settings.llm_fallback_provider, settings.llm_fallback_model
    if (
        fb_id
        and fb_model
        and (fb_id, fb_model)
        != (
            settings.llm_primary_provider,
            settings.llm_primary_model,
        )
    ):
        providers.append(build_provider(fb_id, fb_model, settings))
    return _router(providers, settings)


def build_judge_router(settings: Settings) -> LLMRouter:
    """Single-provider router for grading / evaluation (LLM_JUDGE_*)."""
    return _router(
        [build_provider(settings.llm_judge_provider, settings.llm_judge_model, settings)], settings
    )
