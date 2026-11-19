"""Pydantic models for the concept graph source file (concepts.yaml) and graph query results."""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

ConceptId = Annotated[str, Field(min_length=1, max_length=64)]


class SubjectDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ConceptId
    name: str = Field(min_length=1, max_length=200)


class ConceptDef(BaseModel):
    """One concept as written in concepts.yaml."""

    model_config = ConfigDict(extra="forbid")

    id: ConceptId
    name: str = Field(min_length=1, max_length=200)
    cluster: str = Field(min_length=1, max_length=64)
    difficulty: int = Field(ge=1, le=5)
    order_index: int | None = Field(default=None, ge=0)
    description: str = Field(min_length=10, max_length=600)
    aliases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    prerequisites: list[ConceptId] = Field(default_factory=list)
    related: list[ConceptId] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id_format(cls, v: str) -> str:
        if not ID_PATTERN.match(v):
            raise ValueError("id must be snake_case: lowercase letters, digits, underscores")
        return v


class ConceptFile(BaseModel):
    """The whole concepts.yaml document."""

    model_config = ConfigDict(extra="forbid")

    subject: SubjectDef
    roots: list[ConceptId] = Field(default_factory=list)
    concepts: list[ConceptDef]


class GraphConcept(BaseModel):
    """A concept as returned by GraphRepository."""

    id: str
    subject_id: str
    name: str
    cluster: str
    difficulty: int
    order_index: int
    description: str
    aliases: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    status: str = "approved"


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str  # PREREQUISITE_OF | RELATED_TO
    weight: float = 1.0
    source_kind: str = "human"  # human | llm
    status: str = "approved"  # approved | proposed
    rationale: str | None = None


class Subgraph(BaseModel):
    concepts: list[GraphConcept]
    edges: list[GraphEdge]
