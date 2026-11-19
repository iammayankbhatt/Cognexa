"""Usage counters in Postgres: atomic reservations and token/cost metering.

A request is *reserved* before the model is called: one statement per table increments the
counter only while it is below the limit (INSERT ... ON CONFLICT DO UPDATE ... WHERE count < limit).
Both reservations run in one transaction, so parallel requests can never push a user or the global
counter past its limit. Tokens and cost are added after the call; failed calls are refunded.

Every transaction touches the global row before the user row, so concurrent requests always take
row locks in the same order and cannot deadlock (BUG-019).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import global_usage_daily, llm_calls, usage_daily


class UsageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def global_today(self, day: dt.date) -> int:
        value = await self._s.scalar(
            select(global_usage_daily.c.ai_requests).where(global_usage_daily.c.date == day)
        )
        return int(value or 0)

    async def user_today(self, user_id: uuid.UUID, day: dt.date) -> dict[str, Any]:
        row = (
            await self._s.execute(
                select(
                    usage_daily.c.ai_requests,
                    usage_daily.c.tokens_in,
                    usage_daily.c.tokens_out,
                    usage_daily.c.est_cost_usd,
                ).where(usage_daily.c.user_id == user_id, usage_daily.c.date == day)
            )
        ).first()
        if row is None:
            return {"ai_requests": 0, "tokens_in": 0, "tokens_out": 0, "est_cost_usd": 0.0}
        return {
            "ai_requests": int(row[0]),
            "tokens_in": int(row[1]),
            "tokens_out": int(row[2]),
            "est_cost_usd": float(row[3]),
        }

    async def reserve_global(self, day: dt.date, cap: int) -> bool:
        base = insert(global_usage_daily).values(date=day, ai_requests=1)
        stmt = base.on_conflict_do_update(
            index_elements=[global_usage_daily.c.date],
            set_={"ai_requests": global_usage_daily.c.ai_requests + 1},
            where=global_usage_daily.c.ai_requests < cap,
        ).returning(global_usage_daily.c.ai_requests)
        if cap <= 0:
            return False
        return (await self._s.execute(stmt)).first() is not None

    async def reserve_user(self, user_id: uuid.UUID, day: dt.date, quota: int) -> bool:
        if quota <= 0:
            return False
        base = insert(usage_daily).values(user_id=user_id, date=day, ai_requests=1)
        stmt = base.on_conflict_do_update(
            index_elements=[usage_daily.c.user_id, usage_daily.c.date],
            set_={"ai_requests": usage_daily.c.ai_requests + 1},
            where=usage_daily.c.ai_requests < quota,
        ).returning(usage_daily.c.ai_requests)
        return (await self._s.execute(stmt)).first() is not None

    async def refund(self, user_id: uuid.UUID, day: dt.date, *, global_too: bool = True) -> None:
        # Lock order everywhere: global row first, then the user row (avoids deadlocks, BUG-019).
        if global_too:
            await self._s.execute(
                update(global_usage_daily)
                .where(global_usage_daily.c.date == day)
                .values(ai_requests=func.greatest(global_usage_daily.c.ai_requests - 1, 0))
            )
        await self._s.execute(
            update(usage_daily)
            .where(usage_daily.c.user_id == user_id, usage_daily.c.date == day)
            .values(ai_requests=func.greatest(usage_daily.c.ai_requests - 1, 0))
        )

    async def add_tokens(
        self, user_id: uuid.UUID, day: dt.date, tokens_in: int, tokens_out: int, cost: float
    ) -> None:
        # Same lock order as reserve/refund: global row first, then the user row (BUG-019).
        g = insert(global_usage_daily).values(
            date=day, ai_requests=0, tokens_in=tokens_in, tokens_out=tokens_out
        )
        await self._s.execute(
            g.on_conflict_do_update(
                index_elements=[global_usage_daily.c.date],
                set_={
                    "tokens_in": global_usage_daily.c.tokens_in + tokens_in,
                    "tokens_out": global_usage_daily.c.tokens_out + tokens_out,
                },
            )
        )
        stmt = insert(usage_daily).values(
            user_id=user_id,
            date=day,
            ai_requests=0,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            est_cost_usd=cost,
        )
        await self._s.execute(
            stmt.on_conflict_do_update(
                index_elements=[usage_daily.c.user_id, usage_daily.c.date],
                set_={
                    "tokens_in": usage_daily.c.tokens_in + tokens_in,
                    "tokens_out": usage_daily.c.tokens_out + tokens_out,
                    "est_cost_usd": usage_daily.c.est_cost_usd + cost,
                },
            )
        )

    async def log_call(
        self,
        *,
        user_id: uuid.UUID | None,
        purpose: str,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        latency_ms: int,
        cached: bool,
        fallback_used: bool,
    ) -> None:
        await self._s.execute(
            llm_calls.insert().values(
                user_id=user_id,
                purpose=purpose[:40],
                provider=provider[:60],
                model=model[:120],
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                est_cost_usd=cost,
                latency_ms=max(latency_ms, 0),
                cached=cached,
                fallback_used=fallback_used,
            )
        )

    async def history(self, user_id: uuid.UUID, since: dt.date) -> list[dict[str, Any]]:
        rows = await self._s.execute(
            select(
                usage_daily.c.date,
                usage_daily.c.ai_requests,
                usage_daily.c.tokens_in,
                usage_daily.c.tokens_out,
                usage_daily.c.est_cost_usd,
            )
            .where(usage_daily.c.user_id == user_id, usage_daily.c.date >= since)
            .order_by(usage_daily.c.date)
        )
        return [
            {
                "date": r[0],
                "ai_requests": int(r[1]),
                "tokens_in": int(r[2]),
                "tokens_out": int(r[3]),
                "est_cost_usd": float(r[4]),
            }
            for r in rows
        ]
