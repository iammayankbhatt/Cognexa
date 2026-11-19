"""Content validation, snippet running and chunk building, on a small synthetic subject."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.content.models import Question
from app.content.notes import (
    NoteFormatError,
    build_chunks,
    extract_code_blocks,
    parse_note,
    self_check_pairs,
)
from app.content.snippets import collect_snippets, gpp, run_all
from app.content.validation import validate_subject_content

from .content_helpers import PREREQS, mcq, note_text, valid_questions, write_subject


@pytest.fixture
def subject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    return write_subject(tmp_path, monkeypatch)


def errors(strict: bool = False) -> str:
    return "\n".join(validate_subject_content("mini", strict=strict).errors)


def write_questions(subject: Path, cid: str, data: dict[str, Any]) -> None:
    (subject / "questions" / f"{cid}.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


# ------------------------------------------------------------------ happy path
def test_valid_subject_passes_strictly_except_testset_and_study_sets(subject: Path) -> None:
    rep = validate_subject_content("mini", strict=False)
    assert rep.errors == []
    assert [r.note for r in rep.rows] == ["ok", "ok", "ok"]
    assert all(r.questions == 8 for r in rep.rows)
    strict = validate_subject_content("mini", strict=True)
    assert any("_study_sets.yaml is missing" in e for e in strict.errors)
    assert any("testset.jsonl is missing" in e for e in strict.errors)


def test_missing_files_are_pending_unless_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_subject(tmp_path, monkeypatch, notes=False, questions=False)
    rep = validate_subject_content("mini", strict=False)
    assert rep.errors == [] and {r.note for r in rep.rows} == {"pending"}
    assert any(
        "missing content/base.md" in e for e in validate_subject_content("mini", strict=True).errors
    )


# ------------------------------------------------------------------ notes
def test_note_missing_section_or_wrong_order_or_extra_h2(subject: Path) -> None:
    p = subject / "content" / "mid.md"
    p.write_text(note_text("mid", drop_section="Intuition"), encoding="utf-8")
    assert "missing sections: Intuition" in errors()
    p.write_text(note_text("mid", extra_h2=True), encoding="utf-8")
    assert "unexpected H2 sections: Bonus Round" in errors()
    text = (
        note_text("mid")
        .replace("## Overview", "## Temp")
        .replace("## Intuition", "## Overview")
        .replace("## Temp", "## Intuition")
    )
    p.write_text(text, encoding="utf-8")
    assert "not in the required order" in errors()


def test_note_length_limits(subject: Path) -> None:
    p = subject / "content" / "mid.md"
    p.write_text(note_text("mid", words=100), encoding="utf-8")
    assert "too short" in errors()
    p.write_text(note_text("mid", words=2400), encoding="utf-8")
    assert "too long" in errors()


def test_note_needs_both_languages(subject: Path) -> None:
    p = subject / "content" / "mid.md"
    p.write_text(note_text("mid").replace("```cpp", "```text"), encoding="utf-8")
    assert "needs a ```cpp block" in errors()


def test_builds_on_must_mention_each_prerequisite(subject: Path) -> None:
    p = subject / "content" / "mid.md"
    p.write_text(
        note_text("mid", builds_on="It builds on nothing in particular."), encoding="utf-8"
    )
    assert "'Builds On' never mentions prerequisite 'Base Idea'" in errors()
    p.write_text(note_text("mid", builds_on="It uses base idea heavily."), encoding="utf-8")
    assert errors() == ""  # id/name mention is accepted case-insensitively


def test_leads_to_must_mention_a_dependent(subject: Path) -> None:
    p = subject / "content" / "mid.md"
    p.write_text(note_text("mid", leads_to="It leads to glory."), encoding="utf-8")
    assert "'Leads To' mentions none" in errors()


def test_check_yourself_needs_three_pairs(subject: Path) -> None:
    (subject / "content" / "mid.md").write_text(note_text("mid", checks=2), encoding="utf-8")
    assert "exactly 3" in errors()


def test_frontmatter_must_match_concept(subject: Path) -> None:
    (subject / "content" / "mid.md").write_text(
        note_text("mid", name="Wrong Name"), encoding="utf-8"
    )
    assert "must equal concept name" in errors()


def test_note_without_frontmatter_is_rejected() -> None:
    with pytest.raises(NoteFormatError):
        parse_note("## Overview\nhello")


def test_h2_inside_code_fence_is_not_a_section() -> None:
    text = note_text("base").replace("print('hello from python')", "print('x')\n## not a heading")
    note = parse_note(text)
    assert note.extra_headings == []


def test_chunks_have_stable_ids_kinds_and_hashes() -> None:
    chunks = build_chunks(parse_note(note_text("mid")), "mini")
    assert [c.kind for c in chunks] == [
        "overview",
        "intuition",
        "mechanism",
        "example",
        "code",
        "complexity",
        "pitfalls",
        "prerequisites",
        "next",
        "self_check",
    ]
    assert chunks[0].id == "mid#overview" and chunks[0].subject_id == "mini"
    assert len({c.content_hash for c in chunks}) == len(chunks)
    again = build_chunks(parse_note(note_text("mid")), "mini")
    assert [c.content_hash for c in again] == [c.content_hash for c in chunks]


def test_code_block_and_self_check_parsing() -> None:
    note = parse_note(note_text("mid"))
    code = next(s.text for s in note.sections if s.kind == "code")
    assert len(extract_code_blocks(code, "python")) == 1
    checks = next(s.text for s in note.sections if s.kind == "self_check")
    assert len(self_check_pairs(checks)) == 3


# ------------------------------------------------------------------ questions
def test_question_count_and_type_mix(subject: Path) -> None:
    data = valid_questions("mid", "base")
    data["questions"] = data["questions"][:6]
    write_questions(subject, "mid", data)
    msg = errors()
    assert "only 6 questions" in msg
    assert "code_output" in msg and "short_answer" in msg


def test_question_difficulty_spread(subject: Path) -> None:
    data = valid_questions("mid", "base")
    for q in data["questions"]:
        q["difficulty"] = 2
    write_questions(subject, "mid", data)
    assert "at least 2 difficulty levels" in errors()


def test_diagnoses_prereq_must_be_a_real_prerequisite(subject: Path) -> None:
    data = valid_questions("mid", "base")
    data["questions"][0]["diagnoses_prereq"] = "top"
    write_questions(subject, "mid", data)
    assert "diagnoses_prereq 'top' is not a prerequisite of mid" in errors()
    # restore mid; transitive prerequisites (top -> mid -> base) are allowed
    write_questions(subject, "mid", valid_questions("mid", "base"))
    write_questions(subject, "top", valid_questions("top", "base"))
    assert errors() == ""


def test_duplicate_question_ids_across_files(subject: Path) -> None:
    data = valid_questions("mid", "base")
    data["questions"][0]["id"] = "base-q01"
    write_questions(subject, "mid", data)
    msg = errors()
    assert "must start with 'mid-q'" in msg and "duplicate question id" in msg


def test_stray_files_are_reported(subject: Path) -> None:
    (subject / "content" / "ghost.md").write_text(note_text("base"), encoding="utf-8")
    assert "no such concept" in errors()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda q: q.update(answer="z"), "mcq answer must be one option id"),
        (lambda q: q["options"][1].pop("why_wrong"), "why_wrong"),
        (lambda q: q["options"].pop(), "exactly 4 options"),
        (lambda q: q.update(id="BAD"), "id must look like"),
        (lambda q: q.update(difficulty=4), "less than or equal to 3"),
        (lambda q: q.update(rubric={"key_points": ["x"]}), "only short_answer"),
    ],
)
def test_mcq_schema_rejections(mutate: Any, message: str) -> None:
    q = mcq("mid", 1)
    mutate(q)
    with pytest.raises(ValueError, match=message):
        Question.model_validate(q)


def test_other_question_type_rejections() -> None:
    base = valid_questions("mid")["questions"]
    multi = dict(base[4])
    multi["answer"] = ["a"]
    with pytest.raises(ValueError, match="2\\+ distinct"):
        Question.model_validate(multi)
    multi["answer"] = ["a", "b", "c", "d"]
    with pytest.raises(ValueError, match="not all of them"):
        Question.model_validate(multi)
    tf = dict(base[5])
    tf["answer"] = "yes"
    with pytest.raises(ValueError, match="true or false"):
        Question.model_validate(tf)
    co = dict(base[6])
    co["code"] = None
    with pytest.raises(ValueError, match="needs code"):
        Question.model_validate(co)
    sa = dict(base[7])
    sa.pop("rubric")
    with pytest.raises(ValueError, match="needs a rubric"):
        Question.model_validate(sa)


# ------------------------------------------------------------------ study sets
def make_sets(subject: Path, a: list[str], b: list[str]) -> None:
    (subject / "questions" / "_study_sets.yaml").write_text(
        yaml.safe_dump({"pretest_A": a, "posttest_B": b}), encoding="utf-8"
    )


def extended_subject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Every concept gets 14 questions: q01-q08 from valid_questions plus six extra difficulty-1 mcq."""
    subject = write_subject(tmp_path, monkeypatch)
    for cid in ("base", "mid", "top"):
        data = valid_questions(cid, PREREQS[cid][0] if PREREQS[cid] else None)
        data["questions"] += [mcq(cid, i, 1, None) for i in range(9, 15)]
        write_questions(subject, cid, data)
    return subject


def sets_for(a_ids: list[str], b_ids: list[str]) -> tuple[list[str], list[str]]:
    a = [f"{c}-{q}" for c in ("base", "mid", "top") for q in a_ids]
    b = [f"{c}-{q}" for c in ("base", "mid", "top") for q in b_ids]
    return a, b


def test_matched_study_sets_are_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.content import validation

    monkeypatch.setattr(validation, "STUDY_SET_SIZE", 12)
    subject = extended_subject(tmp_path, monkeypatch)
    # per concept: A = d1,d1,d2,d2  B = d1,d1,d2,d2 (different questions, same concept and difficulty)
    make_sets(subject, *sets_for(["q01", "q02", "q03", "q05"], ["q09", "q10", "q04", "q07"]))
    rep = validate_subject_content("mini")
    assert rep.errors == []
    assert rep.study_sets == "ok"


@pytest.mark.parametrize(
    ("a_ids", "b_ids", "message"),
    [
        (["q01", "q02", "q03", "q05"], ["q09", "q10", "q04", "q08"], "matched difficulty"),
        (["q01", "q02", "q03", "q05"], ["q09", "q10", "q04", "q03"], "must not share questions"),
        (["q01", "q02", "q03"], ["q09", "q10", "q04"], "must have 12 questions"),
    ],
)
def test_invalid_study_sets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    a_ids: list[str],
    b_ids: list[str],
    message: str,
) -> None:
    from app.content import validation

    monkeypatch.setattr(validation, "STUDY_SET_SIZE", 12)
    subject = extended_subject(tmp_path, monkeypatch)
    make_sets(subject, *sets_for(a_ids, b_ids))
    assert message in errors()


def test_study_sets_must_cover_the_same_concepts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.content import validation

    monkeypatch.setattr(validation, "STUDY_SET_SIZE", 4)
    subject = extended_subject(tmp_path, monkeypatch)
    make_sets(
        subject,
        ["base-q01", "base-q02", "mid-q03", "mid-q05"],
        ["top-q09", "top-q10", "mid-q04", "mid-q07"],
    )
    assert "same concepts" in errors()


def test_study_sets_unknown_and_duplicate_ids(subject: Path) -> None:
    make_sets(subject, ["base-q01"] * 20, ["mid-q01"] * 20)
    assert "duplicate question ids" in errors()
    make_sets(subject, ["nope-q01"] * 3, ["base-q01"] * 3)
    assert "unknown question id" in errors()


# ------------------------------------------------------------------ eval test set
def write_testset(subject: Path, items: list[dict[str, Any]]) -> None:
    (subject / "eval" / "testset.jsonl").write_text(
        "\n".join(json.dumps(i) for i in items) + "\n", encoding="utf-8"
    )


def item(
    i: int, category: str, question: str, concepts: list[str], prereqs: list[str]
) -> dict[str, Any]:
    return {
        "id": f"t{i:03d}",
        "question": question,
        "category": category,
        "gold_concepts": concepts,
        "gold_prerequisites": prereqs,
        "reference_answer": "A reference answer long enough to pass.",
    }


def test_testset_rules(subject: Path) -> None:
    write_testset(
        subject,
        [
            item(1, "direct", "What is the Middle Idea exactly?", ["mid"], []),
            item(
                2,
                "unnamed_prerequisite",
                "My program fails when the thing grows large, why?",
                ["mid"],
                ["base"],
            ),
            item(3, "off_topic", "What is the capital of France please?", [], []),
        ],
    )
    rep = validate_subject_content("mini")
    assert rep.errors == [] and rep.testset_count == 3

    write_testset(
        subject,
        [
            item(
                1, "unnamed_prerequisite", "My code about base idea breaks, why?", ["mid"], ["base"]
            )
        ],
    )
    assert "names its own prerequisite 'base'" in errors()

    write_testset(
        subject,
        [
            item(
                1,
                "unnamed_prerequisite",
                "My program fails when it grows large?",
                ["base"],
                ["mid"],
            )
        ],
    )
    assert "is not a prerequisite of ['base']" in errors()

    write_testset(
        subject, [item(1, "off_topic", "What is the capital of France please?", ["mid"], [])]
    )
    assert "off_topic items must have no gold concepts" in errors()

    write_testset(subject, [item(1, "direct", "What is the Middle Idea exactly?", ["ghost"], [])])
    assert "unknown concept 'ghost'" in errors()

    write_testset(subject, [item(1, "direct", "What is the Middle Idea exactly?", ["mid"], [])] * 2)
    assert "duplicate id" in errors()
    assert "minimum 80" in errors(strict=True)


# ------------------------------------------------------------------ snippets
def test_snippets_run_and_failures_are_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = write_subject(tmp_path / "data", monkeypatch)
    (subject / "content" / "mid.md").write_text(
        note_text("mid", python="raise SystemExit(3)", cpp="int main() { return 0; }"),
        encoding="utf-8",
    )
    results = run_all(collect_snippets("mini"), tmp_path / "out")
    by_name = {r.snippet.filename: r for r in results}
    assert by_name["base_1.py"].status == "passed"
    assert by_name["mid_1.py"].status == "failed"
    cpp = by_name["base_1.cpp"]
    if gpp() is None:
        assert cpp.status == "skipped"
    else:
        assert cpp.status == "passed"


def test_cpp_compile_errors_are_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if gpp() is None:
        pytest.skip("g++ not available")
    subject = write_subject(tmp_path / "data", monkeypatch)
    (subject / "content" / "top.md").write_text(
        note_text("top", cpp="int main() { oops }"), encoding="utf-8"
    )
    results = {
        r.snippet.filename: r for r in run_all(collect_snippets("mini", {"top"}), tmp_path / "out")
    }
    assert (
        results["top_1.cpp"].status == "failed" and "compile error" in results["top_1.cpp"].detail
    )


def test_stray_self_correction_text_is_rejected(subject: Path) -> None:
    note = subject / "content" / "mid.md"
    note.write_text(
        note_text("mid").replace("word word", "wait, that is wrong word", 1), encoding="utf-8"
    )
    assert "unfinished or self-correcting text" in errors()
    note.write_text(note_text("mid"), encoding="utf-8")
    assert errors() == ""
    data = valid_questions("mid", "base")
    data["questions"][0]["explanation"] = "Hmm, let me check the code again before answering this."
    write_questions(subject, "mid", data)
    assert "mid-q01: contains unfinished or self-correcting text" in errors()
