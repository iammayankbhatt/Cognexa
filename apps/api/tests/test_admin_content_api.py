"""Content & question-bank editor (Phase 11): roles, chunk edits (re-embedded, kept on re-seed),
question validation, status / reviewed flags, and the item statistics."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import quote

from app.api.admin_content import item_stats
from app.content.models import Question
from app.content.notes import Chunk
from app.db.repositories import ContentRepository
from app.graph.repository import ChunkRecord
from tests.conftest import requires_neo4j, requires_postgres
from tests.test_admin_graph_api import GEnv, concept, genv  # noqa: F401
from tests.test_auth_api import env  # noqa: F401

MCQ: dict[str, Any] = {
    "type": "mcq",
    "difficulty": 1,
    "prompt": "Which structure is last in, first out?",
    "options": [
        {"id": "a", "text": "Stack"},
        {"id": "b", "text": "Queue", "why_wrong": "A queue is first in, first out."},
        {"id": "c", "text": "Heap", "why_wrong": "A heap orders by priority, not time."},
        {"id": "d", "text": "Array", "why_wrong": "An array has no removal order of its own."},
    ],
    "answer": "a",
    "explanation": "A stack removes the most recently added element first (LIFO).",
}


async def seed_content(g: GEnv) -> tuple[str, str, str]:
    cid = f"{g.sid}_stack"
    r = await g.client.post(
        "/admin/graph/concepts",
        params={"subject_id": g.sid},
        headers=g.reviewer,
        json=concept(cid, name="Stack"),
    )
    assert r.status_code == 201, r.text
    note = Chunk(id=f"{cid}#overview", concept_id=cid, subject_id=g.sid, kind="overview",
                 heading="Overview", text="A stack is a LIFO collection of items.", order=0,
                 reviewed=False)  # fmt: skip
    qid = f"{cid}-q01"
    async with g.app.state.db.sessions()() as s, s.begin():
        repo = ContentRepository(s)
        await repo.upsert_chunks([note])
        await repo.upsert_questions([(g.sid, cid, Question(id=qid, **MCQ))])
    await g.app.state.graph.repository().upsert_chunk(
        ChunkRecord(id=note.id, concept_id=cid, subject_id=g.sid, kind="overview",
                    heading="Overview", text=note.text)
    )  # fmt: skip
    return cid, quote(note.id, safe=""), qid


@requires_postgres
@requires_neo4j
async def test_reviewers_only(genv: GEnv) -> None:  # noqa: F811
    g = genv
    cid, chunk_id, qid = await seed_content(g)
    calls = [
        ("GET", f"/admin/content/concepts/{cid}", None),
        ("PUT", f"/admin/content/chunks/{chunk_id}", {"heading": "H", "text": "x" * 30, "kind": "overview"}),
        ("PATCH", f"/admin/content/chunks/{chunk_id}", {"reviewed": True}),
        ("PUT", f"/admin/content/questions/{qid}", MCQ),
        ("PATCH", f"/admin/content/questions/{qid}", {"status": "inactive"}),
    ]  # fmt: skip
    for method, path, body in calls:
        r = await g.client.request(method, path, headers=g.student, json=body)
        assert r.status_code == 403, (method, path)


@requires_postgres
@requires_neo4j
async def test_chunk_edit_reembeds_and_survives_reseed(genv: GEnv) -> None:  # noqa: F811
    g = genv
    cid, url_id, _ = await seed_content(g)
    chunk_id = f"{cid}#overview"
    view = (await g.client.get(f"/admin/content/concepts/{cid}", headers=g.reviewer)).json()
    assert [c["id"] for c in view["chunks"]] == [chunk_id]
    assert view["chunks"][0]["source"] == "notes" and "overview" in view["chunk_kinds"]

    bad = await g.client.put(f"/admin/content/chunks/{url_id}", headers=g.reviewer,
                             json={"heading": "Overview", "text": "y" * 40, "kind": "poetry"})  # fmt: skip
    assert bad.status_code == 422
    new_text = "A stack is a LIFO collection: push adds on top, pop removes the top item."
    r = await g.client.put(
        f"/admin/content/chunks/{url_id}",
        headers=g.reviewer,
        json={"heading": "Overview", "text": new_text, "kind": "overview", "reviewed": True},
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["source"] == "admin" and out["embedded"] is True and out["reviewed"] is True
    assert out["warning"] is None
    graph_text = [c.text for c in await g.app.state.graph.repository().get_chunks([cid])]
    assert graph_text == [new_text]

    # the next seed from the (unchanged) notes file keeps the admin's version everywhere
    original = Chunk(id=chunk_id, concept_id=cid, subject_id=g.sid, kind="overview",
                     heading="Overview", text="A stack is a LIFO collection of items.", order=0,
                     reviewed=False)  # fmt: skip
    async with g.app.state.db.sessions()() as s, s.begin():
        await ContentRepository(s).upsert_chunks([original])
    assert (
        await g.env.db.fetchval("select text from content_chunks where id = $1", chunk_id)
        == new_text
    )
    await g.app.state.graph.repository().upsert_chunk(
        ChunkRecord(id=chunk_id, concept_id=cid, subject_id=g.sid, kind="overview",
                    heading="Overview", text=original.text)
    )  # fmt: skip
    assert [c.text for c in await g.app.state.graph.repository().get_chunks([cid])] == [new_text]

    flag = await g.client.patch(f"/admin/content/chunks/{url_id}", headers=g.reviewer,
                                json={"reviewed": False})  # fmt: skip
    assert flag.status_code == 200 and flag.json()["reviewed"] is False
    actions = {r["action"] for r in await g.env.db.fetch("select action from audit_log")}
    assert {"content.edit_chunk", "content.review_chunk"} <= actions


@requires_postgres
@requires_neo4j
async def test_question_validation_flags_and_reseed(genv: GEnv) -> None:  # noqa: F811
    g = genv
    cid, _, qid = await seed_content(g)
    three = {**MCQ, "options": MCQ["options"][:3]}
    r = await g.client.put(f"/admin/content/questions/{qid}", headers=g.reviewer, json=three)
    assert r.status_code == 422
    assert "exactly 4 options" in r.json()["error"]["message"]
    no_why = {**MCQ, "options": [{**o, "why_wrong": None} for o in MCQ["options"]]}
    r = await g.client.put(f"/admin/content/questions/{qid}", headers=g.reviewer, json=no_why)
    assert r.status_code == 422 and "why_wrong" in r.json()["error"]["message"]
    bad_prereq = {**MCQ, "diagnoses_prereq": f"{g.sid}_nope"}
    r = await g.client.put(f"/admin/content/questions/{qid}", headers=g.reviewer, json=bad_prereq)
    assert r.status_code == 422

    edited = {**MCQ, "prompt": "Which structure removes the newest item first?", "reviewed": True}
    r = await g.client.put(f"/admin/content/questions/{qid}", headers=g.reviewer, json=edited)
    assert r.status_code == 200, r.text
    assert r.json()["source"] == "admin" and r.json()["reviewed"] is True
    r = await g.client.patch(f"/admin/content/questions/{qid}", headers=g.reviewer,
                             json={"status": "inactive"})  # fmt: skip
    assert r.json()["status"] == "inactive"

    async with g.app.state.db.sessions()() as s, s.begin():  # seed the file version again
        await ContentRepository(s).upsert_questions([(g.sid, cid, Question(id=qid, **MCQ))])
    row = await g.env.db.fetchrow("select prompt, status, source from questions where id = $1", qid)
    assert dict(row) == {"prompt": edited["prompt"], "status": "inactive", "source": "admin"}

    view = (await g.client.get(f"/admin/content/concepts/{cid}", headers=g.reviewer)).json()
    q = view["questions"][0]
    assert q["id"] == qid and q["stats"] == {
        "attempts": 0, "pct_correct": None, "discrimination": None, "flags": []
    }  # fmt: skip


def test_item_stats_flags_easy_hard_and_weak_items() -> None:
    strong = [uuid.UUID(int=i) for i in range(1, 13)]
    weak = [uuid.UUID(int=i) for i in range(101, 113)]
    accuracy = {u: 0.9 for u in strong} | {u: 0.3 for u in weak}
    answers = (
        [("easy", u, True) for u in strong + weak]
        + [("hard", u, False) for u in strong + weak]
        + [("good", u, True) for u in strong] + [("good", u, False) for u in weak]
        + [("flat", u, i % 2 == 0) for i, u in enumerate(strong + weak)]
    )  # fmt: skip
    s = item_stats(answers, accuracy)
    assert s["easy"]["flags"] == ["too_easy"] and s["easy"]["pct_correct"] == 1.0
    assert s["hard"]["flags"] == ["too_hard"]
    assert s["good"]["discrimination"] == 1.0 and s["good"]["flags"] == []
    assert s["flat"]["discrimination"] == 0.0 and s["flat"]["flags"] == ["low_discrimination"]
    few = item_stats([("q", strong[0], True)], {strong[0]: 1.0})
    assert few["q"] == {"attempts": 1, "pct_correct": 1.0, "discrimination": None, "flags": []}
