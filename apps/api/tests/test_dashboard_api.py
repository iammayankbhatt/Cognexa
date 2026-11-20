# ruff: noqa: F811  (pytest fixtures imported from other test modules)
"""Dashboard aggregation, knowledge-map graph, notes listing (API + RLS) and revision sheets."""

from __future__ import annotations

import json
import uuid
from typing import Any

from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401
from tests.test_db_migrations import as_user
from tests.test_recommender_api import take_concept_quiz
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
N_CONCEPTS = len(_GRAPH.concepts)


async def get(t: TEnv, h: dict[str, str], path: str, **params: Any) -> Any:
    r = await t.client.get(path, headers=h, params=params)
    assert r.status_code == 200, r.text
    return r.json()


async def test_dashboard_for_a_new_learner(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    d = await get(tenv, h, "/dashboard")
    assert d["concepts_total"] == N_CONCEPTS and d["concepts_practised"] == 0
    assert d["overall_mastery"] == 0 and d["bands"]["not_started"] == N_CONCEPTS
    assert d["streak_days"] == 0 and d["quizzes_this_week"] == 0 and d["activity"] == []
    assert len(d["accuracy_trend"]) == 30 and all(
        x["accuracy"] is None for x in d["accuracy_trend"]
    )
    assert d["recommendations"]["items"][0]["rule"] == "R5"
    assert {c["cluster"] for c in d["per_cluster"]} >= {"foundations", "trees"}
    assert d["usage_today"] == {"ai_requests": 0, "daily_quota": 40}
    assert (await tenv.client.get("/dashboard")).status_code == 401


async def test_dashboard_after_practice(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    await take_concept_quiz(tenv, h, "stack", correct=True)
    await take_concept_quiz(tenv, h, "queue", correct=False)
    await take_concept_quiz(tenv, h, "queue", correct=False)
    thread = await new_thread(tenv, h)
    await ask(tenv, h, thread, "explain binary search")
    d = await get(tenv, h, "/dashboard")
    assert d["concepts_practised"] >= 2 and d["quizzes_this_week"] == 3
    assert d["tutor_questions_this_week"] == 1 and d["streak_days"] == 1
    assert (
        d["accuracy_trend"][-1]["accuracy"] is not None and d["accuracy_trend"][-1]["answers"] > 0
    )
    kinds = [a["kind"] for a in d["activity"]]
    assert "quiz" in kinds and "question" in kinds
    assert d["review_due"] == 0 and d["time_on_task_minutes_7d"] >= 1
    weak = [w["concept_id"] for w in d["weak_concepts"]]
    assert "queue" in weak
    stack_band = sum(d["bands"].values())
    assert stack_band == N_CONCEPTS
    assert 0 < d["overall_mastery"] < 1


async def test_graph_mastery_shape(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    await take_concept_quiz(tenv, h, "stack", correct=True)
    g = await get(tenv, h, "/graph/mastery")
    assert len(g["nodes"]) == N_CONCEPTS
    by_id = {n["id"]: n for n in g["nodes"]}
    assert by_id["stack"]["mastery"] > 0 and by_id["stack"]["band"] in (
        "weak",
        "developing",
        "strong",
    )
    assert by_id["bst"]["mastery"] is None and by_id["bst"]["band"] == "not_started"
    assert {"description", "difficulty", "cluster", "attempts"} <= set(by_id["stack"])
    types = {e["type"] for e in g["edges"]}
    assert types == {"PREREQUISITE_OF", "RELATED_TO"}
    prereq = [e for e in g["edges"] if e["type"] == "PREREQUISITE_OF"]
    assert len(prereq) == sum(len(p) for p in _GRAPH.prereqs_of.values())


async def test_notes_list_filters_delete_and_rls(tenv: TEnv) -> None:
    ada_id, ada = await tenv.env.user("ada@example.com")
    bob_id, bob = await tenv.env.user("bob@example.com")
    await tenv.client.put("/notes/recursion", headers=ada, json={"body": "Base case 100%!"})
    await tenv.client.put("/notes/bst", headers=ada, json={"bookmarked": True})
    await tenv.client.put("/notes/stack", headers=bob, json={"body": "bob's private note"})
    listing = await get(tenv, ada, "/notes")
    assert {n["concept_id"] for n in listing["items"]} == {"recursion", "bst"}
    assert (await get(tenv, ada, "/notes", bookmarked=True))["items"][0]["concept_id"] == "bst"
    assert [n["concept_id"] for n in (await get(tenv, ada, "/notes", q="100%"))["items"]] == [
        "recursion"
    ]
    assert (await get(tenv, ada, "/notes", q="_"))["total"] == 0  # LIKE wildcards are literal
    assert [
        n["concept_id"] for n in (await get(tenv, ada, "/notes", cluster="trees"))["items"]
    ] == ["bst"]
    assert (await get(tenv, ada, "/notes", q="recursion"))["items"][0]["name"] == "Recursion"
    assert (await tenv.client.delete("/notes/stack", headers=ada)).status_code == 404  # bob's
    assert (await tenv.client.delete("/notes/recursion", headers=ada)).status_code == 204
    assert (await get(tenv, ada, "/notes"))["total"] == 1
    # RLS: as the authenticated role, a user sees only their own rows
    async with as_user(tenv.env.db, ada_id):
        rows = await tenv.env.db.fetch("select user_id from notes")
        assert {r["user_id"] for r in rows} == {ada_id}
        assert (
            await tenv.env.db.fetchval("select count(*) from notes where user_id = $1", bob_id) == 0
        )


async def test_revision_sheet_with_fake_provider(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    _, bob = await tenv.env.user("bob@example.com")
    r = await tenv.client.post("/revision-sheets", headers=h, json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "nothing_to_revise"
    r = await tenv.client.post(
        "/revision-sheets", headers=h, json={"concept_ids": ["recursion", "nope"]}
    )
    assert r.status_code == 201, r.text
    sheet = r.json()
    assert sheet["concept_ids"] == ["recursion"] and sheet["content"]
    assert "recursion" in sheet["citations"] and sheet["names"]["recursion"] == "Recursion"
    calls = await tenv.env.db.fetch("select purpose from llm_calls where user_id = $1", uid)
    assert [c["purpose"] for c in calls] == ["revision"]

    # default concepts: the weak ones
    await take_concept_quiz(tenv, h, "queue", correct=False)
    await take_concept_quiz(tenv, h, "queue", correct=False)
    auto = (await tenv.client.post("/revision-sheets", headers=h, json={})).json()
    assert "queue" in auto["concept_ids"]

    listing = await get(tenv, h, "/revision-sheets")
    assert listing["total"] == 2
    one = await get(tenv, h, f"/revision-sheets/{sheet['id']}")
    assert one["content"] == sheet["content"]
    assert (
        await tenv.client.get(f"/revision-sheets/{sheet['id']}", headers=bob)
    ).status_code == 404
    assert (
        await tenv.client.delete(f"/revision-sheets/{sheet['id']}", headers=bob)
    ).status_code == 404
    assert (
        await tenv.client.delete(f"/revision-sheets/{sheet['id']}", headers=h)
    ).status_code == 204
    assert (await get(tenv, h, "/revision-sheets"))["total"] == 1
    for bad in ({"concept_ids": []}, {"concept_ids": ["a"] * 6}, {"x": 1}):
        assert (await tenv.client.post("/revision-sheets", headers=h, json=bad)).status_code == 422
    assert json.dumps(sheet)
    assert uuid.UUID(sheet["id"])
