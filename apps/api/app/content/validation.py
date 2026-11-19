"""Content validation for a subject: notes, question bank, study sets and the eval test set.

`strict=False` (default) validates whatever exists and reports missing files as pending, so CI stays
green while content is written cluster by cluster. `strict=True` also requires full coverage.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.content.models import (
    MIN_BY_CATEGORY,
    MIN_BY_TYPE,
    MIN_QUESTIONS,
    QuestionFile,
    StudySets,
    TestsetItem,
)
from app.content.notes import (
    MAX_WORDS,
    MIN_WORDS,
    REQUIRED_SECTIONS,
    NoteFormatError,
    extract_code_blocks,
    parse_note_file,
    self_check_pairs,
)
from app.graph.loader import load_subject, subject_dir
from app.graph.models import ConceptDef

STUDY_SET_SIZE = 20


@dataclass
class ConceptRow:
    concept_id: str
    cluster: str
    note: str = "pending"  # ok | pending | invalid
    words: int = 0
    questions: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    reviewed: bool = False


@dataclass
class ContentReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rows: list[ConceptRow] = field(default_factory=list)
    testset_count: int = 0
    study_sets: str = "pending"

    @property
    def ok(self) -> bool:
        return not self.errors


def short_name(c: ConceptDef) -> str:
    """Name without a trailing parenthetical, e.g. 'Time Complexity & Big-O'."""
    return re.sub(r"\s*\(.*\)\s*$", "", c.name).strip()


def mentions(text: str, c: ConceptDef) -> bool:
    low = text.lower()
    return short_name(c).lower() in low or c.id.replace("_", " ") in low or c.id in low


def ancestors(concepts: list[ConceptDef]) -> dict[str, set[str]]:
    by_id = {c.id: c for c in concepts}
    memo: dict[str, set[str]] = {}

    def walk(cid: str) -> set[str]:
        if cid in memo:
            return memo[cid]
        memo[cid] = set()  # guards against cycles (validate_graph reports them)
        result: set[str] = set()
        for p in by_id[cid].prerequisites:
            if p in by_id:
                result |= {p} | walk(p)
        memo[cid] = result
        return result

    return {c.id: walk(c.id) for c in concepts}


def _check_note(
    c: ConceptDef,
    dependents: list[ConceptDef],
    path: Path,
    rep: ContentReport,
    row: ConceptRow,
    by_id: dict[str, ConceptDef],
) -> None:
    def err(msg: str) -> None:
        rep.errors.append(f"{c.id}: {msg}")
        row.note = "invalid"

    try:
        note = parse_note_file(path)
    except NoteFormatError as exc:
        err(str(exc))
        return
    row.note = "ok"
    row.words = note.word_count
    row.reviewed = note.frontmatter.reviewed
    fm = note.frontmatter
    if fm.id != c.id:
        err(f"frontmatter id '{fm.id}' does not match file/concept id")
    if fm.name != c.name:
        err(f"frontmatter name '{fm.name}' must equal concept name '{c.name}'")
    if fm.cluster != c.cluster:
        err(f"frontmatter cluster '{fm.cluster}' must equal '{c.cluster}'")
    if note.extra_headings:
        err(f"unexpected H2 sections: {', '.join(note.extra_headings)}")

    got = [s.heading for s in note.sections]
    want = [h for h, _ in REQUIRED_SECTIONS]
    missing = [h for h in want if h not in got]
    if missing:
        err(f"missing sections: {', '.join(missing)}")
    elif got != want:
        err("sections are not in the required order")
    if row.words < MIN_WORDS:
        err(f"too short ({row.words} words; minimum {MIN_WORDS})")
    elif row.words > MAX_WORDS:
        err(f"too long ({row.words} words; maximum {MAX_WORDS})")
    elif row.words < 600:
        rep.warnings.append(f"{c.id}: {row.words} words (target 600-1200)")

    sec = {s.kind: s.text for s in note.sections}
    for kind, text in sec.items():
        if len(text.strip()) < 20:
            err(f"section '{kind}' is empty")
    code = sec.get("code", "")
    if not extract_code_blocks(code, "python"):
        err("Code section needs a ```python block")
    if not extract_code_blocks(code, "cpp"):
        err("Code section needs a ```cpp block")

    builds = sec.get("prerequisites", "")
    for p in c.prerequisites:
        if p in by_id and not mentions(builds, by_id[p]):
            err(f"'Builds On' never mentions prerequisite '{by_id[p].name}'")
    if (
        not c.prerequisites
        and "foundation" not in builds.lower()
        and "no prerequisite" not in builds.lower()
    ):
        rep.warnings.append(f"{c.id}: root concept; 'Builds On' should say it has no prerequisites")
    nxt = sec.get("next", "")
    if dependents and not any(mentions(nxt, d) for d in dependents):
        err("'Leads To' mentions none of the concepts that depend on it")

    pairs = self_check_pairs(sec.get("self_check", ""))
    if len(pairs) != 3:
        err(f"'Check Yourself' needs exactly 3 **Qn.**/**An.** pairs (found {len(pairs)})")


def _check_questions(
    c: ConceptDef,
    anc: set[str],
    path: Path,
    rep: ContentReport,
    row: ConceptRow,
    seen_ids: set[str],
) -> dict[str, object]:
    out: dict[str, object] = {}
    try:
        qf = QuestionFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (ValidationError, yaml.YAMLError, ValueError) as exc:
        rep.errors.append(f"{c.id}: questions file invalid: {str(exc)[:600]}")
        return out
    if qf.concept_id != c.id:
        rep.errors.append(f"{c.id}: questions file concept_id is '{qf.concept_id}'")
    row.questions = len(qf.questions)
    row.by_type = dict(Counter(q.type for q in qf.questions))
    if len(qf.questions) < MIN_QUESTIONS:
        rep.errors.append(f"{c.id}: only {len(qf.questions)} questions (minimum {MIN_QUESTIONS})")
    for qtype, minimum in MIN_BY_TYPE.items():
        have = row.by_type.get(qtype, 0)
        if have < minimum:
            rep.errors.append(f"{c.id}: needs at least {minimum} {qtype} question(s), has {have}")
    if len({q.difficulty for q in qf.questions}) < 2:
        rep.errors.append(f"{c.id}: questions must span at least 2 difficulty levels")
    for q in qf.questions:
        if not q.id.startswith(f"{c.id}-q"):
            rep.errors.append(f"{q.id}: id must start with '{c.id}-q'")
        if q.id in seen_ids:
            rep.errors.append(f"{q.id}: duplicate question id")
        seen_ids.add(q.id)
        if q.diagnoses_prereq is not None and q.diagnoses_prereq not in anc:
            rep.errors.append(
                f"{q.id}: diagnoses_prereq '{q.diagnoses_prereq}' is not a prerequisite of {c.id}"
            )
        out[q.id] = q
    return out


def _check_study_sets(path: Path, questions: dict[str, object], rep: ContentReport) -> None:
    try:
        sets = StudySets.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    except (ValidationError, yaml.YAMLError) as exc:
        rep.errors.append(f"_study_sets.yaml invalid: {str(exc)[:400]}")
        rep.study_sets = "invalid"
        return
    before = len(rep.errors)
    for name, ids in (("pretest_A", sets.pretest_A), ("posttest_B", sets.posttest_B)):
        if len(ids) != STUDY_SET_SIZE:
            rep.errors.append(f"{name}: must have {STUDY_SET_SIZE} questions, has {len(ids)}")
        if len(set(ids)) != len(ids):
            rep.errors.append(f"{name}: duplicate question ids")
        for qid in ids:
            if qid not in questions:
                rep.errors.append(f"{name}: unknown question id '{qid}'")
    if set(sets.pretest_A) & set(sets.posttest_B):
        rep.errors.append("pretest_A and posttest_B must not share questions")

    def profile(ids: list[str]) -> tuple[list[str], list[int]]:
        qs = [questions[i] for i in ids if i in questions]
        concept = sorted(q.id.rsplit("-q", 1)[0] for q in qs)  # type: ignore[attr-defined]
        diff = sorted(q.difficulty for q in qs)  # type: ignore[attr-defined]
        return concept, diff

    if len(rep.errors) == before:
        (ca, da), (cb, db) = profile(sets.pretest_A), profile(sets.posttest_B)
        if ca != cb:
            rep.errors.append("pretest_A and posttest_B must cover the same concepts")
        if da != db:
            rep.errors.append("pretest_A and posttest_B must have matched difficulty distributions")
    rep.study_sets = "ok" if len(rep.errors) == before else "invalid"


def _check_testset(
    path: Path,
    concepts: list[ConceptDef],
    anc: dict[str, set[str]],
    rep: ContentReport,
    strict: bool,
) -> None:
    by_id = {c.id: c for c in concepts}
    items: list[TestsetItem] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            items.append(TestsetItem.model_validate(json.loads(line)))
        except (ValidationError, json.JSONDecodeError) as exc:
            rep.errors.append(f"testset line {lineno}: {str(exc)[:300]}")
    rep.testset_count = len(items)
    for item_id, n in Counter(i.id for i in items).items():
        if n > 1:
            rep.errors.append(f"testset: duplicate id '{item_id}'")
    for it in items:
        for cid in (*it.gold_concepts, *it.gold_prerequisites):
            if cid not in by_id:
                rep.errors.append(f"testset {it.id}: unknown concept '{cid}'")
        if it.category == "off_topic":
            if it.gold_concepts or it.gold_prerequisites:
                rep.errors.append(f"testset {it.id}: off_topic items must have no gold concepts")
            continue
        if not it.gold_concepts:
            rep.errors.append(f"testset {it.id}: needs gold_concepts")
        if it.category == "unnamed_prerequisite":
            if not it.gold_prerequisites:
                rep.errors.append(f"testset {it.id}: unnamed_prerequisite needs gold_prerequisites")
            reach: set[str] = set()
            for g in it.gold_concepts:
                reach |= anc.get(g, set())
            for p in it.gold_prerequisites:
                if p in by_id and p not in reach:
                    rep.errors.append(
                        f"testset {it.id}: '{p}' is not a prerequisite of {it.gold_concepts}"
                    )
                if p in by_id:
                    low = it.question.lower()
                    if short_name(by_id[p]).lower() in low or p.replace("_", " ") in low:
                        rep.errors.append(
                            f"testset {it.id}: question names its own prerequisite '{p}' "
                            "(unnamed_prerequisite must only describe symptoms)"
                        )
        elif it.category == "direct":
            low = it.question.lower()
            if not any(mentions(low, by_id[g]) for g in it.gold_concepts if g in by_id):
                rep.warnings.append(f"testset {it.id}: direct question does not name its concept")
    if strict:
        counts: Counter[str] = Counter(i.category for i in items)
        for cat, minimum in MIN_BY_CATEGORY.items():
            if counts.get(cat, 0) < minimum:
                rep.errors.append(
                    f"testset: category '{cat}' has {counts.get(cat, 0)} items (minimum {minimum})"
                )
        if len(items) < 80:
            rep.errors.append(f"testset: {len(items)} items (minimum 80)")


def validate_subject_content(subject_id: str = "dsa", *, strict: bool = False) -> ContentReport:
    rep = ContentReport()
    doc = load_subject(subject_id)
    concepts = sorted(doc.concepts, key=lambda c: c.order_index or 0)
    by_id = {c.id: c for c in concepts}
    anc = ancestors(concepts)
    deps: dict[str, list[ConceptDef]] = defaultdict(list)
    for c in concepts:
        for p in c.prerequisites:
            deps[p].append(c)

    base = subject_dir(subject_id)
    seen_q: set[str] = set()
    questions: dict[str, object] = {}
    for c in concepts:
        row = ConceptRow(c.id, c.cluster)
        rep.rows.append(row)
        note_path = base / "content" / f"{c.id}.md"
        if note_path.exists():
            _check_note(c, deps[c.id], note_path, rep, row, by_id)
        elif strict:
            rep.errors.append(f"{c.id}: missing content/{c.id}.md")
        q_path = base / "questions" / f"{c.id}.yaml"
        if q_path.exists():
            questions.update(_check_questions(c, anc[c.id], q_path, rep, row, seen_q))
        elif strict:
            rep.errors.append(f"{c.id}: missing questions/{c.id}.yaml")

    known = {c.id for c in concepts}
    for stray in sorted((base / "content").glob("*.md")) if (base / "content").exists() else []:
        if stray.stem not in known:
            rep.errors.append(f"content/{stray.name}: no such concept in concepts.yaml")
    for stray in (
        sorted((base / "questions").glob("*.yaml")) if (base / "questions").exists() else []
    ):
        if stray.stem not in known and not stray.stem.startswith("_"):
            rep.errors.append(f"questions/{stray.name}: no such concept in concepts.yaml")

    sets_path = base / "questions" / "_study_sets.yaml"
    if sets_path.exists():
        _check_study_sets(sets_path, questions, rep)
    elif strict:
        rep.errors.append("questions/_study_sets.yaml is missing")

    test_path = base / "eval" / "testset.jsonl"
    if test_path.exists():
        _check_testset(test_path, concepts, anc, rep, strict)
    elif strict:
        rep.errors.append("eval/testset.jsonl is missing")
    return rep
