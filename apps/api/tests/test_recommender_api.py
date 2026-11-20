# ruff: noqa: F811  (pytest fixtures imported from other test modules)
"""Recommendations, study-group routing, logging and spaced review over HTTP (seeded throwaway
Postgres, in-memory DSA graph)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from app.recommender.engine import ConceptInfo, Graph
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401
from tests.test_tutor_api import (  # noqa: F401
    _GRAPH,
    TEnv,
    fresh_db_url,
    seeded_template,
    tenv,
)

pytestmark = requires_postgres

GRAPH = Graph(
    [ConceptInfo(c.id, c.name, c.order_index) for c in _GRAPH.concepts.values()],
    [(a, b) for b, pres in _GRAPH.prereqs_of.items() for a in pres],
)
ORDER = GRAPH.topological()


async def set_mastery(t: TEnv, uid: uuid.UUID, rows: dict[str, tuple[float, int]]) -> None:
    for cid, (score, attempts) in rows.items():
        await t.env.db.execute(
            "insert into mastery (user_id, concept_id, subject_id, score, attempts, correct, "
            "last_practiced_at) values ($1, $2, 'dsa', $3, $4, 0, now())",
            uid, cid, score, attempts,
        )  # fmt: skip


async def recs(t: TEnv, h: dict[str, str], **params: Any) -> dict[str, Any]:
    r = await t.client.get("/recommendations", headers=h, params=params)
    assert r.status_code == 200, r.text
    return dict(r.json())


async def answer_key(t: TEnv, qid: str) -> Any:
    return json.loads(await t.env.db.fetchval("select answer from questions where id = $1", qid))


async def take_concept_quiz(
    t: TEnv, h: dict[str, str], concept: str, correct: bool
) -> dict[str, Any]:
    r = await t.client.post("/quiz/sessions", headers=h,
                            json={"mode": "concept", "concept_id": concept, "count": 5,
                                  "feedback_mode": "exam"})  # fmt: skip
    s = r.json()
    responses: dict[str, Any] = {}
    for q in s["questions"]:
        if q["type"] == "short_answer":
            continue
        key = await answer_key(t, q["id"])
        if correct:
            responses[q["id"]] = key
        elif q["type"] in ("mcq",):
            responses[q["id"]] = next(o["id"] for o in q["options"] if o["id"] != key)
        elif q["type"] == "true_false":
            responses[q["id"]] = not key
        else:
            responses[q["id"]] = None
    done = await t.client.post(f"/quiz/sessions/{s['id']}/submit", headers=h,
                               json={"responses": responses})  # fmt: skip
    return dict(done.json())


async def test_new_learner_gets_r5_and_logging_is_not_inflated(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    body = await recs(tenv, h)
    assert body["engine"] == "adaptive" and body["study_group"] == "none"
    assert [(i["rule"], i["concept_id"]) for i in body["items"]] == [("R5", ORDER[0])]
    again = await recs(tenv, h)
    assert again["items"][0]["id"] == body["items"][0]["id"]
    rows = await tenv.env.db.fetch(
        "select reason_code, surface, study_group from recommendations_log where user_id = $1", uid
    )
    assert [(r["reason_code"], r["surface"], r["study_group"]) for r in rows] == [
        ("R5", "dashboard", "none")
    ]
    # a different surface is logged separately
    await recs(tenv, h, surface="tutor")
    assert (
        await tenv.env.db.fetchval(
            "select count(*) from recommendations_log where user_id = $1", uid
        )
        == 2
    )


async def test_root_cause_repair_on_the_real_graph(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    strong = {c: (0.9, 4) for c in ORDER[: ORDER.index("call_stack")]}
    await set_mastery(
        tenv, uid,
        {**strong, "call_stack": (0.3, 3), "recursion": (0.3, 3), "dfs_tree_traversals": (0.2, 4)},
    )  # fmt: skip
    # a recent failure on tree traversals makes it the most important weak concept
    sid = await tenv.env.db.fetchval(
        "insert into quiz_sessions (user_id, subject_id, mode, question_ids) "
        "values ($1, 'dsa', 'concept', array['dfs_tree_traversals-q01']) returning id",
        uid,
    )
    await tenv.env.db.execute(
        "insert into quiz_answers (session_id, user_id, question_id, response, score, is_correct) "
        "values ($1, $2, 'dfs_tree_traversals-q01', '{\"value\": null}', 0, false)",
        sid, uid,
    )  # fmt: skip
    body = await recs(tenv, h)
    top = body["items"][0]
    assert (top["rule"], top["concept_id"], top["action"]) == ("R1", "call_stack", "learn")
    assert top["path"][0] == {"source": "call_stack", "target": "recursion"}
    assert top["path"][-1]["target"] == "dfs_tree_traversals"
    assert "start there" in top["reason"]
    assert top["names"]["recursion"] == "Recursion"
    logged = await tenv.env.db.fetchrow(
        "select path, reason_text from recommendations_log where id = $1", uuid.UUID(top["id"])
    )
    assert json.loads(logged["path"])[0]["source"] == "call_stack"


async def test_study_groups_get_different_engines_and_are_logged(tenv: TEnv) -> None:
    _, admin = await tenv.env.user("boss@example.com", role="admin")
    base_uid, base = await tenv.env.user("base@example.com")
    adap_uid, adap = await tenv.env.user("adap@example.com")
    for uid, group in ((base_uid, "baseline"), (adap_uid, "adaptive")):
        await tenv.env.db.execute("update profiles set study_group = $1 where id = $2", group, uid)
        await set_mastery(tenv, uid, {ORDER[0]: (0.2, 3)})  # weak on the very first concept

    # STUDY_MODE off: everyone gets the rule engine
    assert (await recs(tenv, base))["engine"] == "adaptive"
    settings = (await tenv.client.get("/admin/settings", headers=admin)).json()
    features = {**settings["features"], "STUDY_MODE": True}
    r = await tenv.client.put("/admin/settings", headers=admin, json={"features": features})
    assert r.status_code == 200

    b = await recs(tenv, base)
    a = await recs(tenv, adap)
    assert b["engine"] == "baseline" and {i["rule"] for i in b["items"]} == {"BASELINE"}
    assert (
        b["items"][0]["concept_id"] == min(_GRAPH.concepts.values(), key=lambda c: c.order_index).id
    )
    assert a["engine"] == "adaptive" and a["items"][0]["rule"] in ("R1", "R2")
    groups = await tenv.env.db.fetch(
        "select distinct study_group::text as g, reason_code from recommendations_log "
        "where user_id = any($1::uuid[])",
        [base_uid, adap_uid],
    )
    assert {(g["g"], g["reason_code"]) for g in groups} >= {("baseline", "BASELINE")}
    assert any(g["g"] == "adaptive" for g in groups)


async def test_click_and_completion_tracking(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    _, bob = await tenv.env.user("bob@example.com")
    first = (await recs(tenv, h))["items"][0]
    assert (
        await tenv.client.post(f"/recommendations/{first['id']}/click", headers=bob)
    ).status_code == 404
    assert (
        await tenv.client.post(f"/recommendations/{first['id']}/click", headers=h)
    ).status_code == 204
    row = await tenv.env.db.fetchrow(
        "select clicked_at, completed_at from recommendations_log where id = $1",
        uuid.UUID(first["id"]),
    )
    assert row["clicked_at"] is not None and row["completed_at"] is None
    await take_concept_quiz(tenv, h, first["concept_id"], correct=True)
    done = await tenv.env.db.fetchval(
        "select completed_at from recommendations_log where id = $1", uuid.UUID(first["id"])
    )
    assert done is not None
    assert (
        await tenv.client.post(f"/recommendations/{uuid.uuid4()}/click", headers=h)
    ).status_code == 404
    assert uid


async def test_spaced_review_schedule_due_queue_and_streak(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")

    async def interval(concept: str) -> tuple[int, Any]:
        row = await tenv.env.db.fetchrow(
            "select review_interval_days, next_review_at - now() as left_, ease from mastery "
            "where user_id = $1 and concept_id = $2",
            uid, concept,
        )  # fmt: skip
        return int(row["review_interval_days"]), row

    await take_concept_quiz(tenv, h, "stack", correct=True)
    days, row = await interval("stack")
    assert days == 1 and 0.9 < row["left_"].total_seconds() / 86400 <= 1.0
    await take_concept_quiz(tenv, h, "stack", correct=True)
    assert (await interval("stack"))[0] == 3
    await take_concept_quiz(tenv, h, "stack", correct=False)
    days, row = await interval("stack")
    assert days == 1 and float(row["ease"]) < 2.7

    empty = (await tenv.client.get("/review/due", headers=h)).json()
    assert empty["due"] == [] and empty["next_due_at"] and empty["streak_days"] == 1
    await tenv.env.db.execute(
        "update mastery set next_review_at = now() - interval '1 hour' "
        "where user_id = $1 and next_review_at is not null",
        uid,
    )
    due = (await tenv.client.get("/review/due", headers=h)).json()
    assert [d["concept_id"] for d in due["due"]] == ["stack"]
    assert 3 <= len(due["due"][0]["question_ids"]) <= 5
    review = await tenv.client.post(
        "/quiz/sessions", headers=h, json={"mode": "review", "count": 4}
    )
    assert review.status_code == 201
    top = (await recs(tenv, h))["items"]
    assert any(i["rule"] == "R3" and i["concept_id"] == "stack" for i in top)


async def test_tutor_suggestions_come_from_the_recommender(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    body = (await tenv.client.get("/tutor/suggestions", headers=h)).json()
    cont = body["continue"]
    assert cont["rule"] == "R5" and cont["concept_id"] == ORDER[0] and cont["id"]
    surface = await tenv.env.db.fetchval(
        "select surface from recommendations_log where id = $1", uuid.UUID(cont["id"])
    )
    assert surface == "tutor"
    assert uid


def test_streak_counting() -> None:
    import datetime as dt

    from app.api.recommendations import streak_days

    today = dt.date(2026, 11, 20)
    days = {today - dt.timedelta(days=i) for i in (0, 1, 2, 4)}
    assert streak_days(days, today) == 3
    assert streak_days(days - {today}, today) == 2  # nothing yet today: count from yesterday
    assert streak_days(set(), today) == 0
