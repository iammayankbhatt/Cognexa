"""Admin graph editor API (Phase 11): roles, concept CRUD + mirror, edges, cycle rejection,
audit, cache invalidation and YAML export. Neo4j under an isolated subject, Postgres fresh."""

from __future__ import annotations

import itertools
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest
import yaml
from neo4j import AsyncDriver

from app.graph.models import ConceptFile
from app.graph.repository import GraphRepository
from tests.conftest import requires_neo4j, requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401

pytestmark = [requires_postgres, requires_neo4j]


class RepoProvider:
    """Stands in for app.state.graph: hands out a repository on the test Neo4j."""

    def __init__(self, driver: AsyncDriver) -> None:
        self.driver = driver

    @property
    def configured(self) -> bool:
        return True

    def repository(self) -> GraphRepository:
        return GraphRepository(self.driver)

    async def close(self) -> None:
        return None


@dataclass
class GEnv:
    env: Env
    app: Any
    sid: str
    student: dict[str, str]
    reviewer: dict[str, str]

    @property
    def client(self) -> Any:
        return self.env.client


@pytest.fixture
async def genv(
    env: Env,  # noqa: F811
    neo4j_driver: AsyncDriver,
    isolated_subject: str,
) -> AsyncIterator[GEnv]:
    app = env.client._transport.app  # type: ignore[attr-defined]
    app.state.graph = RepoProvider(neo4j_driver)
    sid = isolated_subject
    await GraphRepository(neo4j_driver).upsert_subject(sid, "Test subject")
    await env.db.execute("insert into subjects (id, name) values ($1, 'Test subject')", sid)
    _, student = await env.user("student@example.com")
    _, reviewer = await env.user("reviewer@example.com", role="reviewer")
    yield GEnv(env, app, sid, student, reviewer)


def concept(cid: str, **over: Any) -> dict[str, Any]:
    body = {
        "id": cid,
        "name": cid.replace("_", " ").title(),
        "cluster": "basics",
        "difficulty": 2,
        "description": f"Description of {cid} for the test graph.",
        "aliases": [f"{cid} alias"],
        "keywords": ["kw"],
    }
    return {**body, **over}


async def make_chain(g: GEnv, *ids: str) -> None:
    for cid in ids:
        r = await g.client.post(
            "/admin/graph/concepts",
            params={"subject_id": g.sid},
            headers=g.reviewer,
            json=concept(cid),
        )
        assert r.status_code == 201, r.text
    for a, b in itertools.pairwise(ids):
        r = await g.client.post(
            "/admin/graph/edges",
            headers=g.reviewer,
            json={"source": a, "target": b, "type": "PREREQUISITE_OF", "rationale": "order"},
        )
        assert r.status_code == 201, r.text


async def test_students_are_refused_everywhere(genv: GEnv) -> None:
    g = genv
    calls = [
        ("GET", "/admin/graph", None, None),
        ("POST", "/admin/graph/concepts", concept(f"{g.sid}_x"), None),
        ("PUT", f"/admin/graph/concepts/{g.sid}_x", concept(f"{g.sid}_x"), None),
        ("POST", "/admin/graph/edges", {"source": "aa", "target": "bb", "type": "RELATED_TO"}, None),
        ("GET", "/admin/graph/edges/check", None, {"source": "aa", "target": "bb"}),
        ("DELETE", "/admin/graph/edges", None, {"source": "aa", "target": "bb", "type": "RELATED_TO"}),
        ("GET", "/admin/graph/export.yaml", None, None),
    ]  # fmt: skip
    for method, path, body, params in calls:
        r = await g.client.request(method, path, headers=g.student, json=body, params=params)
        assert r.status_code == 403, (method, path, r.status_code)
        assert r.json()["error"]["code"] == "forbidden"
        anon = await g.client.request(method, path, json=body, params=params)
        assert anon.status_code == 401, (method, path)


async def test_concepts_are_created_mirrored_updated_and_audited(genv: GEnv) -> None:
    g = genv
    a = f"{g.sid}_alpha"
    g.app.state.graph_cache[g.sid] = (0.0, "stale")
    r = await g.client.post(
        "/admin/graph/concepts", params={"subject_id": g.sid}, headers=g.reviewer, json=concept(a)
    )
    assert r.status_code == 201, r.text
    assert r.json()["order_index"] == 0
    assert g.sid not in g.app.state.graph_cache  # public /graph cache invalidated
    dup = await g.client.post(
        "/admin/graph/concepts", params={"subject_id": g.sid}, headers=g.reviewer, json=concept(a)
    )
    assert dup.status_code == 409
    row = await g.env.db.fetchrow("select name, cluster, subject_id from concepts where id = $1", a)
    assert (row["name"], row["cluster"], row["subject_id"]) == (r.json()["name"], "basics", g.sid)

    upd = concept(a, name="Alpha Renamed", difficulty=4)
    del upd["id"]
    r = await g.client.put(f"/admin/graph/concepts/{a}", headers=g.reviewer, json=upd)
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Alpha Renamed" and r.json()["difficulty"] == 4
    assert await g.env.db.fetchval("select name from concepts where id = $1", a) == "Alpha Renamed"
    missing = await g.client.put(
        f"/admin/graph/concepts/{g.sid}_nope", headers=g.reviewer, json=upd
    )
    assert missing.status_code == 404
    bad = await g.client.put(
        f"/admin/graph/concepts/{a}", headers=g.reviewer, json={**upd, "description": "short"}
    )
    assert bad.status_code == 422

    actions = await g.env.db.fetch("select action, target from audit_log order by id")
    assert [(r["action"], r["target"]) for r in actions] == [
        ("graph.create_concept", a),
        ("graph.update_concept", a),
    ]


async def test_cycles_are_rejected_with_the_existing_chain(genv: GEnv) -> None:
    g = genv
    a, b, c = (f"{g.sid}_{n}" for n in ("a", "b", "c"))
    await make_chain(g, a, b, c)

    r = await g.client.post(
        "/admin/graph/edges",
        headers=g.reviewer,
        json={"source": c, "target": a, "type": "PREREQUISITE_OF"},
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "cycle_detected"
    assert err["details"]["path"] == [a, b, c]
    assert "would create a cycle" in err["message"]

    check = await g.client.get(
        "/admin/graph/edges/check", headers=g.reviewer, params={"source": c, "target": a}
    )
    assert check.json()["ok"] is False and check.json()["path"] == [a, b, c]
    fine = await g.client.get(
        "/admin/graph/edges/check", headers=g.reviewer, params={"source": a, "target": c}
    )
    assert fine.json() == {"ok": True, "message": None, "path": []}

    self_loop = await g.client.post(
        "/admin/graph/edges", headers=g.reviewer, json={"source": a, "target": a, "type": "RELATED_TO"}
    )  # fmt: skip
    assert self_loop.status_code == 422
    related_on_prereq = await g.client.post(
        "/admin/graph/edges", headers=g.reviewer, json={"source": b, "target": a, "type": "RELATED_TO"}
    )  # fmt: skip
    assert related_on_prereq.status_code == 409
    unknown = await g.client.post(
        "/admin/graph/edges",
        headers=g.reviewer,
        json={"source": a, "target": f"{g.sid}_zz", "type": "RELATED_TO"},
    )
    assert unknown.status_code == 404

    graph = (
        await g.client.get("/admin/graph", params={"subject_id": g.sid}, headers=g.reviewer)
    ).json()
    assert {(e["source"], e["target"]) for e in graph["edges"]} == {(a, b), (b, c)}
    assert all(e["source_kind"] == "human" and e["status"] == "approved" for e in graph["edges"])


async def test_edges_are_removed_and_audited(genv: GEnv) -> None:
    g = genv
    a, b = f"{g.sid}_a", f"{g.sid}_b"
    await make_chain(g, a, b)
    params = {"source": a, "target": b, "type": "PREREQUISITE_OF", "rationale": "wrong"}
    r = await g.client.delete("/admin/graph/edges", headers=g.reviewer, params=params)
    assert r.status_code == 204
    again = await g.client.delete("/admin/graph/edges", headers=g.reviewer, params=params)
    assert again.status_code == 404
    last = await g.env.db.fetchrow("select action, details from audit_log order by id desc limit 1")
    assert last["action"] == "graph.remove_edge" and '"wrong"' in last["details"]


async def test_export_yaml_round_trips_into_a_valid_concept_file(genv: GEnv) -> None:
    g = genv
    a, b, c = (f"{g.sid}_{n}" for n in ("a", "b", "c"))
    await make_chain(g, a, b, c)
    r = await g.client.post(
        "/admin/graph/edges",
        headers=g.reviewer,
        json={"source": c, "target": a, "type": "RELATED_TO", "rationale": "see also"},
    )
    assert r.status_code == 201, r.text
    resp = await g.client.get(
        "/admin/graph/export.yaml", params={"subject_id": g.sid}, headers=g.reviewer
    )
    assert resp.status_code == 200
    assert resp.headers["x-validation-errors"] == "0"
    assert "attachment" in resp.headers["content-disposition"]
    doc = ConceptFile.model_validate(yaml.safe_load(resp.text))
    by_id = {x.id: x for x in doc.concepts}
    assert doc.subject.id == g.sid and doc.roots == [a]
    assert by_id[b].prerequisites == [a] and by_id[c].prerequisites == [b]
    assert by_id[c].related == [a]  # stored once, on the larger id
    assert [x.order_index for x in doc.concepts] == [0, 1, 2]
    assert by_id[a].aliases == [f"{a} alias"]
