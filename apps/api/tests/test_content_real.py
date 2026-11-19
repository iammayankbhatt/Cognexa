"""Quality gates over the real DSA content (notes, questions, snippets, answer keys)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.content.loader import load_chunks
from app.content.notes import REQUIRED_SECTIONS
from app.content.snippets import collect_snippets, gpp, run_all, verify_code_questions
from app.content.validation import validate_subject_content
from app.graph.loader import load_subject, subject_dir


def test_real_content_validates() -> None:
    rep = validate_subject_content("dsa")
    assert rep.errors == [], "\n".join(rep.errors)


def test_every_existing_note_yields_all_ten_chunks() -> None:
    chunks = load_chunks("dsa")
    notes = sorted((subject_dir("dsa") / "content").glob("*.md"))
    assert len(chunks) == len(notes) * len(REQUIRED_SECTIONS)
    ids = [c.id for c in chunks]
    assert len(set(ids)) == len(ids)


def test_python_snippets_run(tmp_path: Path) -> None:
    snippets = [s for s in collect_snippets("dsa") if s.language == "python"]
    failures = [
        f"{r.snippet.filename}: {r.detail}"
        for r in run_all(snippets, tmp_path)
        if r.status != "passed"
    ]
    assert failures == []


@pytest.mark.skipif(gpp() is None, reason="g++ not available")
def test_cpp_snippets_compile_and_run(tmp_path: Path) -> None:
    snippets = [s for s in collect_snippets("dsa") if s.language == "cpp"]
    failures = [
        f"{r.snippet.filename}: {r.detail}"
        for r in run_all(snippets, tmp_path)
        if r.status != "passed"
    ]
    assert failures == []


def test_code_output_answers_match_real_program_output(tmp_path: Path) -> None:
    failed = [
        f"{r.question_id}: {r.detail}"
        for r in verify_code_questions("dsa", tmp_path)
        if r.status == "failed"
    ]
    assert failed == []


def test_concept_names_in_notes_match_the_graph() -> None:
    names = {c.id: c.name for c in load_subject("dsa").concepts}
    for path in (subject_dir("dsa") / "content").glob("*.md"):
        assert path.stem in names
