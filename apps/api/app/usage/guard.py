"""Usage guard: every AI request goes through it (CLAUDE.md rule 2).

Checks, in order: global daily cap → the user's daily AI requests → per-minute limit → maximum
input length. A request that passes is *reserved* atomically in Postgres before the model is called,
so parallel requests cannot exceed the daily limits. Usage is written to usage_daily and
global_usage_daily; a call that fails before producing an answer is refunded.

Use it as an async context manager inside an endpoint:

    async with guard.request(user, question_text) as ticket:
        result = await router.complete(...)
        await ticket.record(result)
"""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from app.auth.deps import CurrentUser
from app.core.errors import AppError
from app.db.repositories import DEFAULT_APP_SETTINGS, AppSettingsRepository
from app.db.session import Database
from app.llm.types import LLMResult
from app.usage.limiter import SlidingWindowLimiter
from app.usage.repository import UsageRepository


def utc_today(now: dt.datetime | None = None) -> dt.date:
    return (now or dt.datetime.now(dt.UTC)).date()


def next_utc_midnight(now: dt.datetime | None = None) -> dt.datetime:
    now = now or dt.datetime.now(dt.UTC)
    return dt.datetime.combine(now.date() + dt.timedelta(days=1), dt.time(), tzinfo=dt.UTC)


@dataclass(frozen=True)
class Limits:
    daily: int
    per_minute: int
    max_input_chars: int
    max_output_tokens: int
    global_cap: int

    def as_dict(self) -> dict[str, int]:
        return {
            "daily_ai_requests": self.daily,
            "per_minute": self.per_minute,
            "max_input_chars": self.max_input_chars,
            "max_output_tokens": self.max_output_tokens,
        }


async def load_limits(settings_repo: AppSettingsRepository, user: CurrentUser) -> Limits:
    stored = await settings_repo.get("quota.student") or {}
    base = {**DEFAULT_APP_SETTINGS["quota.student"], **stored}
    mult_map = (
        await settings_repo.get("quota.role_multipliers")
        or DEFAULT_APP_SETTINGS["quota.role_multipliers"]
    )
    cap = (
        await settings_repo.get("quota.global_daily_cap")
        or DEFAULT_APP_SETTINGS["quota.global_daily_cap"]
    )
    mult = int(mult_map.get(user.role, 1) or 1)
    daily = int(base["daily_ai_requests"]) * mult
    per_minute = int(base["per_minute"]) * mult
    override = user.profile.get("quota_override") or {}
    if isinstance(override, dict):
        if isinstance(override.get("daily_ai_requests"), int):
            daily = int(override["daily_ai_requests"])
        if isinstance(override.get("per_minute"), int):
            per_minute = int(override["per_minute"])
    return Limits(
        daily=daily,
        per_minute=per_minute,
        max_input_chars=int(base["max_input_chars"]),
        max_output_tokens=int(base["max_output_tokens"]),
        global_cap=int(cap.get("ai_requests", 0)),
    )


def _too_many(code: str, message: str, reset_at: dt.datetime, retry_after_s: float) -> AppError:
    return AppError(
        code,
        message,
        429,
        details={"reset_at": reset_at.isoformat(), "retry_after_s": round(retry_after_s, 1)},
        headers={"Retry-After": str(max(1, int(retry_after_s + 0.999)))},
    )


class _Rejected(Exception):
    def __init__(self, error: AppError) -> None:
        super().__init__(error.message)
        self.error = error


@dataclass
class Ticket:
    """An admitted AI request. Call `record` with the result (cache hits too: cached=True)."""

    guard: UsageGuard
    user: CurrentUser
    day: dt.date
    limits: Limits
    purpose: str = "tutor"
    recorded: bool = False

    async def record(self, result: LLMResult) -> None:
        """Log the call; add tokens and notional cost unless the answer came from the cache."""
        self.recorded = True
        async with self.guard.db.sessions()() as session, session.begin():
            if not result.cached and (result.tokens_in or result.tokens_out):
                await UsageRepository(session).add_tokens(
                    self.user.id, self.day, result.tokens_in, result.tokens_out, result.est_cost_usd
                )
            await UsageRepository(session).log_call(
                user_id=self.user.id,
                purpose=self.purpose,
                provider=result.provider,
                model=result.model,
                tokens_in=0 if result.cached else result.tokens_in,
                tokens_out=0 if result.cached else result.tokens_out,
                cost=0.0 if result.cached else result.est_cost_usd,
                latency_ms=result.latency_ms,
                cached=result.cached,
                fallback_used=result.fallback_used,
            )

    async def mark_cached(self, provider: str = "cache", model: str = "-") -> None:
        """The answer came from the cache: one request, no tokens."""
        await self.record(LLMResult("", provider, model, cached=True))


class UsageGuard:
    def __init__(
        self,
        db: Database,
        limiter: SlidingWindowLimiter | None = None,
        now: Callable[[], dt.datetime] | None = None,
    ) -> None:
        self.db = db
        self.limiter = limiter or SlidingWindowLimiter()
        self._now = now or (lambda: dt.datetime.now(dt.UTC))

    async def limits_for(self, user: CurrentUser) -> Limits:
        async with self.db.sessions()() as session:
            return await load_limits(AppSettingsRepository(session), user)

    async def admit(self, user: CurrentUser, input_text: str, purpose: str = "tutor") -> Ticket:
        now = self._now()
        day = now.date()
        midnight = next_utc_midnight(now)
        until_midnight = (midnight - now).total_seconds()
        async with self.db.sessions()() as session:
            limits = await load_limits(AppSettingsRepository(session), user)
            repo = UsageRepository(session)
            # Fast read-only checks give the right error code in the documented order.
            if await repo.global_today(day) >= limits.global_cap:
                raise _too_many(
                    "GLOBAL_CAP",
                    "Cognexa has reached today's AI limit for everyone. It resets at midnight UTC.",
                    midnight,
                    until_midnight,
                )
            if (await repo.user_today(user.id, day))["ai_requests"] >= limits.daily:
                raise _too_many(
                    "QUOTA_EXCEEDED",
                    f"You have used all {limits.daily} AI requests for today.",
                    midnight,
                    until_midnight,
                )
        key = str(user.id)
        allowed, retry_s = await self.limiter.acquire(key, limits.per_minute)
        if not allowed:
            raise _too_many(
                "RATE_LIMITED",
                f"Too many requests: at most {limits.per_minute} per minute.",
                now + dt.timedelta(seconds=retry_s),
                retry_s,
            )
        if len(input_text) > limits.max_input_chars:
            await self.limiter.release(key)
            raise AppError(
                "INPUT_TOO_LONG",
                f"Please keep your message under {limits.max_input_chars} characters.",
                413,
                details={"max_input_chars": limits.max_input_chars},
            )
        # Atomic reservation: both counters or neither (raising inside begin() rolls back).
        try:
            async with self.db.sessions()() as session, session.begin():
                repo = UsageRepository(session)
                if not await repo.reserve_global(day, limits.global_cap):
                    raise _Rejected(
                        _too_many(
                            "GLOBAL_CAP",
                            "Cognexa has reached today's AI limit for everyone. "
                            "It resets at midnight UTC.",
                            midnight,
                            until_midnight,
                        )
                    )
                if not await repo.reserve_user(user.id, day, limits.daily):
                    raise _Rejected(
                        _too_many(
                            "QUOTA_EXCEEDED",
                            f"You have used all {limits.daily} AI requests for today.",
                            midnight,
                            until_midnight,
                        )
                    )
        except _Rejected as rejected:
            await self.limiter.release(key)
            raise rejected.error from None
        return Ticket(self, user, day, limits, purpose)

    async def refund(self, ticket: Ticket) -> None:
        async with self.db.sessions()() as session, session.begin():
            await UsageRepository(session).refund(ticket.user.id, ticket.day)

    @asynccontextmanager
    async def request(
        self, user: CurrentUser, input_text: str, purpose: str = "tutor"
    ) -> AsyncIterator[Ticket]:
        ticket = await self.admit(user, input_text, purpose)
        try:
            yield ticket
        except BaseException:
            if not ticket.recorded:
                await self.refund(ticket)  # the user got nothing: do not charge them
            raise

    async def usage_summary(self, user: CurrentUser, days: int = 30) -> dict[str, Any]:
        now = self._now()
        day = now.date()
        async with self.db.sessions()() as session:
            limits = await load_limits(AppSettingsRepository(session), user)
            repo = UsageRepository(session)
            today = await repo.user_today(user.id, day)
            history = await repo.history(user.id, day - dt.timedelta(days=days - 1))
        return {
            "today": {
                "date": day,
                **today,
                "remaining": max(limits.daily - today["ai_requests"], 0),
                "resets_at": next_utc_midnight(now),
            },
            "limits": limits.as_dict(),
            "history": history,
        }
