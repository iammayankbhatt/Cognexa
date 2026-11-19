"""Per-user sliding-window rate limiter (in memory).

Correct only with a single backend process, which is what Render Free runs (LIM-003). Moving to
several instances needs a shared store (Redis) instead.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable


class SlidingWindowLimiter:
    def __init__(self, window_s: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.window_s = window_s
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    def _trim(self, key: str, now: float) -> deque[float]:
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= self.window_s:
            hits.popleft()
        return hits

    async def acquire(self, key: str, limit: int) -> tuple[bool, float]:
        """Take a slot. Returns (allowed, seconds until a slot frees up when not allowed)."""
        async with self._lock:
            now = self._clock()
            hits = self._trim(key, now)
            if len(hits) >= max(0, limit):
                retry = self.window_s - (now - hits[0]) if hits else self.window_s
                return False, max(retry, 0.0)
            hits.append(now)
            return True, 0.0

    async def release(self, key: str) -> None:
        """Give back the most recent slot (the request was rejected later for another reason)."""
        async with self._lock:
            hits = self._hits.get(key)
            if hits:
                hits.pop()

    def reset(self) -> None:
        self._hits.clear()
