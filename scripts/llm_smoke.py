"""Smoke-test every configured LLM / embedding provider with one tiny real call each.

Calls each provider DIRECTLY (no fallback), so a broken primary is not hidden by a working fallback:
- primary, fallback and judge: a short completion, a JSON-mode completion, and a stream;
- embeddings: two texts, checking the vector size equals EMBEDDING_DIM.
Prints provider, model, latency and token counts. Never prints API keys. Exit code 1 if any check
fails. With the default fake providers it runs offline (useful to check the wiring).

Usage: uv run --project apps/api python scripts/llm_smoke.py [--only primary|fallback|judge|embedding]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import Awaitable, Callable

from pydantic import BaseModel

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.llm.embeddings import EmbeddingProviderUnavailableError, get_embedding_provider
from app.llm.errors import LLMError
from app.llm.registry import build_provider
from app.llm.router import parse_json_reply
from app.llm.types import CallOptions, Message, StreamDone, TextDelta


class Pong(BaseModel):
    answer: str
    number: int


PROMPT = [
    Message("system", "You are a connectivity test. Be extremely brief."),
    Message("user", "Reply with the single word: pong"),
]
JSON_PROMPT = [
    Message("system", "You are a connectivity test. Reply with JSON only."),
    Message("user", 'Return {"answer": "pong", "number": 7}'),
]


async def check(name: str, fn: Callable[[], Awaitable[str]]) -> bool:
    started = time.monotonic()
    try:
        detail = await fn()
    except (LLMError, EmbeddingProviderUnavailableError, ValueError) as e:
        print(f"  FAIL {name:<10} {type(e).__name__}: {str(e)[:200]}")
        return False
    print(f"  ok   {name:<10} {detail} ({int((time.monotonic() - started) * 1000)} ms)")
    return True


async def chat_checks(label: str, provider: LLMProvider) -> bool:
    print(f"{label}: {provider.name} / {provider.model}")

    async def complete() -> str:
        r = await provider.complete(PROMPT, CallOptions(temperature=0, max_tokens=10))
        return f"text={r.text.strip()[:40]!r} tokens={r.tokens_in}/{r.tokens_out}"

    async def json_mode() -> str:
        r = await provider.complete(
            JSON_PROMPT,
            CallOptions(temperature=0, max_tokens=40, json_schema=Pong.model_json_schema()),
        )
        try:
            parsed = parse_json_reply(r.text, Pong)
        except Exception as e:  # report the raw reply; the router would re-ask once
            raise ValueError(f"reply was not valid Pong JSON: {r.text[:120]!r}") from e
        return f"json={parsed.model_dump()}"

    async def stream() -> str:
        pieces, done = 0, None
        async for ev in provider.stream(PROMPT, CallOptions(temperature=0, max_tokens=10)):
            if isinstance(ev, TextDelta):
                pieces += 1
            elif isinstance(ev, StreamDone):
                done = ev.result
        if done is None:
            raise ValueError("stream ended without a usage record")
        return f"deltas={pieces} text={done.text.strip()[:40]!r} tokens={done.tokens_in}/{done.tokens_out}"

    results = [
        await check("complete", complete),
        await check("json", json_mode),
        await check("stream", stream),
    ]
    await provider.aclose()
    return all(results)


async def embedding_checks(settings: Settings) -> bool:
    print(f"embedding: {settings.embedding_provider} / {settings.embedding_model}")

    async def embed() -> str:
        provider = get_embedding_provider(settings)
        vectors = await provider.embed(["binary search tree", "call stack overflow"])
        sizes = {len(v) for v in vectors}
        if sizes != {settings.embedding_dim}:
            raise ValueError(f"vector sizes {sizes} != EMBEDDING_DIM={settings.embedding_dim}")
        return f"vectors=2 dim={settings.embedding_dim}"

    return await check("embed", embed)


async def run(only: str | None) -> int:
    settings = Settings()
    targets: list[tuple[str, str | None, str | None]] = [
        ("primary", settings.llm_primary_provider, settings.llm_primary_model),
        ("fallback", settings.llm_fallback_provider, settings.llm_fallback_model),
        ("judge", settings.llm_judge_provider, settings.llm_judge_model),
    ]
    ok = True
    for label, provider_id, model in targets:
        if only and only != label:
            continue
        if not provider_id or not model:
            print(f"{label}: not configured (skipped)")
            continue
        try:
            provider = build_provider(provider_id, model, settings)
        except LLMError as e:
            print(f"{label}: FAIL {e}")
            ok = False
            continue
        ok = await chat_checks(label, provider) and ok
    if not only or only == "embedding":
        ok = await embedding_checks(settings) and ok
    print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["primary", "fallback", "judge", "embedding"])
    return asyncio.run(run(parser.parse_args().only))


if __name__ == "__main__":
    sys.exit(main())
