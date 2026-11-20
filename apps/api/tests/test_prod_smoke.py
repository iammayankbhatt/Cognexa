"""scripts/prod_smoke.py logic, against a mocked API (no network)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "prod_smoke.py"


@pytest.fixture(scope="module")
def smoke() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prod_smoke", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["prod_smoke"] = module  # dataclasses look the module up while it executes
    spec.loader.exec_module(module)
    return module


def sse(*events: tuple[str, dict[str, Any]]) -> str:
    return "".join(f"event: {n}\ndata: {json.dumps(d)}\n\n" for n, d in events)


def test_parse_sse_handles_multiple_events_and_crlf(smoke: ModuleType) -> None:
    text = sse(("trace", {"concepts": [{"id": "call_stack"}]}), ("token", {"text": "Hi"}))
    lines = text.replace("\n", "\r\n").split("\n")
    assert smoke.parse_sse(lines) == [
        ("trace", {"concepts": [{"id": "call_stack"}]}),
        ("token", {"text": "Hi"}),
    ]


def test_error_envelope_shape(smoke: ModuleType) -> None:
    good = {"error": {"code": "unauthorized", "message": "m", "request_id": "r"}}
    assert smoke.is_error_envelope(good, "unauthorized")
    assert not smoke.is_error_envelope(good, "forbidden")
    assert not smoke.is_error_envelope({"detail": "Not authenticated"})


WEB = "https://cognexa.example.app"


def fake_api(*, deep_ok: bool = True, concept: str = "call_stack") -> httpx.MockTransport:
    usage = {"n": 3}

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if req.method == "OPTIONS":
            origin = req.headers.get("origin")
            headers = {"access-control-allow-origin": origin} if origin == WEB else {}
            return httpx.Response(200 if headers else 400, headers=headers)
        if path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/health/deep":
            dep = {"status": "ok" if deep_ok else "error", "latency_ms": 5}
            return httpx.Response(
                200,
                json={
                    "status": "ok" if deep_ok else "degraded",
                    "dependencies": {"postgres": dep, "neo4j": {"status": "ok"}},
                },
            )
        if path == "/graph":
            return httpx.Response(200, json={"nodes": [{}] * 69, "edges": [{}] * 131})
        if req.url.host == "cognexa.example.app":
            return httpx.Response(200, text="<title>Cognexa</title>")
        if path == "/auth/v1/token":
            return httpx.Response(200, json={"access_token": "tok"})
        if "authorization" not in req.headers:
            err = {"code": "unauthorized", "message": "Sign in", "request_id": "x"}
            return httpx.Response(401, json={"error": err})
        if path == "/me":
            return httpx.Response(200, json={"role": "student"})
        if path == "/me/usage":
            return httpx.Response(200, json={"today": {"ai_requests": usage["n"]}})
        if path == "/tutor/threads":
            return httpx.Response(201, json={"id": "t1"})
        if path == "/tutor/threads/t1/messages":
            usage["n"] += 1
            body = sse(
                ("trace", {"concepts": [{"id": "recursion"}, {"id": concept}]}),
                ("token", {"text": "a"}),
                ("done", {"id": "m1"}),
            )
            return httpx.Response(200, text=body)
        if path == "/tutor/threads/t1" and req.method == "DELETE":
            return httpx.Response(204)
        if path == "/recommendations":
            return httpx.Response(200, json={"items": []})
        if path == "/graph/mastery":
            return httpx.Response(200, json={"nodes": [{}] * 69})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


CREDS = {"email": "e", "password": "p", "supabase_url": "https://ref.supabase.co", "anon_key": "k"}


def run(smoke: ModuleType, transport: httpx.MockTransport, creds: Any = CREDS) -> list[Any]:
    with httpx.Client(transport=transport) as c:
        results: list[Any] = smoke.Smoke(c, "https://api.example", WEB).run(creds)
        return results


def test_all_checks_pass_on_a_healthy_deployment(smoke: ModuleType) -> None:
    results = run(smoke, fake_api())
    assert [r.name for r in results if not r.ok] == []
    assert len(results) == 11
    tutor = next(r for r in results if r.name.startswith("Tutor"))
    assert "call_stack in trace" in tutor.detail and "quota +1" in tutor.detail


def test_failures_are_reported_without_stopping_the_run(smoke: ModuleType) -> None:
    results = run(smoke, fake_api(deep_ok=False, concept="arrays"))
    failed = {r.name: r.detail for r in results if not r.ok}
    assert set(failed) == {"Deep health: Postgres + Neo4j", "Tutor: canonical recursion question"}
    assert "degraded" in failed["Deep health: Postgres + Neo4j"]
    assert "call_stack not in trace" in failed["Tutor: canonical recursion question"]


def test_signed_in_checks_are_marked_skipped_without_credentials(smoke: ModuleType) -> None:
    results = run(smoke, fake_api(), creds=None)
    assert results[-1].name == "Signed-in checks" and not results[-1].ok
    assert "skipped" in results[-1].detail
    report = smoke.render(results, "https://api.example", WEB)
    assert "6/7 checks passed" in report and "| FAIL |" in report
