"""FakeProvider: deterministic, offline, scriptable. Used in tests and in local "fake" mode.

Behaviour, in order:
1. If a script was given, the next script item decides the reply: a string (reply text), an
   exception (raised), a `FailMidStream` (streams some text, then raises) or a callable taking
   (messages, options) and returning one of those.
2. Otherwise a deterministic default: with a JSON schema, a minimal valid instance of the schema;
   without one, an answer assembled from the `<context>` block of the prompt (so local mode gives
   sensible, grounded answers without any API key), or a short notice when there is no context.
"""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from app.llm.base import LLMProvider
from app.llm.types import (
    CallOptions,
    LLMResult,
    Message,
    StreamDone,
    StreamEvent,
    TextDelta,
    estimate_tokens,
)

_CONTEXT = re.compile(r"<context>(.*?)</context>", re.DOTALL | re.IGNORECASE)
_QUESTION = re.compile(r"<student_question>(.*?)</student_question>", re.DOTALL | re.IGNORECASE)
_TAG = re.compile(r"</?[a-zA-Z_][^>]*>")
_MAX_ANSWER_CHARS = 1500


@dataclass(frozen=True)
class FailMidStream:
    """Script item: stream `text`, then raise `error` (to test errors after the first delta)."""

    text: str
    error: Exception


ScriptItem = str | Exception | FailMidStream | Callable[[Sequence[Message], CallOptions], Any]


def example_from_schema(schema: dict[str, Any], defs: dict[str, Any] | None = None) -> Any:
    """A minimal instance that satisfies a (Pydantic-generated) JSON Schema."""
    defs = defs if defs is not None else schema.get("$defs", {})
    if "$ref" in schema:
        return example_from_schema(defs.get(schema["$ref"].split("/")[-1], {}), defs)
    if "default" in schema:
        return schema["default"]
    if "const" in schema:
        return schema["const"]
    if schema.get("enum"):
        return schema["enum"][0]
    for key in ("anyOf", "oneOf", "allOf"):
        if schema.get(key):
            options = [s for s in schema[key] if s.get("type") != "null"] or schema[key]
            return example_from_schema(options[0], defs)
    kind = schema.get("type")
    if isinstance(kind, list):
        kind = next((k for k in kind if k != "null"), kind[0])
    if kind == "object" or "properties" in schema:
        props = schema.get("properties", {})
        return {name: example_from_schema(props[name], defs) for name in schema.get("required", [])}
    if kind == "array":
        count = int(schema.get("minItems", 0))
        return [example_from_schema(schema.get("items", {}), defs) for _ in range(count)]
    if kind == "string":
        return "x" * int(schema.get("minLength", 0))
    if kind in ("integer", "number"):
        low = schema.get("minimum", schema.get("exclusiveMinimum", 0))
        return int(low) if kind == "integer" else float(low)
    if kind == "boolean":
        return False
    return None


def grounded_answer(messages: Sequence[Message]) -> str:
    """Deterministic answer built only from the prompt's <context> block."""
    # Search message by message: instructions often *mention* the tags ("answer from <context>"),
    # and a regex over the joined prompt would pair that mention with the real closing tag.
    contexts = [c for m in messages for c in _CONTEXT.findall(m.content)]
    questions = [q for m in messages for q in _QUESTION.findall(m.content)]
    question = questions[-1].strip() if questions else ""
    if not contexts:
        about = f' about "{question[:120]}"' if question else ""
        return (
            f"I can only answer from the course notes, and none were provided for this question"
            f"{about}. Try asking about a Data Structures & Algorithms topic."
        )
    paragraphs: list[str] = []
    for block in contexts:
        for para in re.split(r"\n\s*\n", _TAG.sub("", block)):
            line = " ".join(para.split())
            if line and not line.startswith("#"):
                paragraphs.append(line)
    body = ""
    for para in paragraphs:
        if len(body) + len(para) > _MAX_ANSWER_CHARS:
            break
        body += para + "\n\n"
    intro = "Here is what the course notes say"
    intro += f' about "{question[:120]}":' if question else ":"
    return f"{intro}\n\n{body.strip() or paragraphs[0][:_MAX_ANSWER_CHARS]}"


class FakeProvider(LLMProvider):
    def __init__(
        self,
        name: str = "fake",
        model: str = "fake-model",
        script: Iterable[ScriptItem] | None = None,
        latency_s: float = 0.0,
    ) -> None:
        self.name = name
        self.model = model
        self._script: list[ScriptItem] = list(script or [])
        self._latency_s = latency_s
        self.calls: list[tuple[list[Message], CallOptions]] = []

    def push(self, *items: ScriptItem) -> None:
        self._script.extend(items)

    def _next(self, messages: Sequence[Message], options: CallOptions) -> Any:
        self.calls.append((list(messages), options))
        if not self._script:
            return self._default(messages, options)
        item = self._script.pop(0)
        if callable(item) and not isinstance(item, Exception | FailMidStream):
            item = item(messages, options)
        return item

    def _default(self, messages: Sequence[Message], options: CallOptions) -> str:
        if options.json_schema is not None:
            import json

            return json.dumps(example_from_schema(options.json_schema))
        return grounded_answer(messages)

    def _result(self, messages: Sequence[Message], text: str, started: float) -> LLMResult:
        prompt = "".join(m.content for m in messages)
        return LLMResult(
            text=text,
            provider=self.name,
            model=self.model,
            tokens_in=estimate_tokens(prompt),
            tokens_out=estimate_tokens(text),
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    async def complete(self, messages: Sequence[Message], options: CallOptions) -> LLMResult:
        started = time.monotonic()
        if self._latency_s:
            import asyncio

            await asyncio.sleep(self._latency_s)
        item = self._next(messages, options)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, FailMidStream):
            raise item.error
        return self._result(messages, str(item), started)

    async def stream(
        self, messages: Sequence[Message], options: CallOptions
    ) -> AsyncIterator[StreamEvent]:
        started = time.monotonic()
        item = self._next(messages, options)
        if isinstance(item, Exception):
            raise item
        text = item.text if isinstance(item, FailMidStream) else str(item)
        for piece in re.findall(r"\S+\s*|\s+", text):
            yield TextDelta(piece)
        if isinstance(item, FailMidStream):
            raise item.error
        yield StreamDone(self._result(messages, text, started))
