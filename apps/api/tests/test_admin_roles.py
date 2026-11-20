"""Role enforcement on EVERY admin endpoint (Phase 11 test list).

The routes are read from the app itself, so a new /admin route is covered automatically, and a
route that forgets its `require_role` dependency fails `test_every_admin_route_declares_a_role`.
"""

from __future__ import annotations

import inspect
import re
import uuid
from typing import Any

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from app.core.config import Settings
from app.main import create_app
from tests.conftest import requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401


def _minimum_role(dep: Dependant) -> str | None:
    """The role named by a require_role(...) dependency anywhere in the dependency tree."""
    call = dep.call
    if call is not None and call.__qualname__.startswith("require_role."):
        return str(inspect.getclosurevars(call).nonlocals["minimum"])
    for sub in dep.dependencies:
        found = _minimum_role(sub)
        if found:
            return found
    return None


def _walk(routes: list[Any]) -> list[APIRoute]:
    """APIRoutes, also inside included routers (FastAPI 0.165 nests them; the attribute name is
    not public, so any child exposing `routes` is followed and the result is checked against
    the OpenAPI schema below)."""
    out: list[APIRoute] = []
    for r in routes:
        if isinstance(r, APIRoute):
            out.append(r)
            continue
        for child in vars(r).values() if hasattr(r, "__dict__") else []:
            sub = getattr(child, "routes", None)
            if isinstance(sub, list) and child is not r:
                out.extend(_walk(sub))
    return out


def admin_routes(app: Any) -> list[tuple[str, str, str | None]]:
    out = []
    for r in _walk(app.routes):
        if r.path.startswith("/admin"):
            for method in sorted(r.methods - {"HEAD", "OPTIONS"}):
                out.append((method, r.path, _minimum_role(r.dependant)))
    documented = {
        (m.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        if path.startswith("/admin")
        for m in ops
    }
    assert {(m, p) for m, p, _ in out} == documented, "route walk disagrees with OpenAPI"
    return sorted(set(out))


def concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)


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
