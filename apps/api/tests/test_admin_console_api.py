"""Admin console (Phase 11): moderation queue, thumbs-down analytics, overview, a user's usage,
usage CSV and account disabling. Uses the tutor test environment (seeded DSA graph, fake LLM)."""

from __future__ import annotations

import csv
import io

from tests.conftest import requires_postgres
from tests.test_auth_api import env  # noqa: F401
from tests.test_tutor_api import TEnv, ask, fresh_db_url, last, new_thread, seeded_template, tenv  # noqa: F401

pytestmark = requires_postgres


async def reported_answer(t: TEnv) -> tuple[str, dict[str, str]]:
    uid, h = await t.env.user("ada@example.com")
    thread = await new_thread(t, h)
    done = last(await ask(t, h, thread, "What is a binary heap?"), "done")
    r = await t.client.post(
        f"/tutor/messages/{done['message_id']}/feedback",
        headers=h,
        json={"rating": -1, "report": {"reason": "incorrect", "comment": "heap order is wrong"}},
    )
    assert r.status_code == 200, r.text
    return str(uid), h


async def test_moderation_queue_and_analytics(tenv: TEnv) -> None:  # noqa: F811
    _, student = await reported_answer(tenv)
    _, reviewer = await tenv.env.user("rev@example.com", role="reviewer")
    assert (await tenv.client.get("/admin/reports", headers=student)).status_code == 403

    r = await tenv.client.get("/admin/reports", headers=reviewer)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["reason"] == "incorrect" and item["comment"] == "heap order is wrong"
    assert item["reporter"] == "ada@example.com" and item["status"] == "open"
    assert item["message"]["question"] == "What is a binary heap?"
    assert item["message"]["content"] and item["message"]["mode"] == "graphrag"
    assert "binary_heap" in {c["id"] for c in item["message"]["concepts"]}

    cache = await tenv.client.post(
        f"/admin/reports/{item['id']}/invalidate-cache", headers=reviewer
    )
    assert cache.status_code == 200 and cache.json()["had_cache_key"] is True

    act = await tenv.client.post(
        f"/admin/reports/{item['id']}",
        headers=reviewer,
        json={"status": "resolved", "note": "fixed the heap note"},
    )
    assert act.status_code == 200 and act.json()["status"] == "resolved"
    assert (await tenv.client.get("/admin/reports", headers=reviewer)).json()["total"] == 0
    resolved = await tenv.client.get(
        "/admin/reports", headers=reviewer, params={"status": "resolved"}
    )
    assert resolved.json()["items"][0]["resolution_note"] == "fixed the heap note"
    bad = await tenv.client.post(
        f"/admin/reports/{item['id']}", headers=reviewer, json={"status": "open"}
    )
    assert bad.status_code == 422

    by_concept = (await tenv.client.get("/admin/feedback/by-concept", headers=reviewer)).json()
    heap = next(i for i in by_concept["items"] if i["concept_id"] == "binary_heap")
    assert heap["thumbs_down"] == 1 and heap["reports"] == 1

    overview = (await tenv.client.get("/admin/overview", headers=reviewer)).json()
    assert overview["users"] == 2 and overview["dau"] == 1 and overview["wau"] == 1
    assert overview["ai_requests_today"] >= 1 and overview["global_cap"] > 0
    assert overview["open_reports"] == 0 and overview["pending_proposals"] == 0
    actions = {r["action"] for r in await tenv.env.db.fetch("select action from audit_log")}
    assert {"moderation.resolved", "moderation.invalidate_cache"} <= actions


async def test_user_usage_csv_and_disabling(tenv: TEnv) -> None:  # noqa: F811
    student_id, student = await reported_answer(tenv)
    admin_id, admin = await tenv.env.user("boss@example.com", role="admin")
    _, reviewer = await tenv.env.user("rev@example.com", role="reviewer")

    assert (
        await tenv.client.get(f"/admin/users/{student_id}/usage", headers=reviewer)
    ).status_code == 403
    usage = (await tenv.client.get(f"/admin/users/{student_id}/usage", headers=admin)).json()
    assert usage["totals"]["ai_requests"] >= 1
    assert usage["totals"]["tutor_questions"] == 1 and usage["totals"]["reports_filed"] == 1
    assert "content" not in str(usage)  # no chat text in the usage view

    r = await tenv.client.get("/admin/usage/export.csv", headers=admin)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert rows and {"date", "provider", "model", "calls", "est_cost_usd"} <= set(rows[0])
    assert sum(int(x["calls"]) for x in rows) >= 1

    off = await tenv.client.patch(
        f"/admin/users/{student_id}", headers=admin, json={"disabled": True}
    )
    assert off.status_code == 200 and off.json()["disabled_at"] is not None
    me = await tenv.client.get("/me", headers=student)
    assert me.status_code == 403 and me.json()["error"]["code"] == "account_disabled"
    on = await tenv.client.patch(
        f"/admin/users/{student_id}", headers=admin, json={"disabled": False}
    )
    assert on.json()["disabled_at"] is None
    assert (await tenv.client.get("/me", headers=student)).status_code == 200
    self_off = await tenv.client.patch(
        f"/admin/users/{admin_id}", headers=admin, json={"disabled": True}
    )
    assert self_off.status_code == 403
