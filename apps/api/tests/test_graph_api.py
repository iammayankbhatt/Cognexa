"""The public /graph endpoint (live Neo4j seeded by the test fixtures)."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.main import create_app
from tests.conftest import live_settings, requires_neo4j


async def test_graph_is_503_when_neo4j_is_not_configured() -> None:
    app = create_app(Settings(_env_file=None))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        r = await client.get("/graph")
    assert r.status_code == 503 and r.json()["error"]["code"] == "graph_not_configured"


@requires_neo4j
async def test_public_graph_lists_nodes_and_prerequisite_edges() -> None:
    app = create_app(live_settings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        r = await client.get("/graph")  # public: no token
        assert r.status_code == 200, r.text
        body = r.json()
        ids = {n["id"] for n in body["nodes"]}
        assert {"call_stack", "recursion"} <= ids
        assert {"source": "call_stack", "target": "recursion", "type": "PREREQUISITE_OF"} in body[
            "edges"
        ]
        assert (await client.get("/graph", params={"subject_id": "Bad!"})).status_code == 422
        assert (await client.get("/graph")).json() == body  # served from cache
    await app.state.graph.close()
