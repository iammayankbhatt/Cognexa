"""Per-minute limits on expensive endpoints that do not call an LLM (Phase 13).

AI requests already pass the usage guard (quota + per-minute window). These limits protect the
database-heavy or public routes: exports, the dashboard aggregation, quiz creation, and the
public readiness and graph endpoints (keyed by client IP; uvicorn runs with --proxy-headers, so
behind Render this is the caller's address).

In memory, like the AI limiter: correct for the single free-tier instance (LIM-003).
"""

from __future__ import annotations

import datetime as dt
import time
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request

from app.auth.deps import CurrentUser, get_current_user
from app.core.errors import AppError
from app.usage.limiter import SlidingWindowLimiter

# requests per minute; tests may override app.state.route_limits
DEFAULT_LIMITS: dict[str, int] = {
    "health_deep": 30,  # public, pings both databases
    "public_graph": 60,  # public, cached
    "me_export": 5,
    "admin_export": 10,
    "dashboard": 60,
    "quiz_create": 20,
    "concept_search": 120,
}
PRUNE_EVERY_S = 300.0


class RouteLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.window = SlidingWindowLimiter(60.0, clock)
        self._clock = clock
        self._last_prune = clock()

    async def check(self, name: str, key: str, limit: int) -> None:
        now = self._clock()
        if now - self._last_prune >= PRUNE_EVERY_S:
            self.prune()
            self._last_prune = now
        allowed, retry_s = await self.window.acquire(f"{name}:{key}", limit)
        if not allowed:
            reset = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=retry_s)
            raise AppError(
                "RATE_LIMITED",
                f"Too many requests: at most {limit} per minute. Try again shortly.",
                429,
                details={"reset_at": reset.isoformat(), "retry_after_s": round(retry_s, 1)},
                headers={"Retry-After": str(max(1, int(retry_s + 0.999)))},
            )

    def prune(self) -> None:
        """Drop keys whose window is empty, so per-IP keys cannot grow without bound."""
        now = self._clock()
        hits = self.window._hits
        for key in [k for k, q in hits.items() if not q or now - q[-1] >= self.window.window_s]:
            del hits[key]


def _limiter(request: Request) -> tuple[RouteLimiter, dict[str, int]]:
    state = request.app.state
    if not hasattr(state, "route_limiter"):
        state.route_limiter = RouteLimiter()
    return state.route_limiter, getattr(state, "route_limits", DEFAULT_LIMITS)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def limit_by_ip(name: str) -> Callable[[Request], Awaitable[None]]:
    async def _dep(request: Request) -> None:
        limiter, limits = _limiter(request)
        await limiter.check(name, client_ip(request), limits[name])

    return _dep


def limit_by_user(name: str) -> Callable[..., Awaitable[None]]:
    async def _dep(
        request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]
    ) -> None:
        limiter, limits = _limiter(request)
        await limiter.check(name, str(user.id), limits[name])

    return _dep
