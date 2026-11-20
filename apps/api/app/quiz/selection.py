"""Choosing questions for each quiz mode.

- concept: questions of one concept, easiest first, mixing types.
- adaptive: the student's weakest practised concepts plus the next syllabus concept, each with
  questions at the difficulty that matches its mastery (<0.4 -> 1, 0.4-0.75 -> 2, >0.75 -> 3).
- diagnostic: 10 auto-graded questions spread across the core clusters (onboarding).
- review: concepts whose spaced-review date has come (Phase 9 schedules them).
- pretest / posttest: the fixed user-study forms (data/subjects/<id>/questions/_study_sets.yaml).
Questions answered in the last N days are avoided when enough others exist.
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from app.content.models import StudySets
from app.graph.loader import subject_dir
from app.mastery.model import target_difficulty
from app.quiz.grading import QuestionData

AUTO_TYPES = ("mcq", "multi_select", "true_false", "code_output")
DIAGNOSTIC_CLUSTERS = ("foundations", "complexity", "linear", "searching_hashing", "sorting",
                       "trees", "graphs", "paradigms")  # fmt: skip
DIAGNOSTIC_COUNT = 10
TYPE_ORDER = {"mcq": 0, "true_false": 1, "multi_select": 2, "code_output": 3, "short_answer": 4}


def prefer_unseen(
    pool: Sequence[QuestionData], seen: set[str], k: int, rng: random.Random
) -> list[QuestionData]:
    """k questions, unseen ones first (random order within each group)."""
    fresh = [q for q in pool if q.id not in seen]
    old = [q for q in pool if q.id in seen]
    rng.shuffle(fresh)
    rng.shuffle(old)
    return (fresh + old)[:k]


def for_concept(
    pool: Sequence[QuestionData], seen: set[str], count: int, rng: random.Random
) -> list[QuestionData]:
    picked = prefer_unseen(pool, seen, count, rng)
    # easiest first, so a quiz warms up
    return sorted(picked, key=lambda q: (q.difficulty, TYPE_ORDER.get(q.type, 9), q.id))


def adaptive_concepts(
    effective: Mapping[str, float],
    next_concept: str | None,
    concept_order: Sequence[str],
    k: int = 3,
) -> list[str]:
    """Weakest practised concepts first, then the next syllabus concept, then syllabus order."""
    weakest = sorted(
        effective, key=lambda c: (effective[c], concept_order.index(c) if c in concept_order else 0)
    )
    chosen = [c for c in weakest if effective[c] < 0.75][: k - 1]
    if next_concept and next_concept not in chosen:
        chosen.append(next_concept)
    for c in concept_order:
        if len(chosen) >= k:
            break
        if c not in chosen and c not in effective:
            chosen.append(c)
    return chosen[:k]


def for_adaptive(
    pool: Sequence[QuestionData],
    concepts: Sequence[str],
    effective: Mapping[str, float],
    seen: set[str],
    count: int,
    rng: random.Random,
) -> list[QuestionData]:
    by_concept: dict[str, list[QuestionData]] = {c: [] for c in concepts}
    for q in pool:
        if q.concept_id in by_concept:
            by_concept[q.concept_id].append(q)
    picked: list[QuestionData] = []
    per = max(1, count // max(1, len(concepts)))
    for c in concepts:
        target = target_difficulty(effective.get(c))
        qs = by_concept[c]
        # closest difficulty first, unseen first
        ranked = sorted(
            prefer_unseen(qs, seen, len(qs), rng), key=lambda q: abs(q.difficulty - target)
        )
        picked.extend(ranked[:per])
    leftovers = [q for c in concepts for q in by_concept[c] if q not in picked]
    picked.extend(prefer_unseen(leftovers, seen, count - len(picked), rng))
    return picked[:count]


def for_diagnostic(
    pool: Sequence[QuestionData], concept_rows: Sequence[Mapping[str, Any]], rng: random.Random
) -> list[QuestionData]:
    """One easy auto-graded question from the first concepts of each core cluster."""
    by_cluster: dict[str, list[str]] = {}
    for c in concept_rows:
        by_cluster.setdefault(str(c["cluster"]), []).append(str(c["id"]))
    by_concept: dict[str, list[QuestionData]] = {}
    for q in pool:
        if q.type in AUTO_TYPES and q.difficulty <= 2:
            by_concept.setdefault(q.concept_id, []).append(q)
    picked: list[QuestionData] = []
    depth = 0
    while len(picked) < DIAGNOSTIC_COUNT and depth < 6:
        for cluster in DIAGNOSTIC_CLUSTERS:
            ids = by_cluster.get(cluster, [])
            if depth < len(ids) and len(picked) < DIAGNOSTIC_COUNT:
                qs = sorted(by_concept.get(ids[depth], []), key=lambda q: (q.difficulty, q.id))
                if qs:
                    easiest = [q for q in qs if q.difficulty == qs[0].difficulty]
                    picked.append(rng.choice(easiest))
        depth += 1
    return picked


def study_set(subject_id: str, mode: str) -> list[str]:
    path = subject_dir(subject_id) / "questions" / "_study_sets.yaml"
    sets = StudySets.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    return list(sets.pretest_A if mode == "pretest" else sets.posttest_B)
