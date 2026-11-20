"""LLM proposals with human review (Phase 11): suggest edges, ingestion (Markdown + PDF), review
queue, approve / edit / reject / bulk, the graph-first apply saga, and re-seed safety."""

from __future__ import annotations

from typing import Any

import pytest

from app.admin.proposals import ProposalRepository
from app.content.notes import Chunk
from app.db.repositories import ContentRepository
from app.db.session import Database
from tests.conftest import requires_neo4j, requires_postgres
from tests.pdf_helpers import make_pdf
from tests.test_admin_graph_api import GEnv, concept, genv, make_chain  # noqa: F401
from tests.test_auth_api import env  # noqa: F401

pytestmark = [requires_postgres, requires_neo4j]


async def seed_ds(g: GEnv) -> dict[str, str]:
    """stack -> queue_impl chain plus an unrelated concept, with recognisable aliases."""
    ids = {k: f"{g.sid}_{k}" for k in ("array", "stack", "queue")}
    bodies = {
        "array": concept(ids["array"], name="Array Basics", aliases=["array", "contiguous memory"],
                         description="Fixed-size contiguous storage indexed by position."),
        "stack": concept(ids["stack"], name="Stack Basics", aliases=["stack", "lifo", "push pop"],
                         description="A LIFO structure usually built on an array basics layout."),
        "queue": concept(ids["queue"], name="Queue Basics", aliases=["queue", "fifo", "enqueue"],
                         description="A FIFO structure; compare with stack basics."),
    }  # fmt: skip
    for body in bodies.values():
        r = await g.client.post(
            "/admin/graph/concepts", params={"subject_id": g.sid}, headers=g.reviewer, json=body
        )
        assert r.status_code == 201, r.text
    return ids


async def pending(g: GEnv, **params: Any) -> list[dict[str, Any]]:
    r = await g.client.get("/admin/proposals", headers=g.reviewer, params=params)
    assert r.status_code == 200, r.text
    return list(r.json()["items"])


async def test_suggest_edges_creates_pending_proposals_once(genv: GEnv) -> None:  # noqa: F811
    g = genv
    ids = await seed_ds(g)
    url = f"/admin/graph/concepts/{ids['stack']}/suggest-edges"
    assert (
        await g.client.post(url, headers=g.student, params={"subject_id": g.sid})
    ).status_code == 403
    r = await g.client.post(url, headers=g.reviewer, params={"subject_id": g.sid})
    assert r.status_code == 200, r.text
    created = r.json()["created"]
    assert created, r.json()
    items = await pending(g, type="add_edge")
    edge = next(i for i in items if i["payload"]["source"] == ids["array"])
    assert edge["payload"] == {"subject_id": g.sid, "source": ids["array"], "target": ids["stack"],
                               "edge_type": "PREREQUISITE_OF"}  # fmt: skip
    assert edge["proposed_by"] == "llm" and 0 < edge["confidence"] <= 1 and edge["rationale"]
    assert edge["names"][ids["array"]] == "Array Basics"
    again = await g.client.post(url, headers=g.reviewer, params={"subject_id": g.sid})
    assert again.json()["created"] == []
    assert {s["reason"] for s in again.json()["skipped"]} <= {"already proposed", "already linked"}
    used = await g.env.db.fetchval("select coalesce(sum(ai_requests), 0) from usage_daily")
    assert used == 2  # both calls went through the usage guard


async def test_approve_reject_and_acceptance_stats(genv: GEnv) -> None:  # noqa: F811
    g = genv
    ids = await seed_ds(g)
    await g.client.post(
        f"/admin/graph/concepts/{ids['stack']}/suggest-edges",
        headers=g.reviewer,
        params={"subject_id": g.sid},
    )
    items = await pending(g, type="add_edge")
    first, rest = items[0], items[1:]
    r = await g.client.post(
        f"/admin/proposals/{first['id']}/approve", headers=g.reviewer, json={"note": "good"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["proposal"]["status"] == "approved"
    graph = (
        await g.client.get("/admin/graph", params={"subject_id": g.sid}, headers=g.reviewer)
    ).json()
    p = first["payload"]
    made = [e for e in graph["edges"] if {e["source"], e["target"]} == {p["source"], p["target"]}]
    assert made and made[0]["source_kind"] == "llm" and made[0]["status"] == "approved"
    twice = await g.client.post(
        f"/admin/proposals/{first['id']}/approve", headers=g.reviewer, json={}
    )
    assert twice.status_code == 409

    for it in rest:
        r = await g.client.post(
            f"/admin/proposals/{it['id']}/reject", headers=g.reviewer, json={"note": "no"}
        )
        assert r.status_code == 200 and r.json()["proposal"]["status"] == "rejected"
    stats = (await g.client.get("/admin/proposals/stats", headers=g.reviewer)).json()
    edge = stats["by_type"]["add_edge"]
    assert edge["approved"] == 1 and edge["rejected"] == len(rest)
    assert edge["acceptance_rate"] == round(1 / (1 + len(rest)), 4)
    actions = [
        r["action"] for r in await g.env.db.fetch("select action from audit_log order by id")
    ]
    assert "proposal.approve" in actions and "graph.add_edge_from_proposal" in actions
    assert actions.count("proposal.reject") == len(rest)


async def test_cyclic_edge_proposal_is_flagged_and_never_applied(genv: GEnv) -> None:  # noqa: F811
    g = genv
    a, b = f"{g.sid}_a", f"{g.sid}_b"
    await make_chain(g, a, b)
    db: Database = g.app.state.db
    async with db.sessions()() as s, s.begin():
        pid = await ProposalRepository(s).create(
            "add_edge",
            {"subject_id": g.sid, "source": b, "target": a, "edge_type": "PREREQUISITE_OF"},
            "backwards",
            0.9,
        )
    detail = (await g.client.get(f"/admin/proposals/{pid}", headers=g.reviewer)).json()
    assert detail["cycle"]["path"] == [a, b]
    assert {c["id"] for c in detail["preview"]["concepts"]} >= {a, b}
    r = await g.client.post(f"/admin/proposals/{pid}/approve", headers=g.reviewer, json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "cycle_detected"
    still = (await g.client.get(f"/admin/proposals/{pid}", headers=g.reviewer)).json()
    assert still["status"] == "pending"


MD_NOTES = """# Week 3 lecture notes

## Course admin
Office hours move to Thursday. Submit labs on the portal before the deadline please, thanks.

## Stacks
A stack is a LIFO collection: the last element pushed is the first one popped. Push and pop both
run in O(1) time. Stacks power the call stack, undo buttons and bracket matching. A stack built on
an array keeps a top index; push writes at top and increments it, pop decrements it and reads.

## Queues
A queue is FIFO: enqueue adds at the back and dequeue removes from the front, both O(1) with a
circular buffer. Breadth-first search uses a queue to visit vertices level by level, and printers
and schedulers use queues to serve jobs fairly in arrival order. The queue never reorders items.
"""


async def ingest(g: GEnv, filename: str, data: bytes) -> dict[str, Any]:
    r = await g.client.post(
        "/admin/ingest",
        params={"filename": filename, "subject_id": g.sid},
        headers={**g.reviewer, "content-type": "application/octet-stream"},
        content=data,
    )
    assert r.status_code == 202, r.text
    doc = (await g.client.get(f"/admin/ingest/{r.json()['id']}", headers=g.reviewer)).json()
    assert doc["status"] == "done", doc
    return dict(doc)


async def test_markdown_ingestion_tags_sections_and_approved_chunks_are_retrievable(
    genv: GEnv,  # noqa: F811
) -> None:
    g = genv
    ids = await seed_ds(g)
    doc = await ingest(g, "week3.md", MD_NOTES.encode())
    assert doc["sections"] >= 2 and doc["proposals"] == 2 and doc["media_type"] == "text/markdown"
    items = await pending(g, type="tag_chunk", document_id=doc["id"])
    by_concept = {i["payload"]["concept_id"]: i for i in items}
    assert set(by_concept) == {ids["stack"], ids["queue"]}
    assert by_concept[ids["stack"]]["payload"]["document_name"] == "week3.md"
    assert "LIFO" in by_concept[ids["stack"]]["payload"]["text"]

    # same file again: nothing new (text hashes already proposed)
    again = await ingest(g, "week3.md", MD_NOTES.encode())
    assert again["proposals"] == 0

    # approve the queue section, but as a "mechanism" chunk (edit before approval)
    q = by_concept[ids["queue"]]
    r = await g.client.post(
        f"/admin/proposals/{q['id']}/approve",
        headers=g.reviewer,
        json={"edits": {"kind": "mechanism", "heading": "Queues (lecture)"}},
    )
    assert r.status_code == 200, r.text
    chunk_id = r.json()["applied"]["chunk_id"]
    stored = r.json()["proposal"]["payload"]
    assert stored["edited"] is True and stored["original"] == {
        "kind": "overview",
        "heading": "Queues",
    }
    row = await g.env.db.fetchrow(
        "select concept_id, kind, heading, reviewed, source, embedding is not null as has_vec, "
        "embedding_hash = content_hash as fresh from content_chunks where id = $1",
        chunk_id,
    )
    assert dict(row) == {"concept_id": ids["queue"], "kind": "mechanism", "heading": "Queues (lecture)",
                         "reviewed": True, "source": "llm", "has_vec": True, "fresh": True}  # fmt: skip
    repo = g.app.state.graph.repository()
    chunks = await repo.get_chunks([ids["queue"]])
    assert [(c.id, c.source, c.reviewed) for c in chunks] == [(chunk_id, "llm", True)]

    # re-seeding notes for that concept keeps the approved LLM chunk (Postgres and Neo4j)
    note = Chunk(id=f"{ids['queue']}#overview", concept_id=ids["queue"], subject_id=g.sid,
                 kind="overview", heading="Overview", text="Queue notes from the file.", order=0,
                 reviewed=False)  # fmt: skip
    async with g.app.state.db.sessions()() as s, s.begin():
        await ContentRepository(s).upsert_chunks([note])
    left = await g.env.db.fetch(
        "select id from content_chunks where concept_id = $1 order by id", ids["queue"]
    )
    assert {r["id"] for r in left} == {chunk_id, note.id}
    assert await repo.delete_stale_chunks({ids["queue"]: [note.id]}) == 0


async def test_pdf_ingestion_and_file_checks(genv: GEnv) -> None:  # noqa: F811
    g = genv
    ids = await seed_ds(g)
    lines = [line for line in MD_NOTES.splitlines() if line and not line.startswith("#")]
    pdf = make_pdf([["2 Stacks", *lines[1:4]], ["3 Queues", *lines[4:]]])
    doc = await ingest(g, "notes.pdf", pdf)
    assert doc["media_type"] == "application/pdf" and doc["pages"] == 2
    concepts = {i["payload"]["concept_id"] for i in await pending(g, document_id=doc["id"])}
    assert concepts == {ids["stack"], ids["queue"]}

    async def post(name: str, data: bytes) -> Any:
        return await g.client.post(
            "/admin/ingest",
            params={"filename": name, "subject_id": g.sid},
            headers={**g.reviewer, "content-type": "application/octet-stream"},
            content=data,
        )

    scanned = await post("scan.pdf", make_pdf([[], []]))
    assert scanned.status_code == 422 and scanned.json()["error"]["code"] == "scanned_pdf"
    assert (await post("slides.pptx", b"x")).status_code == 415
    assert (await post("big.txt", b"a" * (10 * 1024 * 1024 + 1))).status_code == 413
    assert (await post("broken.pdf", b"%PDF-1.4 nonsense")).status_code == 422
    assert (await post("empty.md", b"")).status_code == 422
    student = await g.client.post(
        "/admin/ingest", params={"filename": "a.md"}, headers=g.student, content=b"hello"
    )
    assert student.status_code == 403


async def test_new_concept_proposal_creates_concept_edges_and_chunk(genv: GEnv) -> None:  # noqa: F811
    g = genv
    ids = await seed_ds(g)
    new_id = f"{g.sid}_deque"
    async with g.app.state.db.sessions()() as s, s.begin():
        pid = await ProposalRepository(s).create(
            "new_concept",
            {"subject_id": g.sid,
             "concept": {"id": new_id, "name": "Deque", "cluster": "basics", "difficulty": 2,
                         "description": "A double-ended queue supporting both ends."},
             "prerequisites": [ids["queue"], ids["stack"], f"{g.sid}_missing"],
             "heading": "Deques", "text": "A deque allows insertion and removal at both ends in O(1)."},
            "not in the catalogue", 0.8,
        )  # fmt: skip
    r = await g.client.post(f"/admin/proposals/{pid}/approve", headers=g.reviewer, json={})
    assert r.status_code == 200, r.text
    applied = r.json()["applied"]
    assert applied["concept_id"] == new_id
    assert sorted(applied["prerequisites_added"]) == sorted([ids["queue"], ids["stack"]])
    assert applied["prerequisites_skipped"] == [
        {"prerequisite": f"{g.sid}_missing", "reason": "not_found"}
    ]
    assert await g.env.db.fetchval("select name from concepts where id = $1", new_id) == "Deque"
    assert (
        await g.env.db.fetchval(
            "select count(*) from content_chunks where concept_id = $1 and source = 'llm'", new_id
        )
        == 1
    )


async def test_bulk_approve_needs_the_confirmed_count(genv: GEnv) -> None:  # noqa: F811
    g = genv
    await seed_ds(g)
    await ingest(g, "week3.md", MD_NOTES.encode())
    n = (await g.client.get("/admin/proposals-count", headers=g.reviewer,
                            params={"min_confidence": 0.5, "type": "tag_chunk"})).json()["matching"]  # fmt: skip
    assert n == 2
    wrong = await g.client.post(
        "/admin/proposals/bulk-approve",
        headers=g.reviewer,
        json={"min_confidence": 0.5, "type": "tag_chunk", "expected_count": n + 1},
    )
    assert wrong.status_code == 409 and wrong.json()["error"]["details"]["matching"] == n
    ok = await g.client.post(
        "/admin/proposals/bulk-approve",
        headers=g.reviewer,
        json={"min_confidence": 0.5, "type": "tag_chunk", "expected_count": n},
    )
    assert ok.status_code == 200, ok.text
    assert len(ok.json()["approved"]) == n and ok.json()["failed"] == []
    assert await pending(g, type="tag_chunk") == []


async def test_partial_failure_is_reported_and_retry_completes(
    genv: GEnv,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    g = genv
    ids = await seed_ds(g)
    await ingest(g, "week3.md", MD_NOTES.encode())
    item = (await pending(g, type="tag_chunk"))[0]
    real = ProposalRepository.decide
    calls = {"n": 0}

    async def flaky(self: ProposalRepository, *a: Any, **k: Any) -> bool:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("database went away")
        return await real(self, *a, **k)

    monkeypatch.setattr(ProposalRepository, "decide", flaky)
    first = await g.client.post(
        f"/admin/proposals/{item['id']}/approve", headers=g.reviewer, json={}
    )
    assert first.status_code == 503 and first.json()["error"]["code"] == "partial_apply"
    # the graph already has the chunk, Postgres does not, the proposal is still pending
    concept_id = item["payload"]["concept_id"]
    assert len(await g.app.state.graph.repository().get_chunks([concept_id])) == 1
    assert (
        await g.env.db.fetchval(
            "select count(*) from content_chunks where concept_id = $1", concept_id
        )
        == 0
    )
    retry = await g.client.post(
        f"/admin/proposals/{item['id']}/approve", headers=g.reviewer, json={}
    )
    assert retry.status_code == 200, retry.text
    assert len(await g.app.state.graph.repository().get_chunks([concept_id])) == 1  # idempotent
    assert (
        await g.env.db.fetchval(
            "select count(*) from content_chunks where concept_id = $1", concept_id
        )
        == 1
    )
    assert ids  # silence unused
