"""Walk the FastAPI app's routes: used by the role/auth enumeration tests and by
scripts/gen_api_docs.py (the Access column of docs/API.md)."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute


def minimum_role(dep: Dependant) -> str | None:
    """The role named by a require_role(...) dependency anywhere in the dependency tree."""
    call = dep.call
    if call is not None and call.__qualname__.startswith("require_role."):
        return str(inspect.getclosurevars(call).nonlocals["minimum"])
    for sub in dep.dependencies:
        found = minimum_role(sub)
        if found:
            return found
    return None


def walk(routes: list[Any]) -> list[APIRoute]:
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
                out.extend(walk(sub))
    return out


def admin_routes(app: Any) -> list[tuple[str, str, str | None]]:
    out = []
    for r in walk(app.routes):
        if r.path.startswith("/admin"):
            for method in sorted((r.methods or set()) - {"HEAD", "OPTIONS"}):
                out.append((method, r.path, minimum_role(r.dependant)))
    documented = {
        (m.upper(), path)
        for path, ops in app.openapi()["paths"].items()
        if path.startswith("/admin")
        for m in ops
    }
    assert {(m, p) for m, p, _ in out} == documented, "route walk disagrees with OpenAPI"
    return sorted(set(out))


def depends_on(dep: Dependant, name: str) -> bool:
    """True if a dependency called `name` appears anywhere in the dependency tree."""
    if dep.call is not None and getattr(dep.call, "__name__", "") == name:
        return True
    return any(depends_on(sub, name) for sub in dep.dependencies)


def all_routes(app: Any) -> list[tuple[str, str, APIRoute]]:
    """(method, path, route) for every API route, checked against the OpenAPI schema."""
    out = [
        (m, r.path, r)
        for r in walk(app.routes)
        for m in sorted((r.methods or set()) - {"HEAD", "OPTIONS"})
    ]
    documented = {(m.upper(), path) for path, ops in app.openapi()["paths"].items() for m in ops}
    assert {(m, p) for m, p, _ in out} == documented, "route walk disagrees with OpenAPI"
    return out
