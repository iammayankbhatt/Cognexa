# ruff: noqa: F811  (pytest fixtures imported from other test modules)
"""Quiz, mastery and Learn API over HTTP (throwaway Postgres seeded with the real DSA content,
in-memory graph, FakeProvider as the judge)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.llm.errors import FatalLLMError
from app.llm.fake import FakeProvider
from app.llm.router import LLMRouter
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401
from tests.test_tutor_api import (  # noqa: F401
    _GRAPH,
    TEnv,
    ask,
    fresh_db_url,
    new_thread,
    seeded_template,
    tenv,
)

pytestmark = requires_postgres


async def no_sleep(_: float) -> None:
    return None


def set_judge(t: TEnv, *providers: FakeProvider) -> None:
    t.app.state.judge_llm = LLMRouter(list(providers), sleep=no_sleep)


async def answer_key(t: TEnv, qid: str) -> Any:
    raw = await t.env.db.fetchval("select answer from questions where id = $1", qid)
    return json.loads(raw)


async def start(t: TEnv, h: dict[str, str], **body: Any) -> dict[str, Any]:
    r = await t.client.post("/quiz/sessions", headers=h, json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def mastery_of(t: TEnv, uid: uuid.UUID, concept: str) -> dict[str, Any] | None:
    row = await t.env.db.fetchrow(
        "select score, attempts, correct, last_practiced_at from mastery "
        "where user_id = $1 and concept_id = $2",
        uid,
        concept,
    )
    return dict(row) if row else None


async def test_concept_quiz_immediate_feedback_updates_mastery(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    s = await start(tenv, h, mode="concept", concept_id="stack", count=5)
    assert s["mode"] == "concept" and len(s["questions"]) == 5 and s["feedback_mode"] == "immediate"
    first = s["questions"][0]
    assert "answer" not in first or first["answer"] is None
    assert all("why_wrong" not in o for o in first["options"] or [])
    raw = json.dumps(s)
    for qid in (q["id"] for q in s["questions"]):
        key = await answer_key(tenv, qid)
        # the stored answer key never appears in the session payload
        assert f'"answer": {json.dumps(key)}' not in raw

    auto = [q for q in s["questions"] if q["type"] != "short_answer"]
    q0 = auto[0]
    key = await answer_key(tenv, q0["id"])
    r = await tenv.client.post(
        f"/quiz/sessions/{s['id']}/answers", headers=h,
        json={"question_id": q0["id"], "response": key, "time_ms": 4200},
    )  # fmt: skip
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["score"] == 1.0 and a["is_correct"] is True and a["correct_answer"] == key
    assert a["feedback"]
    m = await mastery_of(tenv, uid, "stack")
    assert m is not None and m["attempts"] == 1 and float(m["score"]) > 0
    again = await tenv.client.post(f"/quiz/sessions/{s['id']}/answers", headers=h,
                                   json={"question_id": q0["id"], "response": key})  # fmt: skip
    assert again.status_code == 409

    r = await tenv.client.post(f"/quiz/sessions/{s['id']}/submit", headers=h, json={})
    done = r.json()
    assert done["submitted_at"] and done["max_score"] == 5 and done["score"] >= 1
    assert all(q["explanation"] for q in done["questions"])
    assert done["per_concept"][0]["concept_id"] == "stack"
    hist = (await tenv.client.get("/quiz/history", headers=h)).json()
    assert hist["total"] == 1 and hist["items"][0]["concept_name"]
    view = (await tenv.client.get(f"/quiz/sessions/{s['id']}", headers=h)).json()
    assert view["score"] == done["score"]


async def test_exam_mode_grades_on_submit_and_reveals_nothing_before(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    s = await start(tenv, h, mode="concept", concept_id="queue", count=4, feedback_mode="exam")
    qs = [q for q in s["questions"] if q["type"] != "short_answer"]
    k0 = await answer_key(tenv, qs[0]["id"])
    r = await tenv.client.post(f"/quiz/sessions/{s['id']}/answers", headers=h,
                               json={"question_id": qs[0]["id"], "response": k0})  # fmt: skip
    assert r.json() == {"question_id": qs[0]["id"], "saved": True}
    mid = (await tenv.client.get(f"/quiz/sessions/{s['id']}", headers=h)).json()
    a0 = next(q for q in mid["questions"] if q["id"] == qs[0]["id"])["answer"]
    assert set(a0) == {"question_id", "response"}  # no score before submit
    assert await mastery_of(tenv, uid, "queue") is None

    responses = {q["id"]: await answer_key(tenv, q["id"]) for q in qs[1:]}
    done = (
        await tenv.client.post(
            f"/quiz/sessions/{s['id']}/submit", headers=h, json={"responses": responses}
        )
    ).json()
    graded = {q["id"]: q["answer"] for q in done["questions"]}
    assert all(graded[q["id"]]["score"] == 1.0 for q in qs)
    m = await mastery_of(tenv, uid, "queue")
    assert m is not None and m["attempts"] == len(s["questions"])
    # submitting again is idempotent
    again = (await tenv.client.post(f"/quiz/sessions/{s['id']}/submit", headers=h, json={})).json()
    assert again["score"] == done["score"]
    assert (await mastery_of(tenv, uid, "queue"))["attempts"] == m["attempts"]  # type: ignore[index]


async def test_wrong_answer_penalises_the_diagnosed_prerequisite(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    await tenv.env.db.execute(
        "insert into mastery (user_id, concept_id, subject_id, score, attempts, correct) "
        "values ($1, 'call_stack', 'dsa', 0.5, 3, 2)",
        uid,
    )
    qid = await tenv.env.db.fetchval(
        "select id from questions where concept_id = 'recursion' and type = 'mcq' "
        "and diagnoses_prereq = 'call_stack' order by id limit 1"
    )
    sid = (await start(tenv, h, mode="concept", concept_id="recursion", count=20))["id"]
    await tenv.env.db.execute(
        "update quiz_sessions set question_ids = array[$1]::text[] where id = $2",
        qid,
        uuid.UUID(sid),
    )
    key = await answer_key(tenv, qid)
    wrong = next(o for o in "abcd" if o != key)
    a = (
        await tenv.client.post(
            f"/quiz/sessions/{sid}/answers", headers=h, json={"question_id": qid, "response": wrong}
        )
    ).json()
    assert a["score"] == 0.0 and a["diagnoses_prereq"] == "call_stack"
    assert a["diagnoses_prereq_name"] == "Function Calls & the Call Stack"
    assert "needs review" in a["feedback"]
    cs = await mastery_of(tenv, uid, "call_stack")
    assert float(cs["score"]) == 0.45 and cs["attempts"] == 3  # type: ignore[index]
    rec = await mastery_of(tenv, uid, "recursion")
    assert float(rec["score"]) == 0.0 and rec["attempts"] == 1  # type: ignore[index]


async def test_short_answer_judge_usage_cache_pending_and_regrade(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    qid = await tenv.env.db.fetchval(
        "select id from questions where type = 'short_answer' and concept_id = 'call_stack' limit 1"
    )
    rubric = json.loads(
        await tenv.env.db.fetchval("select rubric from questions where id = $1", qid)
    )
    good = " and ".join(rubric["key_points"])

    async def session_with(question: str) -> str:
        sid = (await start(tenv, h, mode="concept", concept_id="call_stack", count=3))["id"]
        await tenv.env.db.execute(
            "update quiz_sessions set question_ids = array[$1]::text[] where id = $2",
            question, uuid.UUID(sid),
        )  # fmt: skip
        return str(sid)

    set_judge(tenv, FakeProvider())
    sid = await session_with(qid)
    a = (await tenv.client.post(f"/quiz/sessions/{sid}/answers", headers=h,
                                json={"question_id": qid, "response": good})).json()  # fmt: skip
    assert a["score"] == 1.0 and a["pending"] is False and a["matched_points"]
    calls = await tenv.env.db.fetch("select purpose, cached from llm_calls where user_id = $1", uid)
    assert [(c["purpose"], c["cached"]) for c in calls] == [("grading", False)]
    graded_by = await tenv.env.db.fetchval(
        "select graded_by from quiz_answers where session_id = $1", uuid.UUID(sid)
    )
    assert graded_by == "llm"

    # same answer again: served from the grading cache (still one request, no tokens)
    sid2 = await session_with(qid)
    await tenv.client.post(f"/quiz/sessions/{sid2}/answers", headers=h,
                           json={"question_id": qid, "response": good})  # fmt: skip
    cached = await tenv.env.db.fetchval(
        "select count(*) from llm_calls where user_id = $1 and cached", uid
    )
    assert cached == 1

    # judge down: the answer is kept as pending and submission still works
    set_judge(tenv, FakeProvider(script=[FatalLLMError("down", status=500)] * 6))
    sid3 = await session_with(qid)
    p = (await tenv.client.post(f"/quiz/sessions/{sid3}/answers", headers=h,
                                json={"question_id": qid, "response": "a new answer"})).json()  # fmt: skip
    assert p["pending"] is True and p["score"] is None
    done = (await tenv.client.post(f"/quiz/sessions/{sid3}/submit", headers=h, json={})).json()
    assert done["submitted_at"] and done["pending"] == 1
    # judge back: regrade fills the score in
    set_judge(tenv, FakeProvider())
    after = (await tenv.client.post(f"/quiz/sessions/{sid3}/regrade", headers=h)).json()
    assert after["pending"] == 0
    assert after["questions"][0]["answer"]["score"] is not None


async def test_timed_quiz_refuses_late_answers_but_allows_submit(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    s = await start(tenv, h, mode="concept", concept_id="arrays", count=3, timed=True)
    assert s["deadline"]
    await tenv.env.db.execute(
        "update quiz_sessions set started_at = now() - interval '1 hour' where id = $1",
        uuid.UUID(s["id"]),
    )
    q0 = s["questions"][0]
    r = await tenv.client.post(f"/quiz/sessions/{s['id']}/answers", headers=h,
                               json={"question_id": q0["id"], "response": None})  # fmt: skip
    assert r.status_code == 409 and r.json()["error"]["code"] == "time_up"
    done = (await tenv.client.post(f"/quiz/sessions/{s['id']}/submit", headers=h,
                                   json={"responses": {q0["id"]: "a"}})).json()  # fmt: skip
    assert done["score"] == 0  # late responses are ignored


async def test_diagnostic_seeds_mastery_across_clusters(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    s = await start(tenv, h, mode="diagnostic", feedback_mode="immediate")
    assert s["feedback_mode"] == "exam" and len(s["questions"]) == 10
    clusters = {_GRAPH.concepts[q["concept_id"]].cluster for q in s["questions"]}
    assert len(clusters) == 8
    responses = {q["id"]: await answer_key(tenv, q["id"]) for q in s["questions"][:6]}
    await tenv.client.post(f"/quiz/sessions/{s['id']}/submit", headers=h,
                           json={"responses": responses})  # fmt: skip
    rows = await tenv.env.db.fetchval(
        "select count(*) from mastery where user_id = $1 and attempts > 0", uid
    )
    assert rows == len({q["concept_id"] for q in s["questions"]})
    m = (await tenv.client.get("/me/mastery", headers=h)).json()
    assert len([i for i in m["items"] if i["attempts"]]) == rows
    assert {i["band"] for i in m["items"]} <= {"weak", "developing", "strong"}


async def test_adaptive_review_and_study_forms(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    await tenv.env.db.execute(
        "insert into mastery (user_id, concept_id, subject_id, score, attempts, correct, "
        "last_practiced_at) values ($1, 'bst', 'dsa', 0.2, 4, 1, now()), "
        "($1, 'binary_heap', 'dsa', 0.95, 4, 4, now())",
        uid,
    )
    s = await start(tenv, h, mode="adaptive", count=6)
    concepts = {q["concept_id"] for q in s["questions"]}
    assert "bst" in concepts and "binary_heap" not in concepts
    bst_q = [q for q in s["questions"] if q["concept_id"] == "bst"]
    assert all(q["difficulty"] == 1 for q in bst_q)

    r = await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "review"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "nothing_due"
    await tenv.env.db.execute(
        "update mastery set next_review_at = now() - interval '1 day' where concept_id = 'bst' "
        "and user_id = $1",
        uid,
    )
    review = await start(tenv, h, mode="review", count=3)
    assert {q["concept_id"] for q in review["questions"]} == {"bst"}

    # Study forms: a student takes the pre-test once the study is running and they consented
    # (Phase 12 gating; the gating itself is tested in test_study_api.py).
    _, admin = await tenv.env.user("boss@example.com", role="admin")
    r = await tenv.client.put("/admin/study", headers=admin, json={"enabled": True})
    assert r.status_code == 200
    assert (await tenv.client.post("/study/consent", headers=h)).status_code == 200
    pre = await start(tenv, h, mode="pretest")
    assert len(pre["questions"]) == 20 and pre["questions"][0]["id"] == "call_stack-q01"
    assert pre["feedback_mode"] == "exam" and pre["deadline"]


async def test_quiz_validation_and_isolation(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    _, bob = await tenv.env.user("bob@example.com")
    r = await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "concept"})
    assert r.status_code == 422
    r = await tenv.client.post("/quiz/sessions", headers=h,
                               json={"mode": "concept", "concept_id": "no_such_concept"})  # fmt: skip
    assert r.status_code == 404
    for bad in ({"mode": "nope"}, {"mode": "concept", "count": 50}, {"mode": "concept", "x": 1}):
        assert (await tenv.client.post("/quiz/sessions", headers=h, json=bad)).status_code == 422
    s = await start(tenv, h, mode="concept", concept_id="stack", count=3)
    mcq = next((q for q in s["questions"] if q["type"] == "mcq"), None)
    if mcq is not None:
        r = await tenv.client.post(f"/quiz/sessions/{s['id']}/answers", headers=h,
                                   json={"question_id": mcq["id"], "response": "z"})  # fmt: skip
        assert r.status_code == 422
    r = await tenv.client.post(f"/quiz/sessions/{s['id']}/answers", headers=h,
                               json={"question_id": "bst-q01", "response": "a"})  # fmt: skip
    assert r.status_code == 404
    assert (await tenv.client.get(f"/quiz/sessions/{s['id']}", headers=bob)).status_code == 404
    r = await tenv.client.post(f"/quiz/sessions/{s['id']}/submit", headers=bob, json={})
    assert r.status_code == 404
    assert (await tenv.client.get("/quiz/history")).status_code == 401


async def test_concept_page_and_interest_logging(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    r = await tenv.client.get("/concepts/recursion", headers=h)
    assert r.status_code == 200, r.text
    page = r.json()
    assert page["name"] == "Recursion" and page["description"]
    kinds = [s["kind"] for s in page["sections"]]
    assert kinds[0] == "overview" and "code" in kinds and len(kinds) == 10
    assert [p["id"] for p in page["prerequisites"]] == ["call_stack"]
    assert {"backtracking", "divide_and_conquer"} <= {c["id"] for c in page["related"]}
    assert page["leads_to"] and page["question_count"] >= 8 and page["mastery"] is None
    assert (await tenv.client.get("/concepts/nope_nope", headers=h)).status_code == 404
    assert (await tenv.client.get("/concepts/Bad-Id", headers=h)).status_code == 422

    # a tutor question logs its matched concepts for the recommender
    thread = await new_thread(tenv, h)
    await ask(tenv, h, thread, "explain binary search")
    logged = await tenv.env.db.fetch(
        "select concept_id, source from concept_interest where user_id = $1", uid
    )
    assert ("binary_search", "tutor") in {(r["concept_id"], r["source"]) for r in logged}


async def test_retry_wrong_ones_with_a_question_list(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    s = await start(
        tenv, h, mode="concept", question_ids=["bst-q01", "stack-q02", "bst-q01", "nope"]
    )
    assert [q["id"] for q in s["questions"]] == ["bst-q01", "stack-q02"]
    r = await tenv.client.post(
        "/quiz/sessions", headers=h, json={"mode": "adaptive", "question_ids": ["bst-q01"]}
    )
    assert r.status_code == 422


async def test_note_and_bookmark_per_concept_are_private(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    _, bob = await tenv.env.user("bob@example.com")
    empty = (await tenv.client.get("/notes/recursion", headers=h)).json()
    assert empty == {"concept_id": "recursion", "body": "", "bookmarked": False, "updated_at": None}
    r = await tenv.client.put("/notes/recursion", headers=h, json={"bookmarked": True})
    assert r.json()["bookmarked"] is True and r.json()["body"] == ""
    r = await tenv.client.put("/notes/recursion", headers=h, json={"body": "Base case first!"})
    assert r.json() == {**r.json(), "body": "Base case first!", "bookmarked": True}
    assert (await tenv.client.get("/notes/recursion", headers=bob)).json()["body"] == ""
    assert (await tenv.client.put("/notes/recursion", headers=h, json={})).status_code == 422
    assert (
        await tenv.client.put("/notes/nope_x", headers=h, json={"body": "x"})
    ).status_code == 404
    long = {"body": "x" * 20001}
    assert (await tenv.client.put("/notes/recursion", headers=h, json=long)).status_code == 422
