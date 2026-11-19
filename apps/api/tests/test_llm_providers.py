"""Groq and Gemini providers against mocked HTTP (no network), plus the provider registry."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from app.core.config import Settings
from app.llm.errors import FatalLLMError, ProviderUnavailableError, RetryableLLMError
from app.llm.fake import FakeProvider
from app.llm.gemini import GeminiEmbeddingProvider, GeminiProvider
from app.llm.groq import GroqProvider
from app.llm.registry import build_judge_router, build_provider, build_router
from app.llm.types import CallOptions, Message, StreamDone, TextDelta

MSGS = [Message("system", "be brief"), Message("user", "hi"), Message("assistant", "hello"),
        Message("user", "what is a heap?")]  # fmt: skip


def mock(handler: Callable[[httpx.Request], httpx.Response]) -> tuple[httpx.AsyncClient, list]:  # type: ignore[type-arg]
    seen: list[httpx.Request] = []

    def wrapped(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return handler(req)

    return httpx.AsyncClient(transport=httpx.MockTransport(wrapped)), seen


async def collect(gen) -> tuple[str, StreamDone]:  # type: ignore[no-untyped-def]
    text, done = "", None
    async for ev in gen:
        if isinstance(ev, TextDelta):
            text += ev.text
        elif isinstance(ev, StreamDone):
            done = ev
    assert done is not None
    return text, done


# ---------------------------------------------------------------- Groq


def groq(handler: Callable[[httpx.Request], httpx.Response], key: str | None = "gk"):  # type: ignore[no-untyped-def]
    client, seen = mock(handler)
    return GroqProvider("groq-model", key, "https://groq.test/openai/v1", client=client), seen


async def test_groq_complete_sends_openai_payload_and_reads_usage() -> None:
    body = {
        "model": "groq-model",
        "choices": [{"message": {"role": "assistant", "content": "A heap is a tree."}}],
        "usage": {"prompt_tokens": 21, "completion_tokens": 6},
    }
    p, seen = groq(lambda r: httpx.Response(200, json=body))
    res = await p.complete(MSGS, CallOptions(temperature=0.1, max_tokens=50))
    assert (res.text, res.tokens_in, res.tokens_out, res.provider) == (
        "A heap is a tree.",
        21,
        6,
        "groq",
    )
    req = seen[0]
    assert str(req.url) == "https://groq.test/openai/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer gk"
    sent = json.loads(req.content)
    assert sent["model"] == "groq-model" and sent["max_completion_tokens"] == 50
    assert [m["role"] for m in sent["messages"]] == ["system", "user", "assistant", "user"]
    assert "response_format" not in sent and "stream" not in sent


async def test_groq_json_mode_adds_response_format_and_schema_prompt() -> None:
    body = {"choices": [{"message": {"content": "{}"}}]}
    p, seen = groq(lambda r: httpx.Response(200, json=body))
    res = await p.complete(MSGS, CallOptions(json_schema={"type": "object", "title": "Pick"}))
    sent = json.loads(seen[0].content)
    assert sent["response_format"] == {"type": "json_object"}
    assert '"title":"Pick"' in sent["messages"][0]["content"]
    assert res.tokens_in > 0 and res.tokens_out > 0  # estimated when usage is missing


@pytest.mark.parametrize(
    ("status", "headers", "kind", "retry_after"),
    [
        (429, {"retry-after": "7"}, RetryableLLMError, 7.0),
        (503, {}, RetryableLLMError, None),
        (401, {}, FatalLLMError, None),
        (400, {}, FatalLLMError, None),
    ],
)
async def test_groq_maps_http_errors(status, headers, kind, retry_after) -> None:  # type: ignore[no-untyped-def]
    p, _ = groq(
        lambda r: httpx.Response(status, headers=headers, json={"error": {"message": "nope"}})
    )
    with pytest.raises(kind) as info:
        await p.complete(MSGS, CallOptions())
    assert info.value.status == status and "nope" in str(info.value)
    if retry_after is not None:
        assert info.value.retry_after_s == retry_after


async def test_groq_timeout_is_retryable_and_missing_key_is_unavailable() -> None:
    def boom(r: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=r)

    p, _ = groq(boom)
    with pytest.raises(RetryableLLMError):
        await p.complete(MSGS, CallOptions())
    p2, seen = groq(lambda r: httpx.Response(200, json={}), key=None)
    with pytest.raises(ProviderUnavailableError):
        await p2.complete(MSGS, CallOptions())
    assert seen == []  # never sent a request without a key


async def test_groq_stream_parses_sse_and_x_groq_usage() -> None:
    chunks = [
        {"choices": [{"delta": {"role": "assistant"}}]},
        {"choices": [{"delta": {"content": "A heap "}}]},
        {"choices": [{"delta": {"content": "is a tree."}}]},
        {"choices": [], "x_groq": {"usage": {"prompt_tokens": 30, "completion_tokens": 5}}},
    ]
    sse = "".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n"
    p, seen = groq(
        lambda r: httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
    )
    text, done = await collect(p.stream(MSGS, CallOptions()))
    assert text == "A heap is a tree." == done.result.text
    assert (done.result.tokens_in, done.result.tokens_out) == (30, 5)
    assert json.loads(seen[0].content)["stream"] is True


async def test_groq_stream_error_status_raises_before_any_text() -> None:
    p, _ = groq(lambda r: httpx.Response(429, json={"error": {"message": "slow down"}}))
    with pytest.raises(RetryableLLMError):
        await collect(p.stream(MSGS, CallOptions()))


# ---------------------------------------------------------------- Gemini


def gemini_body(text: str, tin: int = 11, tout: int = 3) -> dict:  # type: ignore[type-arg]
    return {
        "candidates": [
            {"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": "STOP"}
        ],
        "usageMetadata": {"promptTokenCount": tin, "candidatesTokenCount": tout},
    }


async def test_gemini_complete_maps_roles_system_and_json_config() -> None:
    client, seen = mock(lambda r: httpx.Response(200, json=gemini_body("A heap is a tree.")))
    p = GeminiProvider("gem-model", "k", http_client=client)
    res = await p.complete(MSGS, CallOptions(json_schema={"type": "object"}, max_tokens=64))
    assert (res.text, res.tokens_in, res.tokens_out, res.provider) == (
        "A heap is a tree.",
        11,
        3,
        "gemini",
    )
    req = seen[0]
    assert req.url.path.endswith("/models/gem-model:generateContent")
    assert req.headers["x-goog-api-key"] == "k"
    sent = json.loads(req.content)
    assert [c["role"] for c in sent["contents"]] == ["user", "model", "user"]
    assert sent["systemInstruction"]["parts"][0]["text"] == "be brief"
    cfg = sent["generationConfig"]
    assert cfg["maxOutputTokens"] == 64 and cfg["responseMimeType"] == "application/json"
    assert cfg["responseJsonSchema"] == {"type": "object"}


async def test_gemini_api_version_override_changes_the_url() -> None:
    client, seen = mock(lambda r: httpx.Response(200, json=gemini_body("ok")))
    await GeminiProvider("m", "k", http_client=client, api_version="v1beta").complete(
        MSGS, CallOptions()
    )
    assert seen[0].url.path.startswith("/v1beta/")


@pytest.mark.parametrize(("status", "kind"), [(429, RetryableLLMError), (500, RetryableLLMError),
                                              (400, FatalLLMError), (403, FatalLLMError)])  # fmt: skip
async def test_gemini_maps_http_errors(status, kind) -> None:  # type: ignore[no-untyped-def]
    err = {"error": {"code": status, "message": "quota or bad", "status": "X"}}
    client, _ = mock(lambda r: httpx.Response(status, json=err))
    with pytest.raises(kind) as info:
        await GeminiProvider("m", "k", http_client=client).complete(MSGS, CallOptions())
    assert info.value.status == status


async def test_gemini_missing_key_is_unavailable() -> None:
    with pytest.raises(ProviderUnavailableError):
        await GeminiProvider("m", None).complete(MSGS, CallOptions())


async def test_gemini_stream_yields_chunks_and_final_usage() -> None:
    c1 = {"candidates": [{"content": {"role": "model", "parts": [{"text": "A heap "}]}}]}
    c2 = gemini_body("is a tree.", 40, 7)
    sse = f"data: {json.dumps(c1)}\r\n\r\ndata: {json.dumps(c2)}\r\n\r\n"
    client, seen = mock(
        lambda r: httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})
    )
    text, done = await collect(
        GeminiProvider("m", "k", http_client=client).stream(MSGS, CallOptions())
    )
    assert text == "A heap is a tree." and (done.result.tokens_in, done.result.tokens_out) == (
        40,
        7,
    )
    assert seen[0].url.path.endswith(":streamGenerateContent")


async def test_gemini_embeddings_batch_normalise_and_check_dim() -> None:
    def handler(r: httpx.Request) -> httpx.Response:
        n = len(json.loads(r.content)["requests"])
        return httpx.Response(200, json={"embeddings": [{"values": [3.0, 4.0]}] * n})

    client, seen = mock(handler)
    emb = GeminiEmbeddingProvider("emb", 2, "k", http_client=client)
    vectors = await emb.embed([f"t{i}" for i in range(150)])
    assert len(vectors) == 150 and vectors[0] == pytest.approx([0.6, 0.8])
    assert [len(json.loads(r.content)["requests"]) for r in seen] == [100, 50]
    first = json.loads(seen[0].content)["requests"][0]
    assert first["taskType"] == "RETRIEVAL_DOCUMENT" and first["outputDimensionality"] == 2
    query = await emb.for_queries().embed(["q"])
    assert len(query) == 1 and json.loads(seen[-1].content)["requests"][0]["taskType"] == (
        "RETRIEVAL_QUERY"
    )

    bad = GeminiEmbeddingProvider("emb", 3, "k", http_client=client)  # API returns 2 dims
    with pytest.raises(FatalLLMError, match="EMBEDDING_DIM=3"):
        await bad.embed(["x"])


# ---------------------------------------------------------------- registry


def test_registry_builds_configured_providers() -> None:
    s = Settings(
        _env_file=None,
        llm_primary_provider="groq",
        llm_primary_model="primary-model",
        llm_fallback_provider="gemini",
        llm_fallback_model="fallback-model",
        llm_judge_provider="fake",
        llm_judge_model="judge",
        groq_api_key=None,
        gemini_api_key=None,
    )
    r = build_router(s)
    assert [(p.name, p.model) for p in r.providers] == [
        ("groq", "primary-model"),
        ("gemini", "fallback-model"),
    ]
    assert [(p.name, p.model) for p in build_judge_router(s).providers] == [("fake", "judge")]


def test_registry_skips_duplicate_fallback_and_rejects_unknown() -> None:
    s = Settings(_env_file=None, llm_primary_provider="fake", llm_primary_model="m",
                 llm_fallback_provider="fake", llm_fallback_model="m")  # fmt: skip
    r = build_router(s)
    assert len(r.providers) == 1 and isinstance(r.providers[0], FakeProvider)
    s2 = Settings(_env_file=None, llm_fallback_provider="", llm_fallback_model="")
    assert len(build_router(s2).providers) == 1  # blank fallback = none
    with pytest.raises(ProviderUnavailableError, match="unknown LLM provider"):
        build_provider("openai", "x", s)
