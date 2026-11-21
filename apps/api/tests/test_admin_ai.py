"""Admin AI endpoints: usage dashboard, settings, LLM check; quota 429 over HTTP."""

from __future__ import annotations

from app.llm.errors import FatalLLMError
from app.llm.fake import FakeProvider
from app.llm.router import LLMRouter
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401

pytestmark = requires_postgres


async def test_admin_ai_endpoints_require_admin(env: Env) -> None:  # noqa: F811
    _, student = await env.user("s@example.com")
    for method, path in (("GET", "/admin/usage"), ("GET", "/admin/settings"),
                         ("PUT", "/admin/settings"), ("POST", "/admin/llm/check")):  # fmt: skip
        assert (await env.client.request(method, path)).status_code == 401
        r = await env.client.request(method, path, headers=student, json={})
        assert r.status_code == 403, (method, path)


async def test_llm_check_records_usage_and_shows_in_dashboard(env: Env) -> None:  # noqa: F811
    _, admin = await env.user("boss@example.com", role="admin")
    r = await env.client.post("/admin/llm/check", headers=admin, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "fake" and body["tokens_in"] > 0 and body["text"]
    assert body["providers"][0]["circuit_open"] is False

    usage = (await env.client.get("/admin/usage", headers=admin, params={"days": 7})).json()
    assert usage["totals"]["ai_requests"] == 1 and usage["totals"]["calls"] == 1
    assert usage["totals"]["cache_hit_rate"] == 0.0
    assert usage["by_model"][0]["provider"] == "fake" and usage["by_model"][0]["calls"] == 1
    assert usage["by_user"][0]["email"] == "boss@example.com"
    assert usage["by_day"][0]["ai_requests"] == 1 and usage["by_day"][0]["est_cost_usd"] > 0
    purpose = await env.db.fetchval("select purpose from llm_calls")
    assert purpose == "admin_check"
    assert (
        await env.client.get("/admin/usage", headers=admin, params={"days": 0})
    ).status_code == 422


async def test_settings_round_trip_validation_and_audit(env: Env) -> None:  # noqa: F811
    admin_id, admin = await env.user("boss@example.com", role="admin")
    view = (await env.client.get("/admin/settings", headers=admin)).json()
    assert view["quota"]["daily_ai_requests"] == 40
    assert view["features"] == {"AGENTIC_MODE": True, "STUDY_MODE": False,
                                "PLAIN_RAG_VISIBLE_TO_STUDENTS": False}  # fmt: skip
    assert view["providers"]["keys"] == {"groq": False, "gemini": False}  # booleans, never values

    patch = {
        "features": {"AGENTIC_MODE": False, "STUDY_MODE": True, "PLAIN_RAG_VISIBLE_TO_STUDENTS": False},
        "quota": {"daily_ai_requests": 10, "per_minute": 3, "max_input_chars": 1500,
                  "max_output_tokens": 600},
        "pricing": {"default": {"input_per_1m": 0.2, "output_per_1m": 0.6},
                    "models": {"fake-model": {"input_per_1m": 0, "output_per_1m": 0}}},
    }  # fmt: skip
    r = await env.client.put("/admin/settings", headers=admin, json=patch)
    assert r.status_code == 200, r.text
    after = r.json()
    assert after["features"]["STUDY_MODE"] is True and after["quota"]["per_minute"] == 3
    assert after["pricing"]["models"]["fake-model"]["input_per_1m"] == 0
    audit = await env.db.fetchrow("select actor, action, target from audit_log")
    assert (audit["actor"], audit["action"], audit["target"]) == (
        admin_id,
        "settings.update",
        "features,pricing,quota",
    )
    # students now see the new daily limit (admins get the x5 multiplier)
    _, student = await env.user("s@example.com")
    usage = (await env.client.get("/me/usage", headers=student)).json()
    assert usage["limits"]["daily_ai_requests"] == 10 and usage["limits"]["per_minute"] == 3

    for bad in (
        {},
        {"quota": {"daily_ai_requests": -1, "per_minute": 3, "max_input_chars": 1500,
                   "max_output_tokens": 600}},
        {"cache": {"enabled": True}},
        {"unknown": {}},
        {"features": {"AGENTIC_MODE": True, "STUDY_MODE": False,
                      "PLAIN_RAG_VISIBLE_TO_STUDENTS": False, "EXTRA": True}},
    ):  # fmt: skip
        assert (await env.client.put("/admin/settings", headers=admin, json=bad)).status_code == 422


async def test_quota_429_envelope_over_http(env: Env) -> None:  # noqa: F811
    admin_id, admin = await env.user("boss@example.com", role="admin")
    await env.db.execute(
        "update profiles set quota_override = '{\"daily_ai_requests\": 1}' where id = $1", admin_id
    )
    assert (await env.client.post("/admin/llm/check", headers=admin, json={})).status_code == 200
    r = await env.client.post("/admin/llm/check", headers=admin, json={})
    assert r.status_code == 429
    err = r.json()["error"]
    assert err["code"] == "QUOTA_EXCEEDED" and err["request_id"]
    assert err["details"]["reset_at"].endswith("+00:00") and int(r.headers["retry-after"]) >= 1


async def test_failed_model_call_is_502_and_refunded(env: Env) -> None:  # noqa: F811
    _, admin = await env.user("boss@example.com", role="admin")
    app = env.client._transport.app  # type: ignore[attr-defined]
    app.state.llm = LLMRouter([FakeProvider(script=[FatalLLMError("bad key", status=401)])])
    r = await env.client.post("/admin/llm/check", headers=admin, json={})
    assert r.status_code == 502 and r.json()["error"]["code"] == "llm_unavailable"
    assert await env.db.fetchval("select coalesce(sum(ai_requests), 0) from usage_daily") == 0
    assert await env.db.fetchval("select count(*) from llm_calls") == 0


async def test_me_reports_tutor_modes_from_role_and_flag(env: Env) -> None:  # noqa: F811
    """BUG-057: PLAIN_RAG_VISIBLE_TO_STUDENTS was enforced by the API but the web could not know
    it, so turning it on changed nothing for students."""
    _, admin = await env.user("boss@example.com", role="admin")
    _, student = await env.user("ada@example.com")
    assert (await env.client.get("/me", headers=student)).json()["tutor_modes"] == ["graphrag"]
    assert (await env.client.get("/me", headers=admin)).json()["tutor_modes"] == [
        "graphrag",
        "plain_rag",
    ]
    r = await env.client.put(
        "/admin/settings",
        headers=admin,
        json={"features": {"AGENTIC_MODE": True, "STUDY_MODE": False,
                           "PLAIN_RAG_VISIBLE_TO_STUDENTS": True}},
    )  # fmt: skip
    assert r.status_code == 200, r.text
    me = (await env.client.get("/me", headers=student)).json()
    assert me["tutor_modes"] == ["graphrag", "plain_rag"]
