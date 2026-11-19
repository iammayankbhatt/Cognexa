"""Runtime feature flags: env defaults (AGENTIC_MODE, STUDY_MODE) overridden by app_settings."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.repositories import DEFAULT_APP_SETTINGS, AppSettingsRepository

FLAG_NAMES = ("AGENTIC_MODE", "STUDY_MODE", "PLAIN_RAG_VISIBLE_TO_STUDENTS")


def env_flags(settings: Settings) -> dict[str, bool]:
    return {
        **DEFAULT_APP_SETTINGS["features"],
        "AGENTIC_MODE": settings.agentic_mode,
        "STUDY_MODE": settings.study_mode,
    }


async def get_flags(session: AsyncSession, settings: Settings) -> dict[str, bool]:
    stored: dict[str, Any] = await AppSettingsRepository(session).get("features") or {}
    merged = env_flags(settings)
    for name in FLAG_NAMES:
        if isinstance(stored.get(name), bool):
            merged[name] = stored[name]
    return merged
