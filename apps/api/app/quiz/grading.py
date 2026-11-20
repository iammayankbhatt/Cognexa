"""Auto-grading for every question type except short answers (see judge.py).

- mcq / true_false: exact match.
- multi_select: partial credit max(0, (correct chosen - wrong chosen) / total correct); duplicate
  selections count once.
- code_output: compare after normalising line endings, trailing spaces, case and trailing
  newlines.
Every result carries feedback: the explanation, plus for a wrong answer the misconception (the
chosen distractor's `why_wrong`) and the diagnosed prerequisite ("This often means Call Stack
needs review").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

CORRECT_AT = 0.999  # a score at or above this counts as fully correct


@dataclass
class QuestionData:
    id: str
    concept_id: str
    type: str
    difficulty: int
    prompt: str
    answer: Any
    explanation: str = ""
    options: list[dict[str, Any]] | None = None
    rubric: dict[str, Any] | None = None
    code: str | None = None
    language: str = "python"
    misconception_tag: str | None = None
    diagnoses_prereq: str | None = None

    @classmethod
    def from_row(cls, r: dict[str, Any]) -> QuestionData:
        return cls(
            id=r["id"],
            concept_id=r["concept_id"],
            type=str(r["type"]),
            difficulty=int(r["difficulty"]),
            prompt=r["prompt"],
            answer=r["answer"],
            explanation=r.get("explanation") or "",
            options=r.get("options"),
            rubric=r.get("rubric"),
            code=r.get("code"),
            language=r.get("language") or "python",
            misconception_tag=r.get("misconception_tag"),
            diagnoses_prereq=r.get("diagnoses_prereq"),
        )

    def public(self) -> dict[str, Any]:
        """What the student sees before answering: no answer, no why_wrong, no rubric."""
        return {
            "id": self.id,
            "concept_id": self.concept_id,
            "type": self.type,
            "difficulty": self.difficulty,
            "prompt": self.prompt,
            "code": self.code,
            "language": self.language,
            "options": [{"id": o["id"], "text": o["text"]} for o in self.options or []] or None,
        }


@dataclass
class Grade:
    score: float | None  # None while a short answer waits for the LLM grader
    is_correct: bool | None
    feedback: str
    misconceptions: list[str] = field(default_factory=list)
    diagnoses_prereq: str | None = None
    graded_by: str = "auto"
    pending: bool = False
    details: dict[str, Any] | None = None


class InvalidResponseError(ValueError):
    pass


_SPACES_EOL = re.compile(r"[ \t]+\n")


def normalise_output(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = _SPACES_EOL.sub("\n", t)
    return "\n".join(line.rstrip() for line in t.strip("\n").split("\n")).strip().casefold()


def check_response(q: QuestionData, response: Any) -> Any:
    """Validate the response shape for the question type; returns the cleaned value.
    None (no answer) is allowed and scores 0."""
    if response is None:
        return None
    t = q.type
    option_ids = {o["id"] for o in q.options or []}
    if t == "mcq":
        if not isinstance(response, str) or response not in option_ids:
            raise InvalidResponseError("Choose one of the options.")
        return response
    if t == "multi_select":
        if not isinstance(response, list) or not all(isinstance(x, str) for x in response):
            raise InvalidResponseError("Send a list of option ids.")
        chosen = list(dict.fromkeys(response))
        if not set(chosen) <= option_ids:
            raise InvalidResponseError("Unknown option.")
        return chosen
    if t == "true_false":
        if not isinstance(response, bool):
            raise InvalidResponseError("Answer true or false.")
        return response
    if t in ("code_output", "short_answer"):
        if not isinstance(response, str):
            raise InvalidResponseError("Type your answer.")
        if len(response) > 4000:
            raise InvalidResponseError("That answer is too long.")
        return response
    raise InvalidResponseError(f"Unknown question type {t}.")


def _feedback(
    q: QuestionData, correct: bool, misconceptions: list[str], prereq_name: str | None
) -> str:
    parts = [q.explanation.strip()] if q.explanation else []
    if not correct:
        parts.extend(m.strip() for m in misconceptions if m)
        if prereq_name:
            parts.append(f"This often means {prereq_name} needs review.")
    return "\n\n".join(p for p in parts if p)


def grade_auto(q: QuestionData, response: Any, prereq_name: str | None = None) -> Grade:
    """Grade an mcq, multi_select, true_false or code_output answer (already validated)."""
    why = {o["id"]: o.get("why_wrong") for o in q.options or []}
    misconceptions: list[str] = []
    if response is None or response == "" or response == []:
        score = 0.0
    elif q.type == "mcq":
        score = 1.0 if response == q.answer else 0.0
        if score == 0.0 and why.get(response):
            misconceptions.append(str(why[response]))
    elif q.type == "true_false":
        score = 1.0 if response is q.answer or response == q.answer else 0.0
    elif q.type == "multi_select":
        correct = set(q.answer)
        chosen = set(response)
        good = len(chosen & correct)
        bad = len(chosen - correct)
        score = max(0.0, (good - bad) / len(correct)) if correct else 0.0
        misconceptions.extend(str(why[c]) for c in sorted(chosen - correct) if why.get(c))
    elif q.type == "code_output":
        score = 1.0 if normalise_output(response) == normalise_output(str(q.answer)) else 0.0
    else:
        raise ValueError(f"grade_auto cannot grade {q.type}")
    correct_flag = score >= CORRECT_AT
    diagnosed = q.diagnoses_prereq if score < 0.5 else None
    return Grade(
        score=round(score, 3),
        is_correct=correct_flag,
        feedback=_feedback(q, correct_flag, misconceptions, prereq_name if diagnosed else None),
        misconceptions=misconceptions,
        diagnoses_prereq=diagnosed,
    )


def correct_answer_view(q: QuestionData) -> Any:
    """The correct answer to reveal after grading (reference answer for short answers)."""
    return q.answer
