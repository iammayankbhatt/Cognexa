"""Content & question-bank editor (reviewer role).

Edits made here win over the files until they are copied back into data/subjects/ (DEC-060):
an edited chunk or question gets source 'admin', and seeding skips such rows.

Question statistics (per question, over graded answers):
- attempts, % correct;
- discrimination D = p(upper) - p(lower): learners are split at the median of their overall
  accuracy; a good item is answered correctly more often by stronger learners (D >= 0.2 is
  usual, < 0.1 is weak);
- flags: too_easy (>= 95 % correct), too_hard (<= 15 %), both from 10 attempts;
  low_discrimination (D < 0.1) from 20 attempts.
"""

from __future__ import annotations

import hashlib
import statistics
import uuid
from collections import defaultdict
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import case, func, select, update

from app.admin.graph_editor import GraphEditor
from app.auth.deps import CurrentUser, require_role
from app.content.models import Question
from app.content.notes import KIND_BY_HEADING
from app.core.errors import AppError
from app.db.tables import content_chunks, questions, quiz_answers
from app.graph.repository import ChunkRecord

router = APIRouter(prefix="/admin/content", tags=["admin"])
Reviewer = Annotated[CurrentUser, Depends(require_role("reviewer"))]
CHUNK_KINDS = sorted(set(KIND_BY_HEADING.values()))
MIN_ATTEMPTS_FLAG = 10
MIN_ATTEMPTS_DISCRIMINATION = 20


def editor(request: Request) -> GraphEditor:
    return GraphEditor.from_request(request)


Editor = Annotated[GraphEditor, Depends(editor)]


class ChunkEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=20, max_length=12_000)
    kind: str = Field(max_length=32)
    reviewed: bool | None = None


class Flags(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewed: bool | None = None
    status: Literal["active", "inactive"] | None = None


class QuestionEdit(BaseModel):
    """Every authored field except the id (validated with the same rules as the YAML files)."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["mcq", "multi_select", "true_false", "code_output", "short_answer"]
    difficulty: int
    prompt: str
    code: str | None = None
    language: Literal["python", "cpp"] = "python"
    options: list[dict[str, Any]] | None = None
    answer: Any
    explanation: str
    rubric: dict[str, Any] | None = None
    misconception_tag: str | None = Field(default=None, max_length=100)
    diagnoses_prereq: str | None = Field(default=None, max_length=64)
    reviewed: bool | None = None


def _chunk_view(r: Any) -> dict[str, Any]:
    return {
        "id": r.id,
        "concept_id": r.concept_id,
        "kind": r.kind,
        "heading": r.heading,
        "text": r.text,
        "order": r.order,
        "reviewed": r.reviewed,
        "source": r.source,
        "embedded": r.embedding_hash is not None and r.embedding_hash == r.content_hash,
        "updated_at": r.updated_at,
    }


def _question_view(r: Any) -> dict[str, Any]:
    return {
        "id": r.id,
        "concept_id": r.concept_id,
        "type": r.type,
        "difficulty": r.difficulty,
        "prompt": r.prompt,
        "code": r.code,
        "language": r.language,
        "options": r.options,
        "answer": r.answer,
        "explanation": r.explanation,
        "rubric": r.rubric,
        "misconception_tag": r.misconception_tag,
        "diagnoses_prereq": r.diagnoses_prereq,
        "status": r.status,
        "source": r.source,
        "reviewed": r.reviewed,
        "updated_at": r.updated_at,
    }


def item_stats(
    answers: list[tuple[str, uuid.UUID, bool]], user_accuracy: dict[uuid.UUID, float]
) -> dict[str, dict[str, Any]]:
    """answers = (question_id, user_id, correct). Pure function, unit-tested."""
    by_q: dict[str, list[tuple[uuid.UUID, bool]]] = defaultdict(list)
    for qid, uid, ok in answers:
        by_q[qid].append((uid, ok))
    median = statistics.median(user_accuracy.values()) if user_accuracy else 0.0
    out: dict[str, dict[str, Any]] = {}
    for qid, rows in by_q.items():
        n = len(rows)
        pct = sum(ok for _, ok in rows) / n
        upper = [ok for uid, ok in rows if user_accuracy.get(uid, 0.0) >= median]
        lower = [ok for uid, ok in rows if user_accuracy.get(uid, 0.0) < median]
        disc = (
            round(sum(upper) / len(upper) - sum(lower) / len(lower), 3) if upper and lower else None
        )
        flags = []
        if n >= MIN_ATTEMPTS_FLAG and pct >= 0.95:
            flags.append("too_easy")
        if n >= MIN_ATTEMPTS_FLAG and pct <= 0.15:
            flags.append("too_hard")
        # an item everyone gets right (or wrong) cannot discriminate; it is flagged as such above
        if not flags and n >= MIN_ATTEMPTS_DISCRIMINATION and disc is not None and disc < 0.1:
            flags.append("low_discrimination")
        out[qid] = {
            "attempts": n,
            "pct_correct": round(pct, 3),
            "discrimination": disc,
            "flags": flags,
        }
    return out


@router.get("/concepts/{concept_id}")
async def concept_content(concept_id: str, _: Reviewer, ed: Editor) -> dict[str, Any]:
    concept = await ed.repo.get_concept(concept_id)
    if concept is None:
        raise AppError("not_found", "Concept not found.", 404)
    async with ed.db.sessions()() as session:
        chunk_rows = (
            await session.execute(
                select(content_chunks)
                .where(content_chunks.c.concept_id == concept_id)
                .order_by(content_chunks.c.order, content_chunks.c.id)
            )
        ).all()
        q_rows = (
            await session.execute(
                select(questions)
                .where(questions.c.concept_id == concept_id)
                .order_by(questions.c.status, questions.c.id)
            )
        ).all()
        qids = [r.id for r in q_rows]
        graded = quiz_answers.c.is_correct.is_not(None) & quiz_answers.c.pending.is_(False)
        answers = (
            await session.execute(
                select(
                    quiz_answers.c.question_id, quiz_answers.c.user_id, quiz_answers.c.is_correct
                ).where(quiz_answers.c.question_id.in_(qids), graded)
            )
        ).all() if qids else []  # fmt: skip
        users = {a.user_id for a in answers}
        accuracy = (
            {
                r.user_id: float(r.acc)
                for r in await session.execute(
                    select(
                        quiz_answers.c.user_id,
                        func.avg(case((quiz_answers.c.is_correct, 1.0), else_=0.0)).label("acc"),
                    )
                    .where(quiz_answers.c.user_id.in_(users), graded)
                    .group_by(quiz_answers.c.user_id)
                )
            }
            if users
            else {}
        )
    stats = item_stats([(a.question_id, a.user_id, bool(a.is_correct)) for a in answers], accuracy)
    empty: dict[str, Any] = {
        "attempts": 0,
        "pct_correct": None,
        "discrimination": None,
        "flags": [],
    }
    return {
        "concept": concept.model_dump(),
        "chunks": [_chunk_view(r) for r in chunk_rows],
        "chunk_kinds": CHUNK_KINDS,
        "questions": [{**_question_view(r), "stats": stats.get(r.id, empty)} for r in q_rows],
    }


async def _load_chunk(ed: GraphEditor, chunk_id: str) -> Any:
    async with ed.db.sessions()() as session:
        row = (
            await session.execute(select(content_chunks).where(content_chunks.c.id == chunk_id))
        ).first()
    if row is None:
        raise AppError("not_found", "Chunk not found.", 404)
    return row


@router.put("/chunks/{chunk_id}")
async def edit_chunk(
    chunk_id: str, body: ChunkEdit, request: Request, user: Reviewer, ed: Editor
) -> dict[str, Any]:
    if body.kind not in CHUNK_KINDS:
        raise AppError("validation_error", f"Unknown chunk kind '{body.kind}'.", 422)
    old = await _load_chunk(ed, chunk_id)
    concept = await ed.repo.get_concept(old.concept_id)
    if concept is None:
        raise AppError("not_found", "The chunk's concept no longer exists.", 404)
    source = "admin" if old.source == "notes" else old.source
    reviewed = old.reviewed if body.reviewed is None else body.reviewed
    digest = hashlib.sha256(f"{body.heading}\n{body.text}".encode()).hexdigest()
    embedder = request.app.state.tutor.embedder
    vector: list[float] | None = None
    warning = None
    if embedder is not None:
        try:
            vector = (await embedder.embed([f"{concept.name} - {body.heading}\n{body.text}"]))[0]
        except Exception:
            warning = "Saved, but embedding failed: run scripts/seed_vectors.py to index it."
    else:
        warning = "Saved without an embedding: run scripts/seed_vectors.py to index it."
    await ed.repo.upsert_chunk(
        ChunkRecord(
            id=chunk_id,
            concept_id=old.concept_id,
            subject_id=old.subject_id,
            kind=body.kind,
            heading=body.heading,
            text=body.text,
            order=old.order,
            reviewed=reviewed,
            source=source,
        )
    )
    async with ed.db.sessions()() as session, session.begin():
        await session.execute(
            update(content_chunks)
            .where(content_chunks.c.id == chunk_id)
            .values(
                heading=body.heading,
                text=body.text,
                kind=body.kind,
                reviewed=reviewed,
                source=source,
                content_hash=digest,
                embedding=vector,
                embedding_hash=digest if vector is not None else None,
                embedding_model=embedder.model if vector is not None else None,
                updated_at=func.now(),
            )
        )
    await ed._after_change(
        user.id,
        old.subject_id,
        "content.edit_chunk",
        chunk_id,
        {"before": {"heading": old.heading, "kind": old.kind, "chars": len(old.text)},
         "after": {"heading": body.heading, "kind": body.kind, "chars": len(body.text)}},
        [old.concept_id],
    )  # fmt: skip
    return {**_chunk_view(await _load_chunk(ed, chunk_id)), "warning": warning}


@router.patch("/chunks/{chunk_id}")
async def flag_chunk(chunk_id: str, body: Flags, user: Reviewer, ed: Editor) -> dict[str, Any]:
    if body.reviewed is None or body.status is not None:
        raise AppError("validation_error", "Chunks only take a reviewed flag.", 422)
    old = await _load_chunk(ed, chunk_id)
    await ed.repo._write(
        "MATCH (k:Chunk {id: $id}) SET k.reviewed = $reviewed", id=chunk_id, reviewed=body.reviewed
    )
    async with ed.db.sessions()() as session, session.begin():
        await session.execute(
            update(content_chunks)
            .where(content_chunks.c.id == chunk_id)
            .values(reviewed=body.reviewed, updated_at=func.now())
        )
    await ed._after_change(
        user.id, old.subject_id, "content.review_chunk", chunk_id, {"reviewed": body.reviewed}, []
    )
    return _chunk_view(await _load_chunk(ed, chunk_id))


async def _load_question(ed: GraphEditor, question_id: str) -> Any:
    async with ed.db.sessions()() as session:
        row = (
            await session.execute(select(questions).where(questions.c.id == question_id))
        ).first()
    if row is None:
        raise AppError("not_found", "Question not found.", 404)
    return row


@router.put("/questions/{question_id}")
async def edit_question(
    question_id: str, body: QuestionEdit, user: Reviewer, ed: Editor
) -> dict[str, Any]:
    old = await _load_question(ed, question_id)
    data = body.model_dump(exclude={"reviewed"})
    try:
        q = Question(id=question_id, **data)
    except ValidationError as e:
        first = e.errors()[0]
        where = ".".join(str(p) for p in first["loc"]) or "question"
        raise AppError(
            "validation_error",
            f"{where}: {first['msg'].removeprefix('Value error, ')}",
            422,
            details={"errors": [
                {"loc": [str(p) for p in err["loc"]], "msg": err["msg"]} for err in e.errors()
            ]},
        ) from e  # fmt: skip
    if q.diagnoses_prereq and await ed.repo.get_concept(q.diagnoses_prereq) is None:
        raise AppError("validation_error", "diagnoses_prereq must be an existing concept id.", 422)
    values: dict[str, Any] = {
        "type": q.type,
        "difficulty": q.difficulty,
        "prompt": q.prompt,
        "code": q.code,
        "language": q.language,
        "options": [o.model_dump() for o in q.options] if q.options else None,
        "answer": q.answer,
        "explanation": q.explanation,
        "rubric": q.rubric.model_dump() if q.rubric else None,
        "misconception_tag": q.misconception_tag,
        "diagnoses_prereq": q.diagnoses_prereq,
        "source": "admin",
        "updated_at": func.now(),
    }
    if body.reviewed is not None:
        values["reviewed"] = body.reviewed
    async with ed.db.sessions()() as session, session.begin():
        await session.execute(
            update(questions).where(questions.c.id == question_id).values(**values)
        )
    await ed._after_change(
        user.id,
        old.subject_id,
        "content.edit_question",
        question_id,
        {"before": _question_view(old) | {"updated_at": None}, "type": q.type},
        [old.concept_id],
    )
    return _question_view(await _load_question(ed, question_id))


@router.patch("/questions/{question_id}")
async def flag_question(
    question_id: str, body: Flags, user: Reviewer, ed: Editor
) -> dict[str, Any]:
    if body.reviewed is None and body.status is None:
        raise AppError("validation_error", "Nothing to change.", 422)
    old = await _load_question(ed, question_id)
    values: dict[str, Any] = {"updated_at": func.now()}
    if body.reviewed is not None:
        values["reviewed"] = body.reviewed
    if body.status is not None:
        values["status"] = body.status
        values["source"] = "admin"  # keep the admin's choice on the next seed
    async with ed.db.sessions()() as session, session.begin():
        await session.execute(
            update(questions).where(questions.c.id == question_id).values(**values)
        )
    await ed._after_change(
        user.id,
        old.subject_id,
        "content.flag_question",
        question_id,
        body.model_dump(exclude_none=True),
        [],
    )
    return _question_view(await _load_question(ed, question_id))
