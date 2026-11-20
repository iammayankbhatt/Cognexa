# ruff: noqa: F811  (pytest fixtures imported from other test modules)
"""User-study mode: assignment, consent → pretest → learning → posttest, gating, export."""

from __future__ import annotations

import csv
import io
import json
import re
import uuid
from typing import Any

import asyncpg
import pytest

from app.study.service import gain, participant_id, pick_group
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401
from tests.test_db_migrations import as_user
from tests.test_tutor_api import (  # noqa: F401
    TEnv,
    fresh_db_url,
    new_thread,
    seeded_template,
    tenv,
)


def test_group_assignment_balances_and_alternates() -> None:
    assert pick_group({"adaptive": 3, "baseline": 2}, "random") == "baseline"
    assert pick_group({"adaptive": 1, "baseline": 4}, "random") == "adaptive"
    assert pick_group({}, "random", rng=lambda: 0.1) == "adaptive"
    assert pick_group({}, "random", rng=lambda: 0.9) == "baseline"
    assert [pick_group({"adaptive": n // 2 + n % 2, "baseline": n // 2}, "alternate") for n in range(4)] == [
        "adaptive", "baseline", "adaptive", "baseline",
    ]  # fmt: skip
    assert gain(8, 14, 20) == 0.5 and gain(20, 20, 20) is None and gain(None, 3, 20) is None
    pid = participant_id("salt", uuid.UUID(int=1))
    assert re.fullmatch(r"[0-9a-f]{16}", pid) and pid != participant_id("other", uuid.UUID(int=1))


pytestmark = requires_postgres


async def study_on(t: TEnv) -> dict[str, str]:
    _, admin = await t.env.user(f"admin-{uuid.uuid4().hex[:6]}@example.com", role="admin")
    r = await t.client.put(
        "/admin/study", headers=admin, json={"enabled": True, "assignment": "random"}
    )
    assert r.status_code == 200, r.text
    return admin


async def me(t: TEnv, h: dict[str, str]) -> dict[str, Any]:
    r = await t.client.get("/study/me", headers=h)
    assert r.status_code == 200, r.text
    return dict(r.json())


async def answer_all(
    t: TEnv, h: dict[str, str], session: dict[str, Any], correct: int
) -> dict[str, Any]:
    responses: dict[str, Any] = {}
    for i, q in enumerate(session["questions"]):
        key = json.loads(
            await t.env.db.fetchval("select answer from questions where id = $1", q["id"])
        )
        if i < correct:
            responses[q["id"]] = key
    r = await t.client.post(
        f"/quiz/sessions/{session['id']}/submit", headers=h, json={"responses": responses}
    )
    assert r.status_code == 200, r.text
    return dict(r.json())


async def test_full_study_flow_with_gating(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("stu@example.com")
    assert (await me(tenv, h))["step"] == "off"
    admin = await study_on(tenv)
    state = await me(tenv, h)
    assert state["step"] == "consent" and state["group"] == "none"

    # the tests are not available before consent
    r = await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "pretest"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_available"

    state = (await tenv.client.post("/study/consent", headers=h)).json()
    assert state["step"] == "pretest" and state["group"] in ("adaptive", "baseline")
    group = state["group"]
    assert (await tenv.client.post("/study/consent", headers=h)).json()[
        "group"
    ] == group  # idempotent

    r = await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "posttest"})
    assert r.status_code == 409
    pre = (
        await tenv.client.post(
            "/quiz/sessions", headers=h, json={"mode": "pretest", "feedback_mode": "immediate"}
        )
    ).json()
    assert len(pre["questions"]) == 20 and pre["deadline"] and pre["feedback_mode"] == "exam"
    again = (await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "pretest"})).json()
    assert again["id"] == pre["id"]  # an open test is resumed, not restarted

    # the tutor is paused while a study test is open
    thread = await new_thread(tenv, h)
    r = await tenv.client.post(
        f"/tutor/threads/{thread}/messages", headers=h, json={"content": "what is a stack"}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "test_in_progress"

    await answer_all(tenv, h, pre, correct=8)
    state = await me(tenv, h)
    assert state["step"] == "learning" and state["pretest"]["score"] == 8
    r = await tenv.client.post(
        f"/tutor/threads/{thread}/messages", headers=h, json={"content": "what is a stack"}
    )
    assert r.status_code == 200
    assert (
        await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "pretest"})
    ).status_code == 409

    # posttest unlocks by admin date
    r = await tenv.client.put(
        "/admin/study", headers=admin, json={"posttest_unlock_at": "2020-01-01T00:00:00Z"}
    )
    assert r.status_code == 200
    assert (await me(tenv, h))["step"] == "posttest"
    post = (await tenv.client.post("/quiz/sessions", headers=h, json={"mode": "posttest"})).json()
    assert {q["id"] for q in post["questions"]}.isdisjoint({q["id"] for q in pre["questions"]})
    await answer_all(tenv, h, post, correct=14)
    assert (await me(tenv, h))["step"] == "complete"

    view = (await tenv.client.get("/admin/study", headers=admin)).json()
    assert view["enabled"] is True and view["funnel"][group] == {
        "enrolled": 1,
        "pretest": 1,
        "posttest": 1,
    }

    r = await tenv.client.get("/admin/study/export.csv", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 1 and rows[0]["group"] == group
    assert float(rows[0]["normalized_gain"]) == pytest.approx((14 - 8) / (20 - 8), abs=1e-4)
    assert "stu@example.com" not in r.text and str(uid) not in r.text
    assert re.fullmatch(r"[0-9a-f]{16}", rows[0]["participant"])
    assert int(rows[0]["tutor_questions"]) == 1
    audit = await tenv.env.db.fetchval(
        "select count(*) from audit_log where action = 'study.update'"
    )
    assert audit == 2


async def test_balancing_withdrawal_and_permissions(tenv: TEnv) -> None:
    admin = await study_on(tenv)
    users = [await tenv.env.user(f"p{i}@example.com") for i in range(6)]
    groups = [
        (await tenv.client.post("/study/consent", headers=h)).json()["group"] for _, h in users
    ]
    assert groups.count("adaptive") == 3 and groups.count("baseline") == 3

    _, h0 = users[0]
    state = (await tenv.client.post("/study/withdraw", headers=h0)).json()
    assert state["step"] == "withdrawn" and state["group"] == "none"
    funnel = (await tenv.client.get("/admin/study", headers=admin)).json()["funnel"]
    assert funnel["withdrawn"] == {"count": 1}
    assert sum(funnel[g]["enrolled"] for g in ("adaptive", "baseline")) == 5
    rows = list(
        csv.DictReader(
            io.StringIO((await tenv.client.get("/admin/study/export.csv", headers=admin)).text)
        )
    )
    assert len(rows) == 5

    _, student = users[1]
    for method, path in (
        ("GET", "/admin/study"),
        ("PUT", "/admin/study"),
        ("GET", "/admin/study/export.csv"),
    ):
        r = await tenv.client.request(
            method, path, headers=student, json={} if method == "PUT" else None
        )
        assert r.status_code == 403
    assert (
        await tenv.client.put("/admin/study", headers=admin, json={"posttest_after_days": 999})
    ).status_code == 422


async def test_students_cannot_change_their_study_fields(env: Env) -> None:
    uid, _ = await env.user("rls@example.com")
    async with as_user(env.db, uid):
        with pytest.raises(asyncpg.PostgresError, match="only be changed by the backend"):
            await env.db.execute("update profiles set study_consent_at = now() where id = $1", uid)
    async with as_user(env.db, uid):
        await env.db.execute("update profiles set theme = 'titanium-light' where id = $1", uid)
