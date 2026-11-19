"""LLM layer: FakeProvider, pricing and the router (fallback, backoff, breaker, JSON repair)."""

from __future__ import annotations

import json

import pytest
from pydantic import BaseModel, Field

from app.llm.errors import (
    AllProvidersFailedError,
    FatalLLMError,
    RetryableLLMError,
)
from app.llm.fake import FailMidStream, FakeProvider, example_from_schema, grounded_answer
from app.llm.pricing import estimate_cost
from app.llm.router import CircuitBreaker, LLMRouter, parse_json_reply
from app.llm.types import Message, StreamDone, TextDelta

USER = [Message("user", "What is a stack?")]


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class Sleeper:
    def __init__(self, clock: Clock | None = None) -> None:
        self.delays: list[float] = []
        self.clock = clock

    async def __call__(self, s: float) -> None:
        self.delays.append(s)
        if self.clock:
            self.clock.t += s


def router(*providers: FakeProvider, **kw: object) -> tuple[LLMRouter, Sleeper, Clock]:
    clock = Clock()
    sleeper = Sleeper(clock)
    r = LLMRouter(
        providers,
        sleep=sleeper,
        clock=clock,
        rng=lambda: 0.5,
        **kw,  # type: ignore[arg-type]
    )
    return r, sleeper, clock


def rate_limited(retry_after: float | None = None) -> RetryableLLMError:
    return RetryableLLMError("429", status=429, retry_after_s=retry_after)


# ---------------------------------------------------------------- fake provider + pricing


async def test_fake_answers_from_context_deterministically() -> None:
    msgs = [
        Message("system", "Answer only from <context>."),
        Message(
            "user",
            "<context>## Stack\n\nA stack is LIFO: the last item pushed is popped first.\n\n"
            "Push and pop are O(1).</context>\n<student_question>what is a stack</student_question>",
        ),
    ]
    a = await FakeProvider().complete(msgs, _opts())
    b = await FakeProvider().complete(msgs, _opts())
    assert a.text == b.text
    assert "LIFO" in a.text and "what is a stack" in a.text and "## Stack" not in a.text
    assert a.tokens_in > 0 and a.tokens_out > 0 and a.provider == "fake"


def test_fake_without_context_says_so() -> None:
    text = grounded_answer([Message("user", "<student_question>hi</student_question>")])
    assert "none were provided" in text and '"hi"' in text


class Pick(BaseModel):
    concept_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0.1)
    mode: str = Field(default="graphrag")
    off_topic: bool


def test_example_from_schema_is_valid() -> None:
    value = example_from_schema(Pick.model_json_schema())
    Pick.model_validate(value)  # raises if invalid


async def test_fake_script_and_json_default() -> None:
    fake = FakeProvider(script=["first", RetryableLLMError("boom")])
    assert (await fake.complete(USER, _opts())).text == "first"
    with pytest.raises(RetryableLLMError):
        await fake.complete(USER, _opts())
    reply = await fake.complete(USER, _opts(json_schema=Pick.model_json_schema()))
    Pick.model_validate_json(reply.text)
    assert len(fake.calls) == 3


def test_estimate_cost_uses_model_rate_then_default() -> None:
    pricing = {
        "default": {"input_per_1m": 1.0, "output_per_1m": 2.0},
        "models": {"cheap": {"input_per_1m": 0.1, "output_per_1m": 0.2}},
    }
    assert estimate_cost("cheap", 1_000_000, 1_000_000, pricing) == pytest.approx(0.3)
    assert estimate_cost("other", 500_000, 0, pricing) == pytest.approx(0.5)
    assert estimate_cost("x", 10, 10, {"default": {"input_per_1m": "bad"}}) == 0.0


# ---------------------------------------------------------------- complete


async def test_success_on_primary_reports_cost_and_attempts() -> None:
    r, sleeper, _ = router(FakeProvider(script=["ok"]))
    res = await r.complete(USER)
    assert (res.text, res.attempts, res.fallback_used) == ("ok", 1, False)
    assert res.est_cost_usd > 0 and sleeper.delays == []


async def test_retries_with_exponential_backoff_then_succeeds() -> None:
    primary = FakeProvider(script=[rate_limited(), rate_limited(), "third time"])
    r, sleeper, _ = router(primary, backoff_base_s=0.5, breaker_threshold=10)
    res = await r.complete(USER)
    assert res.text == "third time" and res.attempts == 3
    assert sleeper.delays == [pytest.approx(0.375), pytest.approx(0.75)]  # base*2^n*(0.5+0.25)


async def test_retry_after_is_honoured_but_capped() -> None:
    primary = FakeProvider(script=[rate_limited(retry_after=5), rate_limited(retry_after=99), "ok"])
    r, sleeper, _ = router(primary, backoff_max_s=8.0, breaker_threshold=10)
    await r.complete(USER)
    assert sleeper.delays == [5, 8.0]


async def test_falls_back_after_max_attempts() -> None:
    primary = FakeProvider("groq", "m1", script=[rate_limited()] * 3)
    fallback = FakeProvider("gemini", "m2", script=["from fallback"])
    r, _, _ = router(primary, fallback, breaker_threshold=10)
    res = await r.complete(USER)
    assert (res.text, res.provider, res.fallback_used, res.attempts) == (
        "from fallback",
        "gemini",
        True,
        4,
    )
    assert len(primary.calls) == 3


async def test_fatal_error_skips_retries_and_falls_back() -> None:
    primary = FakeProvider("groq", "m1", script=[FatalLLMError("401 bad key", status=401)])
    fallback = FakeProvider("gemini", "m2", script=["ok"])
    r, sleeper, _ = router(primary, fallback)
    assert (await r.complete(USER)).provider == "gemini"
    assert len(primary.calls) == 1 and sleeper.delays == []


async def test_all_providers_failing_raises_with_causes() -> None:
    primary = FakeProvider("groq", "m1", script=[FatalLLMError("bad")])
    fallback = FakeProvider("gemini", "m2", script=[FatalLLMError("also bad")])
    r, _, _ = router(primary, fallback)
    with pytest.raises(AllProvidersFailedError) as info:
        await r.complete(USER)
    assert [c.args[0] for c in info.value.causes] == ["bad", "also bad"]


async def test_circuit_breaker_skips_provider_for_cooldown() -> None:
    primary = FakeProvider("groq", "m1", script=[rate_limited()] * 3 + ["recovered"])
    fallback = FakeProvider("gemini", "m2")
    r, _, clock = router(primary, fallback, breaker_threshold=3, breaker_cooldown_s=60)
    first = await r.complete(USER)  # 3 failures open the breaker, fallback answers
    assert first.provider == "gemini" and r.breaker(primary).is_open

    calls_before = len(primary.calls)
    second = await r.complete(USER)  # still open: primary not even tried
    assert second.provider == "gemini" and len(primary.calls) == calls_before
    assert r.status()[0]["circuit_open"] is True

    clock.t += 61  # cooldown over: primary is tried again
    third = await r.complete(USER)
    assert third.provider == "groq" and third.text == "recovered"
    assert not r.breaker(primary).is_open


def test_breaker_resets_on_success() -> None:
    clock = Clock()
    b = CircuitBreaker(2, 60, clock)
    b.record_failure()
    b.record_success()
    b.record_failure()
    assert not b.is_open
    b.record_failure()
    assert b.is_open


# ---------------------------------------------------------------- JSON mode


class Answer(BaseModel):
    concept_id: str
    confidence: float = Field(ge=0, le=1)


async def test_json_valid_first_time() -> None:
    fake = FakeProvider(script=['```json\n{"concept_id": "stack", "confidence": 0.9}\n```'])
    r, _, _ = router(fake)
    res = await r.complete(USER, schema=Answer)
    assert res.data == Answer(concept_id="stack", confidence=0.9)
    assert fake.calls[0][1].json_schema == Answer.model_json_schema()


async def test_json_repaired_once_with_the_validation_error() -> None:
    fake = FakeProvider(
        script=[
            '{"concept_id": "stack", "confidence": 7}',
            '{"concept_id": "stack", "confidence": 0.7}',
        ]
    )
    r, _, _ = router(fake)
    res = await r.complete(USER, schema=Answer)
    assert res.data.confidence == 0.7 and res.attempts == 2
    repair_messages = fake.calls[1][0]
    assert repair_messages[-2].role == "assistant"
    assert "confidence" in repair_messages[-1].content
    assert res.tokens_in > fake.calls[0][0][0].content.count(" ")  # tokens of both calls summed


async def test_json_still_invalid_after_repair_falls_back() -> None:
    bad = FakeProvider("groq", "m1", script=["not json", "still not json"])
    good = FakeProvider(
        "gemini", "m2", script=[json.dumps({"concept_id": "queue", "confidence": 1})]
    )
    r, _, _ = router(bad, good)
    res = await r.complete(USER, schema=Answer)
    assert res.provider == "gemini" and res.data.concept_id == "queue"


async def test_json_failure_everywhere_raises() -> None:
    r, _, _ = router(FakeProvider(script=["nope", "nope"]))
    with pytest.raises(AllProvidersFailedError):
        await r.complete(USER, schema=Answer)


def test_parse_json_reply_rejects_prose() -> None:
    with pytest.raises(ValueError):
        parse_json_reply("Sure! Here it is: {}", Answer)


# ---------------------------------------------------------------- streaming


async def _collect(r: LLMRouter) -> tuple[str, StreamDone]:
    text, done = "", None
    async for ev in r.stream(USER):
        if isinstance(ev, TextDelta):
            text += ev.text
        else:
            done = ev
    assert done is not None
    return text, done


async def test_stream_yields_deltas_then_usage() -> None:
    r, _, _ = router(FakeProvider(script=["one two three"]))
    text, done = await _collect(r)
    assert text == "one two three" == done.result.text
    assert done.result.tokens_out > 0 and done.result.est_cost_usd > 0


async def test_stream_retries_and_falls_back_before_first_token() -> None:
    primary = FakeProvider("groq", "m1", script=[rate_limited()] * 3)
    fallback = FakeProvider("gemini", "m2", script=["fallback answer"])
    r, sleeper, _ = router(primary, fallback, breaker_threshold=10)
    text, done = await _collect(r)
    assert text == "fallback answer" and done.result.fallback_used and len(sleeper.delays) == 2


async def test_stream_error_after_first_token_is_not_retried() -> None:
    primary = FakeProvider("groq", "m1", script=[FailMidStream("partial answer", rate_limited())])
    fallback = FakeProvider("gemini", "m2", script=["should not be used"])
    r, _, _ = router(primary, fallback)
    seen = ""
    with pytest.raises(RetryableLLMError):
        async for ev in r.stream(USER):
            if isinstance(ev, TextDelta):
                seen += ev.text
    assert seen == "partial answer" and fallback.calls == []


def _opts(**kw: object):  # type: ignore[no-untyped-def]
    from app.llm.types import CallOptions

    return CallOptions(**kw)  # type: ignore[arg-type]
