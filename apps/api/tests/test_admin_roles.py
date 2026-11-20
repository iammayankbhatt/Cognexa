"""Role enforcement on EVERY admin endpoint (Phase 11 test list).

The routes are read from the app itself, so a new /admin route is covered automatically, and a
route that forgets its `require_role` dependency fails `test_every_admin_route_declares_a_role`.
"""

from __future__ import annotations

from app.core.config import Settings
from app.main import create_app
from tests.conftest import requires_postgres
from tests.route_walk import admin_routes, concrete
from tests.test_auth_api import Env, env  # noqa: F401


def test_every_admin_route_declares_a_role() -> None:
    routes = admin_routes(create_app(Settings(_env_file=None)))
    assert len(routes) >= 40, "the admin console should expose its full route table"
    missing = [(m, p) for m, p, role in routes if role not in ("reviewer", "admin")]
    assert missing == [], f"admin routes without require_role: {missing}"


@requires_postgres
async def test_students_anonymous_and_reviewers_are_refused(env: Env) -> None:  # noqa: F811
    app = env.client._transport.app  # type: ignore[attr-defined]
    _, student = await env.user("student-roles@example.com")
    _, reviewer = await env.user("reviewer-roles@example.com", role="reviewer")
    checked = 0
    for method, path, role in admin_routes(app):
        url = concrete(path)
        body = {} if method in ("POST", "PUT", "PATCH") else None
        anon = await env.client.request(method, url, json=body)
        assert anon.status_code == 401, (method, path, anon.status_code)
        r = await env.client.request(method, url, json=body, headers=student)
        assert r.status_code == 403, (method, path, r.status_code)
        assert r.json()["error"]["code"] == "forbidden"
        if role == "admin":
            r = await env.client.request(method, url, json=body, headers=reviewer)
            assert r.status_code == 403, ("reviewer", method, path, r.status_code)
        checked += 1
    assert checked >= 40
