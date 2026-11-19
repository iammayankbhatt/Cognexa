"""The public /graph endpoint (live Neo4j; each test seeds its own isolated subject)."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.graph.models import GraphEdge
from app.graph.repository import PREREQUISITE, GraphRepository
from app.main import create_app
from tests.conftest import live_settings, make_concept, requires_neo4j


async def test_graph_is_503_when_neo4j_is_not_configured() -> None:
    # Explicit None: `_env_file=None` still reads environment variables, and CI sets NEO4J_URI.
    app = create_app(Settings(_env_file=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        r = await client.get("/graph")
    assert r.status_code == 503 and r.json()["error"]["code"] == "graph_not_configured"


@requires_neo4j
async def test_public_graph_lists_nodes_and_prerequisite_edges(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    # The test seeds its own subject: CI starts with an empty Neo4j (BUG-018).
    sid = isolated_subject
    await graph_repo.upsert_subject(sid, "Test subject")
    for i, name in enumerate(["base", "next"]):
        await graph_repo.upsert_concept(sid, make_concept(f"{sid}_{name}", order_index=i))
    await graph_repo.upsert_edge(
        GraphEdge(source=f"{sid}_base", target=f"{sid}_next", type=PREREQUISITE)
    )

    app = create_app(live_settings())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as client:
        r = await client.get("/graph", params={"subject_id": sid})  # public: no token
        assert r.status_code == 200, r.text
        body = r.json()
        assert {n["id"] for n in body["nodes"]} == {f"{sid}_base", f"{sid}_next"}
        assert body["edges"] == [
            {"source": f"{sid}_base", "target": f"{sid}_next", "type": "PREREQUISITE_OF"}
        ]
        assert (await client.get("/graph", params={"subject_id": "Bad!"})).status_code == 422
        again = await client.get("/graph", params={"subject_id": sid})
        assert again.json() == body  # served from cache
    await app.state.graph.close()
