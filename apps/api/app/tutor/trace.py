"""RetrievalTrace: what each pipeline stage did, stored with the answer and shown in the UI.

It is the explainability record of the project (report §2.3): which concepts were matched and how,
which prerequisite edges brought in which concepts, which chunks filled the context, and what the
agentic controller decided.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["graphrag", "plain_rag"]
Intent = Literal["explain", "debug", "compare", "example", "complexity", "other"]
MatchSource = Literal["llm", "fulltext", "embedding", "fusion", "continued"]
Role = Literal["matched", "prerequisite", "related"]
Action = Literal["answer_now", "ask_diagnostic", "expand_traversal"]


class ConceptMatch(BaseModel):
    id: str
    name: str
    confidence: float = Field(ge=0, le=1)
    reason: str = ""
    source: MatchSource = "llm"


class TraceEdge(BaseModel):
    source: str
    target: str
    type: str


class TraceConcept(BaseModel):
    id: str
    name: str
    role: Role
    depth: int = 0  # 0 for matched concepts, hops away otherwise
    weak: bool | None = None  # prerequisites only: mastery < 0.6 or never practised
    mastery: float | None = None
    path: list[TraceEdge] = Field(default_factory=list)  # edges from this concept to a match


class TraceChunk(BaseModel):
    id: str
    concept_id: str
    kind: str
    tokens: int
    score: float | None = None  # plain_rag: cosine similarity


class ControllerStep(BaseModel):
    action: Action
    reason: str = ""
    question: str | None = None  # the diagnostic question, for ask_diagnostic


class FallbackInfo(BaseModel):
    fulltext: list[str] = Field(default_factory=list)
    embedding: list[str] = Field(default_factory=list)
    fused: list[str] = Field(default_factory=list)


class RetrievalTrace(BaseModel):
    version: int = 1
    mode: Mode = "graphrag"
    question: str = ""
    is_on_topic: bool = True
    intent: Intent = "explain"
    classification_path: Literal["llm", "hybrid", "continued", "cache", "none"] = "llm"
    matched: list[ConceptMatch] = Field(default_factory=list)
    fallback: FallbackInfo | None = None
    depth: int = 2
    concepts: list[TraceConcept] = Field(default_factory=list)
    controller: list[ControllerStep] = Field(default_factory=list)
    diagnostic: str | None = None  # set when this turn ended with a diagnostic question
    diagnostic_reply: str | None = None  # the student's answer, when a turn resumed
    chunks: list[TraceChunk] = Field(default_factory=list)
    budget_tokens: int = 0
    used_tokens: int = 0
    timings_ms: dict[str, int] = Field(default_factory=dict)
    cached: bool = False
    truncated: bool = False
    citations: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)
    cache_key: str | None = None  # response-cache entry this answer came from or went into

    def summary(self) -> str:
        """Human-readable one-liner, e.g. 'Recursion ← Call Stack (weak)'."""
        names = {c.id: c.name for c in self.concepts}
        matched = [names.get(m.id, m.name) for m in self.matched]
        prereqs = [
            c.name + (" (weak)" if c.weak else "")
            for c in self.concepts
            if c.role == "prerequisite"
        ][:3]
        if not matched:
            return "No matching concept"
        return " + ".join(matched) + ("" if not prereqs else " ← " + ", ".join(prereqs))
