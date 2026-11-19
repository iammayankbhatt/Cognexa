"""Async JWKS cache for verifying Supabase access tokens signed with asymmetric keys.

Keys are fetched from the project's `/auth/v1/.well-known/jwks.json`, cached for `ttl_s`, and
refetched early (at most once per `min_refetch_s`) when a token names an unknown `kid`, which is
what happens right after a signing-key rotation.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from jwt import PyJWK
from jwt.exceptions import PyJWKError

Fetcher = Callable[[str], Awaitable[dict[str, Any]]]


class JwksUnavailableError(RuntimeError):
    pass


async def http_fetch(url: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


class JwksCache:
    def __init__(
        self,
        url: str,
        *,
        ttl_s: float = 600,
        min_refetch_s: float = 30,
        fetcher: Fetcher = http_fetch,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.url = url
        self._ttl = ttl_s
        self._min_refetch = min_refetch_s
        self._fetch = fetcher
        self._clock = clock
        self._keys: dict[str, PyJWK] = {}
        self._fetched_at: float | None = None
        self._lock = asyncio.Lock()

    def _fresh(self) -> bool:
        return self._fetched_at is not None and self._clock() - self._fetched_at < self._ttl

    async def _refresh(self) -> None:
        try:
            doc = await self._fetch(self.url)
        except Exception as exc:  # network errors, bad JSON, HTTP errors
            raise JwksUnavailableError(f"could not fetch JWKS: {type(exc).__name__}") from exc
        keys: dict[str, PyJWK] = {}
        for jwk in doc.get("keys", []):
            kid = jwk.get("kid")
            if not kid or jwk.get("use", "sig") != "sig":
                continue
            try:
                keys[kid] = PyJWK(jwk)
            except PyJWKError:
                continue  # unsupported key type: skip rather than fail every request
        self._keys = keys
        self._fetched_at = self._clock()

    async def get_key(self, kid: str) -> PyJWK | None:
        async with self._lock:
            if not self._fresh():
                await self._refresh()
            elif (
                kid not in self._keys
                and self._fetched_at is not None
                and self._clock() - self._fetched_at >= self._min_refetch
            ):
                await self._refresh()  # possibly a newly rotated key
            return self._keys.get(kid)
