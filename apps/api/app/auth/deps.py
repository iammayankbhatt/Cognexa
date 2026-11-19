"""FastAPI dependencies: the signed-in user and role checks.

The role is NOT read from the token (Supabase tokens only say "authenticated"); it comes from
public.profiles and is cached briefly per user so every request does not hit the database.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwks import JwksCache
from app.auth.tokens import AuthUnavailableError, TokenError, verify_token
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.profiles import ProfileRepository
from app.db.session import get_session

ROLE_RANK = {"student": 0, "reviewer": 1, "admin": 2}


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None
    role: str
    profile: dict[str, Any]


class ProfileCache:
    """Tiny in-process TTL cache (one backend instance on Render free; see LIM-003)."""

    def __init__(self, ttl_s: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_s
        self._clock = clock
        self._items: dict[uuid.UUID, tuple[float, dict[str, Any]]] = {}

    def get(self, user_id: uuid.UUID) -> dict[str, Any] | None:
        hit = self._items.get(user_id)
        if hit and self._clock() - hit[0] < self._ttl:
            return hit[1]
        self._items.pop(user_id, None)
        return None

    def put(self, user_id: uuid.UUID, profile: dict[str, Any]) -> None:
        self._items[user_id] = (self._clock(), profile)

    def invalidate(self, user_id: uuid.UUID) -> None:
        self._items.pop(user_id, None)


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AppError("unauthorized", "Sign in to continue.", 401)
    return token.strip()


async def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUser:
    token = _bearer(request)
    jwks: JwksCache | None = getattr(request.app.state, "jwks", None)
    try:
        claims = await verify_token(token, settings, jwks)
    except TokenError as exc:
        raise AppError("unauthorized", "Your session is invalid or has expired.", 401) from exc
    except AuthUnavailableError as exc:
        raise AppError("auth_unavailable", "Sign-in is temporarily unavailable.", 503) from exc

    cache: ProfileCache = request.app.state.profile_cache
    profile = cache.get(claims.user_id)
    if profile is None:
        profile = await ProfileRepository(session).ensure(claims.user_id)
        if profile is None:
            raise AppError("unauthorized", "This account no longer exists.", 401)
        cache.put(claims.user_id, profile)
    return CurrentUser(
        id=claims.user_id, email=claims.email, role=str(profile["role"]), profile=profile
    )


def require_role(minimum: str) -> Callable[..., Awaitable[CurrentUser]]:
    """Dependency factory: allow roles at or above `minimum` (student < reviewer < admin)."""
    if minimum not in ROLE_RANK:
        raise ValueError(f"unknown role {minimum!r}")

    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if ROLE_RANK.get(user.role, -1) < ROLE_RANK[minimum]:
            raise AppError("forbidden", "You do not have permission to do that.", 403)
        return user

    return _check
