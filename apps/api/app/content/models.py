"""Schemas for learning content: questions, study sets and the evaluation test set."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

QuestionType = Literal["mcq", "multi_select", "true_false", "code_output", "short_answer"]
Category = Literal["direct", "unnamed_prerequisite", "multi_concept", "misconception", "off_topic"]

QUESTION_ID = re.compile(r"^[a-z][a-z0-9_]*-q\d{2,3}$")

# Minimum number of questions per concept by type (Phase 3 part 2).
MIN_BY_TYPE: dict[str, int] = {
    "mcq": 4,
    "multi_select": 1,
    "true_false": 1,
    "code_output": 1,
    "short_answer": 1,
}
MIN_QUESTIONS = 8

# Minimum size of the evaluation test set by category (Phase 3 part 3).
MIN_BY_CATEGORY: dict[str, int] = {
    "direct": 20,
    "unnamed_prerequisite": 25,
    "multi_concept": 15,
    "misconception": 12,
    "off_topic": 8,
}


class Option(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Annotated[str, Field(pattern=r"^[a-f]$")]
    text: str = Field(min_length=1, max_length=400)
    # Required for incorrect options: why this distractor is wrong (a plausible misconception).
    why_wrong: str | None = Field(default=None, max_length=500)


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_points: list[str] = Field(min_length=1)
    max_score: float = 1
    partial_credit: bool = True


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: QuestionType
    difficulty: int = Field(ge=1, le=3)
    prompt: str = Field(min_length=10, max_length=1200)
    code: str | None = None
    language: Literal["python", "cpp"] = "python"
    options: list[Option] | None = None
    # mcq: option id | multi_select: list of option ids | true_false: bool |
    # code_output: expected output string | short_answer: reference answer string
    answer: Any
    explanation: str = Field(min_length=30, max_length=1500)
    rubric: Rubric | None = None
    misconception_tag: str | None = None
    diagnoses_prereq: str | None = None

    @field_validator("id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not QUESTION_ID.match(v):
            raise ValueError("id must look like '<concept_id>-q03'")
        return v

    @model_validator(mode="after")
    def _check_shape(self) -> Question:
        t = self.type
        if t in ("mcq", "multi_select"):
            if not self.options:
                raise ValueError(f"{t} needs options")
            ids = [o.id for o in self.options]
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate option ids")
            if t == "mcq":
                if len(self.options) != 4:
                    raise ValueError("mcq needs exactly 4 options")
                if not isinstance(self.answer, str) or self.answer not in ids:
                    raise ValueError("mcq answer must be one option id")
                correct = {self.answer}
            else:
                if len(self.options) < 4:
                    raise ValueError("multi_select needs at least 4 options")
                if (
                    not isinstance(self.answer, list)
                    or len(self.answer) < 2
                    or len(set(self.answer)) != len(self.answer)
                    or not set(self.answer) <= set(ids)
                    or len(self.answer) >= len(ids)
                ):
                    raise ValueError(
                        "multi_select answer must list 2+ distinct option ids, not all of them"
                    )
                correct = set(self.answer)
            for o in self.options:
                if o.id not in correct and not (o.why_wrong and len(o.why_wrong) >= 10):
                    raise ValueError(f"incorrect option '{o.id}' needs a why_wrong explanation")
        elif t == "true_false":
            if not isinstance(self.answer, bool):
                raise ValueError("true_false answer must be true or false")
            if self.options:
                raise ValueError("true_false takes no options")
        elif t == "code_output":
            if not (self.code and self.code.strip()):
                raise ValueError("code_output needs code")
            if not isinstance(self.answer, str) or not self.answer.strip():
                raise ValueError("code_output answer must be the expected output string")
        elif t == "short_answer":
            if not isinstance(self.answer, str) or len(self.answer.strip()) < 10:
                raise ValueError("short_answer needs a reference answer string")
            if self.rubric is None:
                raise ValueError("short_answer needs a rubric")
        if t != "short_answer" and self.rubric is not None:
            raise ValueError("only short_answer questions take a rubric")
        return self


class QuestionFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str
    questions: list[Question]


class StudySets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pretest_A: list[str]
    posttest_B: list[str]


class TestsetItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str = Field(min_length=10, max_length=600)
    category: Category
    gold_concepts: list[str]
    gold_prerequisites: list[str]
    reference_answer: str = Field(min_length=10)
