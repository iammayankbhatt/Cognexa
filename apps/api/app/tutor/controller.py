"""Stage 5: the bounded agentic step (AGENTIC_MODE).

After traversal, a small JSON call picks ONE action:
- answer_now: the context is good enough;
- ask_diagnostic: ask the student one quick check question about the most suspicious weak
  prerequisite; the turn ends and the student's reply resumes it with the stored trace;
- expand_traversal: the context is thin, walk prerequisites to depth 3 and decide again.
At most MAX_STEPS controller calls per turn. A second expand, a diagnostic without a weak
prerequisite, or any controller failure all become answer_now: the step can never loop.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from app.guardrails.prompts import GUARD_RULES, wrap_question
from app.llm.errors import LLMError
from app.llm.fake import register_fake_responder
from app.llm.router import LLMRouter
from app.llm.types import LLMResult, Message
from app.tutor.trace import Action, ControllerStep, Intent, TraceConcept

MAX_STEPS = 2
EXPANDED_DEPTH = 3
THIN_CONTEXT_TOKENS = 600  # less gathered context than this counts as thin


class ControllerDecision(BaseModel):
    action: Action
    reason: str = Field(default="", max_length=300)
    question: str | None = Field(default=None, max_length=300)
    concept_id: str | None = Field(default=None, max_length=80)


CONTROLLER_SYSTEM = f"""\
You are the planning step of Cognexa, a Data Structures & Algorithms tutor. Before the answer is
written, choose ONE action:
- "answer_now": the context is enough to answer well (the usual choice).
- "ask_diagnostic": the question looks like a symptom of a weak prerequisite and one quick check
  question would show whether the student understands it. Set "question" to that single short
  question (start with "Quick check:") and "concept_id" to the prerequisite it tests. Use this
  sparingly and never when the student is just asking for a definition.
- "expand_traversal": the gathered context is thin and deeper prerequisites could help.
Reply with JSON only.

{GUARD_RULES}"""


def controller_messages(
    *,
    question: str,
    intent: Intent,
    concepts: Sequence[TraceConcept],
    context_tokens: int,
    depth: int,
    step: int,
    allow_diagnostic: bool,
) -> list[Message]:
    lines = [f"Intent: {intent}", f"Traversal depth: {depth} (max {EXPANDED_DEPTH})"]
    for c in concepts:
        if c.role == "matched":
            lines.append(f"Matched: {c.id} ({c.name})")
        elif c.role == "prerequisite":
            m = "never practised" if c.mastery is None else f"mastery {c.mastery:.2f}"
            lines.append(
                f"Prerequisite: {c.id} ({c.name}), {c.depth} step(s), "
                f"{'WEAK' if c.weak else 'ok'}, {m}"
            )
    lines.append(f"Context gathered: about {context_tokens} tokens")
    lines.append(f"Planning step {step} of {MAX_STEPS}")
    if not allow_diagnostic:
        lines.append("ask_diagnostic is not available for this turn.")
    if depth >= EXPANDED_DEPTH:
        lines.append("expand_traversal is not available (already at max depth).")
    user = "<plan_input>\n" + "\n".join(lines) + "\n</plan_input>\n\n" + wrap_question(question)
    return [Message("system", CONTROLLER_SYSTEM), Message("user", user)]


# ---------------------------------------------------------------- fake responder

_PLAN_INPUT = re.compile(r"<plan_input>(.*?)</plan_input>", re.DOTALL)
_PREREQ_LINE = re.compile(
    r"^Prerequisite: ([a-z0-9_]+) \(([^)]*)\), (\d+) step\(s\), (WEAK|ok), (.*)$", re.MULTILINE
)
_MATCHED_LINE = re.compile(r"^Matched: ([a-z0-9_]+) \(([^)]*)\)$", re.MULTILINE)


def fake_controller(messages: Sequence[Message], _schema: dict[str, Any]) -> dict[str, Any]:
    """Deterministic policy for local (keyless) mode:
    - expand when the gathered context is thin and depth can grow;
    - ask a diagnostic when the question is a debugging symptom and a prerequisite was practised
      with a low score (evidence, not just "never practised", so new students are not quizzed);
    - otherwise answer now."""
    user = "\n".join(m.content for m in messages if m.role == "user")
    plan = "\n".join(_PLAN_INPUT.findall(user))
    tokens_m = re.search(r"about (\d+) tokens", plan)
    depth_m = re.search(r"depth: (\d+)", plan)
    tokens = int(tokens_m.group(1)) if tokens_m else 0
    depth = int(depth_m.group(1)) if depth_m else 2
    if tokens < THIN_CONTEXT_TOKENS and depth < EXPANDED_DEPTH:
        return {"action": "expand_traversal", "reason": "context is thin"}
    can_ask = "ask_diagnostic is not available" not in plan
    if can_ask and "Intent: debug" in plan:
        matched = _MATCHED_LINE.findall(plan)
        for cid, name, _steps, state, mastery in _PREREQ_LINE.findall(plan):
            if state == "WEAK" and mastery.startswith("mastery"):
                about = matched[0][1] if matched else "this problem"
                return {
                    "action": "ask_diagnostic",
                    "reason": f"{name} is weak ({mastery}) and explains this symptom",
                    "question": f"Quick check: in your own words, what is {name.lower()} and how "
                    f"is it involved in {about.lower()}?",
                    "concept_id": cid,
                }
    return {"action": "answer_now", "reason": "context covers the question"}


register_fake_responder("ControllerDecision", fake_controller)


# ---------------------------------------------------------------- the step


async def decide(
    llm: LLMRouter,
    *,
    question: str,
    intent: Intent,
    concepts: Sequence[TraceConcept],
    context_tokens: int,
    depth: int,
    step: int,
    allow_diagnostic: bool,
    results: list[LLMResult],
) -> ControllerStep:
    """One controller call, with its decision checked against what is allowed."""
    try:
        result = await llm.complete(
            controller_messages(
                question=question,
                intent=intent,
                concepts=concepts,
                context_tokens=context_tokens,
                depth=depth,
                step=step,
                allow_diagnostic=allow_diagnostic,
            ),
            schema=ControllerDecision,
            temperature=0.0,
            max_tokens=200,
        )
    except LLMError:
        return ControllerStep(action="answer_now", reason="planner unavailable")
    results.append(result)
    d = result.data if isinstance(result.data, ControllerDecision) else None
    if d is None:
        return ControllerStep(action="answer_now", reason="planner reply unusable")
    weak = [c for c in concepts if c.role == "prerequisite" and c.weak]
    if d.action == "expand_traversal" and (depth >= EXPANDED_DEPTH or step >= MAX_STEPS):
        return ControllerStep(action="answer_now", reason=f"expand not possible: {d.reason}")
    if d.action == "ask_diagnostic":
        if not allow_diagnostic or not weak or not (d.question and d.question.strip()):
            return ControllerStep(
                action="answer_now", reason=f"diagnostic not possible: {d.reason}"
            )
        q = " ".join(d.question.split())
        return ControllerStep(action="ask_diagnostic", reason=d.reason, question=q)
    return ControllerStep(action=d.action, reason=d.reason)
