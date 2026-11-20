"""Stage 1: map the question to concepts (zero-shot LLM, with a hybrid retrieval fallback).

1. One JSON LLM call: the compact concept catalogue, the last turns of the thread (so "why?" works
   as a follow-up) and the question → {is_on_topic, concepts[≤3]{id, confidence, reason}, intent}.
2. If the call fails, returns unusable JSON, or the best confidence is below CLASSIFY_THRESHOLD:
   also run (a) the Neo4j fulltext index over name/aliases/keywords and (b) embedding similarity
   over concept descriptions, and merge all ranked lists with reciprocal-rank fusion (RRF).
The trace records which path decided.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from app.graph.repository import STOPWORDS
from app.guardrails.prompts import GUARD_RULES, wrap_question
from app.llm.embeddings import EmbeddingProvider
from app.llm.errors import LLMError
from app.llm.fake import register_fake_responder
from app.llm.router import LLMRouter
from app.llm.types import LLMResult, Message
from app.tutor.catalogue import Catalogue
from app.tutor.graph_source import TutorGraph
from app.tutor.trace import ConceptMatch, FallbackInfo, Intent

logger = logging.getLogger(__name__)

RRF_K = 60
MAX_CONCEPTS = 3
EMBEDDING_MIN_SIMILARITY = 0.25  # below this an embedding "match" is noise
RELATIVE_CUTOFF = 0.35  # LLM picks this far below the best pick are dropped


class ConceptPick(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(default="", max_length=300)


class Classification(BaseModel):
    is_on_topic: bool
    concepts: list[ConceptPick] = Field(default_factory=list, max_length=MAX_CONCEPTS)
    intent: Intent = "explain"


CLASSIFIER_SYSTEM = f"""\
You map a student's question to concepts in a Data Structures & Algorithms course.
Choose at most {MAX_CONCEPTS} concept ids from the catalogue below (ids only, exactly as written).
Pick the concept the question is really about, including the underlying cause when the student
describes a symptom (for example a crash caused by how something works). Give each a confidence
from 0 to 1 and a short reason. Set is_on_topic to false when the question is not about
programming, data structures or algorithms. Intent is one of: explain, debug, compare, example,
complexity, other.

Concept catalogue:
<catalogue>
{{catalogue}}
</catalogue>

{GUARD_RULES}"""


def classifier_messages(
    catalogue: Catalogue, question: str, history: Sequence[Message]
) -> list[Message]:
    turns = "\n".join(f"{m.role}: {m.content[:400]}" for m in history)
    user = (f"<history>\n{turns}\n</history>\n\n" if turns else "") + wrap_question(question)
    return [
        Message("system", CLASSIFIER_SYSTEM.replace("{catalogue}", catalogue.text)),
        Message("user", user),
    ]


# ---------------------------------------------------------------- heuristics (fallback + fake)

_INTENT_CUES: list[tuple[Intent, re.Pattern[str]]] = [
    ("debug", re.compile(r"\b(crash(es|ed|ing)?|errors?|bugs?|wrong|fails?|failing|exceeded|"
                         r"exception|overflows?|why does my|why is my|doesn't work|does not work|"
                         r"segfaults?|infinite|slow|slower|takes forever)\b")),
    ("complexity", re.compile(r"\b(complexity|big[- ]?o|o\(|runtime|how fast|time cost|"
                              r"space cost|amortized)\b")),
    ("compare", re.compile(r"\b(difference|differences|vs\.?|versus|compare|comparison|"
                           r"better than|or a)\b")),
    ("example", re.compile(r"\b(example|show me|code for|implement|walk me through|trace)\b")),
]  # fmt: skip
_WORD = re.compile(r"[a-z0-9]+")
_STOP = STOPWORDS | {"a", "an", "of", "in", "on", "or", "to", "is", "by", "vs"}


def heuristic_intent(text: str) -> Intent:
    t = text.lower()
    for intent, pattern in _INTENT_CUES:
        if pattern.search(t):
            return intent
    return "explain"


def _fold(word: str) -> str:
    """Crude plural folding so "segfaults" matches "segfault" (but "class" stays "class")."""
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _norm(text: str) -> list[str]:
    return [_fold(w) for w in _WORD.findall(text.lower())]


def keyword_scores(
    text: str, rows: Sequence[tuple[str, str, list[str]]]
) -> list[tuple[str, float]]:
    """Deterministic phrase matching: rows are (id, name, phrases). Whole phrases score their word
    count; shared name words add half a point. Returns (id, score) best first, score > 0 only."""
    t = " " + " ".join(_norm(text)) + " "
    words = set(t.split())
    scored: list[tuple[str, float]] = []
    for cid, name, phrases in rows:
        score = 0.0
        for phrase in {p.lower() for p in [name, cid.replace("_", " "), *phrases] if p}:
            norm = " ".join(_norm(phrase))
            if norm and f" {norm} " in t:
                score += len(norm.split())
        # Shared name words add half a point each (3+ letters, not stopwords: the "s" of
        # "what's" must not match "Dijkstra's"). Word-only matches stay below the threshold, so
        # they always go through the hybrid fallback.
        name_words = {w for w in _norm(name) if len(w) >= 3 and w not in _STOP}
        score += 0.5 * len(name_words & words)
        if score > 0:
            scored.append((cid, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored


_PROGRAMMING_CUES = re.compile(
    r"\b(code|coding|program\w*|function|method|class|loops?|arrays?|lists?|strings?|pointers?|"
    r"nodes?|trees?|graphs?|algorithms?|complexity|big[- ]?o|runtime|recursi\w*|iterat\w*|"
    r"sort\w*|search\w*|hash\w*|stack|queue|heap|python|java|javascript|compil\w*|segfaults?|"
    r"bugs?|debug\w*|memory|index|integer|variables?|data structures?|implement\w*|factorial|"
    r"fibonacci|matrix)\b|c\+\+|o\(n"
)
_CATALOGUE_LINE = re.compile(r"^([a-z0-9_]+) \| ([^|]*) \| ([^|]*) \| ([^|]*) \|", re.MULTILINE)
_QUESTION_TAG = re.compile(r"<student_question>(.*?)</student_question>", re.DOTALL)
_HISTORY_TAG = re.compile(r"<history>(.*?)</history>", re.DOTALL)


def fake_classify(messages: Sequence[Message], _schema: dict[str, Any]) -> dict[str, Any]:
    """FakeProvider responder: keyword/alias matching against the catalogue in the prompt."""
    system = next((m.content for m in messages if m.role == "system"), "")
    user = "\n".join(m.content for m in messages if m.role == "user")
    rows = [
        (cid, name.strip(), [p.strip() for p in f"{aliases};{keywords}".split(";") if p.strip()])
        for cid, name, aliases, keywords in _CATALOGUE_LINE.findall(system)
    ]
    question = " ".join(_QUESTION_TAG.findall(user)).strip()
    scored = keyword_scores(question, rows)
    if not scored:  # a short follow-up ("why?") falls back to the conversation
        scored = keyword_scores(" ".join(_HISTORY_TAG.findall(user)), rows)
    if any(s >= 1 for _, s in scored):
        # A whole alias/keyword phrase beats loose name-word overlap ("function" alone must not
        # add "Function Calls & the Call Stack" to a question about recursive functions).
        scored = [(cid, s) for cid, s in scored if s >= 1]
    picks = [
        {"id": cid, "confidence": round(min(0.95, 0.45 + 0.15 * s), 2), "reason": "keyword match"}
        for cid, s in scored[:MAX_CONCEPTS]
    ]
    # No concept phrase matched: decline only when nothing in the question sounds like
    # programming; otherwise return no picks so the hybrid fallback decides (as a real model that
    # is unsure would).
    on_topic = bool(picks) or bool(_PROGRAMMING_CUES.search(question.lower()))
    return {"is_on_topic": on_topic, "concepts": picks, "intent": heuristic_intent(question)}


register_fake_responder("Classification", fake_classify)


def rrf(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal-rank fusion: score(id) = sum over lists of 1 / (k + rank)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(dict.fromkeys(ranking), start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


# ---------------------------------------------------------------- the stage


@dataclass
class ClassifyResult:
    is_on_topic: bool
    intent: Intent
    matched: list[ConceptMatch]
    path: str  # "llm" | "hybrid"
    fallback: FallbackInfo | None = None
    llm_results: list[LLMResult] = field(default_factory=list)


async def classify(
    *,
    question: str,
    history: Sequence[Message],
    catalogue: Catalogue,
    llm: LLMRouter,
    repo: TutorGraph | None,
    embedder: EmbeddingProvider | None,
    threshold: float,
) -> ClassifyResult:
    llm_results: list[LLMResult] = []
    parsed: Classification | None = None
    try:
        result = await llm.complete(
            classifier_messages(catalogue, question, history),
            schema=Classification,
            temperature=0.0,
            max_tokens=300,
        )
        llm_results.append(result)
        parsed = result.data if isinstance(result.data, Classification) else None
    except LLMError:
        parsed = None

    picks: list[ConceptMatch] = []
    if parsed is not None:
        seen: set[str] = set()
        for p in parsed.concepts:
            if p.id in catalogue.by_id and p.id not in seen:  # drop invented ids
                seen.add(p.id)
                picks.append(
                    ConceptMatch(
                        id=p.id,
                        name=catalogue.name(p.id),
                        confidence=p.confidence,
                        reason=p.reason,
                        source="llm",
                    )
                )
        picks.sort(key=lambda m: -m.confidence)
        if not parsed.is_on_topic:
            return ClassifyResult(False, parsed.intent, [], "llm", None, llm_results)
        if picks and picks[0].confidence >= threshold:
            # Keep picks close to the best one; a far weaker extra concept only adds noise.
            top = picks[0].confidence
            close = [m for m in picks if m.confidence >= top - RELATIVE_CUTOFF]
            return ClassifyResult(
                True, parsed.intent, close[:MAX_CONCEPTS], "llm", None, llm_results
            )

    # ---- hybrid fallback: fulltext + description embeddings (+ weak LLM picks), fused by RRF
    fulltext: list[str] = []
    if repo is not None:
        fulltext = [cid for cid, _ in await repo.search_concepts(catalogue.subject_id, question, 5)]
        fulltext = [cid for cid in fulltext if cid in catalogue.by_id]
    embedding: list[str] = []
    if embedder is not None and catalogue.concepts:
        try:
            qvec = (await embedder.embed([question]))[0]
            nearest = await catalogue.nearest(qvec, embedder, k=5)
            embedding = [cid for cid, sim in nearest if sim >= EMBEDDING_MIN_SIMILARITY]
        except Exception:  # embeddings down or misconfigured: fulltext alone still works
            logger.warning("classifier embedding fallback failed", exc_info=True)
    rankings = [r for r in ([m.id for m in picks], fulltext, embedding) if r]
    fused = rrf(rankings)[:MAX_CONCEPTS]
    info = FallbackInfo(fulltext=fulltext, embedding=embedding, fused=[cid for cid, _ in fused])
    intent: Intent = parsed.intent if parsed is not None else heuristic_intent(question)
    if not fused:
        return ClassifyResult(False, intent, [], "hybrid", info, llm_results)
    by_pick = {m.id: m for m in picks}
    best = fused[0][1]
    matched: list[ConceptMatch] = []
    for cid, score in fused:
        # fused scores are tiny (1/61...); map them to 0.4-0.6 relative to the best one
        confidence = 0.4 + 0.2 * score / best
        if cid in by_pick:
            confidence = max(confidence, by_pick[cid].confidence)
        matched.append(
            ConceptMatch(
                id=cid,
                name=catalogue.name(cid),
                confidence=round(confidence, 3),
                reason=by_pick[cid].reason if cid in by_pick else "fulltext/embedding match",
                source="fusion",
            )
        )
    return ClassifyResult(True, intent, matched, "hybrid", info, llm_results)
