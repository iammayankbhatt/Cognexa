"""Load validated chunks and questions from a subject's data folder for the seed scripts."""

from __future__ import annotations

import yaml

from app.content.models import Question, QuestionFile
from app.content.notes import Chunk, build_chunks, parse_note_file
from app.graph.loader import subject_dir


def load_chunks(subject_id: str = "dsa") -> list[Chunk]:
    """Chunks for every concept note that exists, in concept-file order."""
    chunks: list[Chunk] = []
    for path in sorted((subject_dir(subject_id) / "content").glob("*.md")):
        chunks.extend(build_chunks(parse_note_file(path), subject_id))
    return chunks


def load_questions(subject_id: str = "dsa") -> list[tuple[str, Question]]:
    """(concept_id, question) for every question file that exists."""
    out: list[tuple[str, Question]] = []
    for path in sorted((subject_dir(subject_id) / "questions").glob("*.yaml")):
        if path.stem.startswith("_"):
            continue
        qf = QuestionFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        out.extend((qf.concept_id, q) for q in qf.questions)
    return out
