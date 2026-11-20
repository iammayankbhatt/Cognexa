"""Every route is either explicitly public or requires authentication (Phase 13 security).

Routes come from the app itself (cross-checked with OpenAPI), so a new route that forgets
`get_current_user` fails here unless it is added to PUBLIC on purpose.
"""

from __future__ import annotations

from app.core.config import Settings
from app.main import create_app
from tests.conftest import requires_postgres
from tests.route_walk import all_routes, concrete, depends_on
from tests.test_auth_api import Env, env  # noqa: F401

# Deliberately public: liveness, readiness (used by the keep-alive) and the landing page's graph.
PUBLIC = {
    ("GET", "/health"),
    ("GET", "/health/deep"),
    ("GET", "/graph"),
    # FastAPI's own documentation routes are not in the OpenAPI paths and not walked
}


def test_every_route_is_public_or_authenticated() -> None:
    routes = all_routes(create_app(Settings(_env_file=None)))
    assert len(routes) >= 80  # guards against an empty walk
    unexpected_public = [
        (m, p)
        for m, p, r in routes
        if (m, p) not in PUBLIC and not depends_on(r.dependant, "get_current_user")
    ]
    assert unexpected_public == [], f"routes without authentication: {unexpected_public}"
    # the allow-list must not go stale either
    assert {(m, p) for m, p, _ in routes} >= PUBLIC
    authenticated_public = [
        (m, p)
        for m, p, r in routes
        if (m, p) in PUBLIC and depends_on(r.dependant, "get_current_user")
    ]
    assert authenticated_public == []


@requires_postgres
async def test_anonymous_callers_get_401_everywhere_but_public_routes(env: Env) -> None:  # noqa: F811
    app = env.client._transport.app  # type: ignore[attr-defined]
    checked = 0
    for method, path, _ in all_routes(app):
        if (method, path) in PUBLIC:
            continue
        body = {} if method in ("POST", "PUT", "PATCH") else None
        r = await env.client.request(method, concrete(path), json=body)
        assert r.status_code == 401, (method, path, r.status_code)
        assert r.json()["error"]["code"] == "unauthorized"
        bad = await env.client.request(
            method, concrete(path), json=body, headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert bad.status_code == 401, ("bad token", method, path)
        checked += 1
    assert checked >= 80
