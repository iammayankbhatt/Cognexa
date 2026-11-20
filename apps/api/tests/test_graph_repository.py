"""GraphRepository integration tests against a real Neo4j (docker locally, CI service)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.graph.loader import load_concept_file, load_subject
from app.graph.models import ConceptFile, GraphEdge, SubjectDef
from app.graph.repository import (
    PREREQUISITE,
    RELATED,
    ChunkRecord,
    CycleError,
    GraphRepository,
    UnknownConceptError,
)
from app.graph.seed import InvalidGraphError, seed_subject

from .conftest import make_concept

pytestmark = pytest.mark.asyncio

FIXTURES = Path(__file__).parent / "fixtures"


async def build_chain(repo: GraphRepository, sid: str) -> dict[str, str]:
    """a -> b -> c -> d (prerequisite chain), a -> e, and d ~ f (related). Returns name -> id."""
    ids = {n: f"{sid}_{n}" for n in "abcdef"}
    await repo.upsert_subject(sid, "Test subject")
    for i, n in enumerate("abcdef"):
        await repo.upsert_concept(sid, make_concept(ids[n], order_index=i))
    for src, dst in [("a", "b"), ("b", "c"), ("c", "d"), ("a", "e")]:
        await repo.upsert_edge(GraphEdge(source=ids[src], target=ids[dst], type=PREREQUISITE))
    await repo.upsert_edge(GraphEdge(source=ids["d"], target=ids["f"], type=RELATED))
    return ids


def idset(items: list) -> list[str]:  # type: ignore[type-arg]
    return [i.concept.id if hasattr(i, "concept") else i.id for i in items]


# ----------------------------------------------------------------------- basic reads
async def test_get_and_list_concepts(graph_repo: GraphRepository, isolated_subject: str) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    c = await graph_repo.get_concept(ids["a"])
    assert c is not None
    assert c.subject_id == isolated_subject
    assert c.aliases == [f"alias {ids['a']}"]
    listed = await graph_repo.list_concepts(isolated_subject)
    assert [x.id for x in listed] == [ids[n] for n in "abcdef"]
    assert await graph_repo.get_concept("does_not_exist") is None


async def test_get_prerequisites_respects_depth_and_orders_nearest_first(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    d1 = await graph_repo.get_prerequisites(ids["d"], depth=1)
    assert idset(d1) == [ids["c"]]
    d2 = await graph_repo.get_prerequisites(ids["d"], depth=2)
    assert idset(d2) == [ids["c"], ids["b"]]
    assert [p.depth for p in d2] == [1, 2]
    d3 = await graph_repo.get_prerequisites(ids["d"], depth=3)
    assert idset(d3) == [ids["c"], ids["b"], ids["a"]]
    assert await graph_repo.get_prerequisites(ids["a"], depth=5) == []


async def test_depth_is_clamped_not_injected(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    huge = await graph_repo.get_prerequisites(ids["d"], depth=10_000)
    assert len(huge) == 3
    zero = await graph_repo.get_prerequisites(ids["d"], depth=0)
    assert idset(zero) == [ids["c"]]  # clamped up to 1


async def test_get_dependents(graph_repo: GraphRepository, isolated_subject: str) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    d1 = await graph_repo.get_dependents(ids["a"], depth=1)
    assert set(idset(d1)) == {ids["b"], ids["e"]}
    d2 = await graph_repo.get_dependents(ids["a"], depth=2)
    assert set(idset(d2)) == {ids["b"], ids["e"], ids["c"]}


async def test_proposed_edges_are_ignored_by_traversals(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    await graph_repo.upsert_edge(
        GraphEdge(
            source=ids["a"],
            target=ids["d"],
            type=PREREQUISITE,
            status="proposed",
            source_kind="llm",
            rationale="test",
        )
    )
    assert idset(await graph_repo.get_prerequisites(ids["d"], depth=1)) == [ids["c"]]
    # ...but they count for cycle checks, so approving later can never create a cycle
    assert await graph_repo.would_create_cycle(ids["d"], ids["a"])


async def test_related_is_stored_once_and_queried_undirected(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    assert idset(await graph_repo.get_related(ids["d"])) == [ids["f"]]
    assert idset(await graph_repo.get_related(ids["f"])) == [ids["d"]]
    # upserting the same pair in the other direction must not create a second edge
    await graph_repo.upsert_edge(GraphEdge(source=ids["f"], target=ids["d"], type=RELATED))
    related = [e for e in await graph_repo.list_edges(isolated_subject) if e.type == RELATED]
    assert len(related) == 1


async def test_get_subgraph(graph_repo: GraphRepository, isolated_subject: str) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    sub = await graph_repo.get_subgraph([ids["d"]], depth=2)
    got = {c.id for c in sub.concepts}
    assert got == {ids["d"], ids["c"], ids["b"], ids["f"]}
    pairs = {(e.source, e.target, e.type) for e in sub.edges}
    assert (ids["b"], ids["c"], PREREQUISITE) in pairs
    assert (ids["c"], ids["d"], PREREQUISITE) in pairs
    assert (ids["d"], ids["f"], RELATED) in pairs
    assert all(ids["a"] not in (e.source, e.target) for e in sub.edges)
    empty = await graph_repo.get_subgraph([], depth=2)
    assert empty.concepts == [] and empty.edges == []


async def test_topological_order(graph_repo: GraphRepository, isolated_subject: str) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    order = await graph_repo.topological_order(isolated_subject)
    assert set(order) == set(ids.values())
    pos = {c: i for i, c in enumerate(order)}
    for src, dst in [("a", "b"), ("b", "c"), ("c", "d"), ("a", "e")]:
        assert pos[ids[src]] < pos[ids[dst]]


# ----------------------------------------------------------------------- chunks
async def test_chunks_filter_order_and_limit(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    for order, kind in enumerate(["overview", "intuition", "mechanism"]):
        await graph_repo.upsert_chunk(
            ChunkRecord(
                id=f"{ids['a']}#{kind}",
                concept_id=ids["a"],
                subject_id=isolated_subject,
                kind=kind,
                heading=kind.title(),
                text=f"text of {kind}",
                order=order,
            )
        )
    all_chunks = await graph_repo.get_chunks([ids["a"]])
    assert [c.kind for c in all_chunks] == ["overview", "intuition", "mechanism"]
    only = await graph_repo.get_chunks([ids["a"]], kinds=["intuition"])
    assert [c.kind for c in only] == ["intuition"]
    limited = await graph_repo.get_chunks([ids["a"]], limit=2)
    assert len(limited) == 2
    assert await graph_repo.get_chunks([ids["b"]]) == []


# ----------------------------------------------------------------------- cycles and edits
async def test_would_create_cycle(graph_repo: GraphRepository, isolated_subject: str) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    assert await graph_repo.would_create_cycle(ids["d"], ids["a"])  # a is already before d
    assert await graph_repo.would_create_cycle(ids["a"], ids["a"])
    assert not await graph_repo.would_create_cycle(ids["a"], ids["d"])  # redundant, acyclic
    assert not await graph_repo.would_create_cycle(ids["e"], ids["f"])


async def test_upsert_edge_rejects_cycle_and_leaves_graph_unchanged(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    before = await graph_repo.list_edges(isolated_subject)
    with pytest.raises(CycleError):
        await graph_repo.upsert_edge(GraphEdge(source=ids["d"], target=ids["a"], type=PREREQUISITE))
    with pytest.raises(ValueError):
        await graph_repo.upsert_edge(GraphEdge(source=ids["a"], target=ids["a"], type=PREREQUISITE))
    assert await graph_repo.list_edges(isolated_subject) == before


async def test_upsert_edge_unknown_concept_and_type(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    with pytest.raises(UnknownConceptError):
        await graph_repo.upsert_edge(
            GraphEdge(source=ids["a"], target="nope_nope", type=PREREQUISITE)
        )
    with pytest.raises(ValueError):
        await graph_repo.upsert_edge(GraphEdge(source=ids["a"], target=ids["b"], type="LIKES"))


async def test_upsert_edge_is_idempotent_and_updates_properties(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    for weight in (1.0, 0.5):
        await graph_repo.upsert_edge(
            GraphEdge(source=ids["a"], target=ids["b"], type=PREREQUISITE, weight=weight)
        )
    edges = [
        e
        for e in await graph_repo.list_edges(isolated_subject)
        if (e.source, e.target) == (ids["a"], ids["b"])
    ]
    assert len(edges) == 1 and edges[0].weight == 0.5


async def test_delete_edge(graph_repo: GraphRepository, isolated_subject: str) -> None:
    ids = await build_chain(graph_repo, isolated_subject)
    assert await graph_repo.delete_edge(ids["a"], ids["e"], PREREQUISITE)
    assert not await graph_repo.delete_edge(ids["a"], ids["e"], PREREQUISITE)
    # related edges delete in either direction
    assert await graph_repo.delete_edge(ids["f"], ids["d"], RELATED)
    assert await graph_repo.get_related(ids["d"]) == []
    with pytest.raises(ValueError):
        await graph_repo.delete_edge(ids["a"], ids["b"], "LIKES")


async def test_hostile_ids_are_treated_as_data(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    await build_chain(graph_repo, isolated_subject)
    nasty = "x' }) MATCH (n) DETACH DELETE n //"
    assert await graph_repo.get_concept(nasty) is None
    assert await graph_repo.get_prerequisites(nasty, depth=3) == []
    assert len(await graph_repo.list_concepts(isolated_subject)) == 6  # nothing was deleted


# ----------------------------------------------------------------------- seeding
def doc_for(sid: str, edges: list[tuple[str, str]]) -> ConceptFile:
    names = sorted({n for e in edges for n in e})
    prereqs: dict[str, list[str]] = {n: [] for n in names}
    for before, after in edges:
        prereqs[after].append(f"{sid}_{before}")
    order = {n: i for i, n in enumerate(names)}
    return ConceptFile(
        subject=SubjectDef(id=sid, name="Seed test"),
        roots=[f"{sid}_{n}" for n in names if not prereqs[n]],
        concepts=[make_concept(f"{sid}_{n}", prereqs[n], order_index=order[n]) for n in names],
    )


async def test_seed_twice_creates_no_duplicates(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    doc = doc_for(isolated_subject, [("a", "b"), ("b", "c")])
    first = await seed_subject(graph_repo, doc)
    second = await seed_subject(graph_repo, doc)
    assert first == second
    assert len(await graph_repo.list_concepts(isolated_subject)) == 3
    assert len(await graph_repo.list_edges(isolated_subject)) == 2


async def test_seed_prune_removes_stale_human_edges_but_keeps_llm_edges(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    sid = isolated_subject
    await seed_subject(graph_repo, doc_for(sid, [("a", "b"), ("b", "c"), ("a", "c")]))
    await graph_repo.upsert_edge(
        GraphEdge(
            source=f"{sid}_a",
            target=f"{sid}_c",
            type=PREREQUISITE,
            source_kind="llm",
            status="proposed",
        )
    )
    # new file drops a->c; the stored a->c is now an llm-sourced edge, so it must survive
    result = await seed_subject(graph_repo, doc_for(sid, [("a", "b"), ("b", "c")]), prune=True)
    assert result.pruned_edges == 0
    # a different stale human edge is pruned
    await graph_repo.upsert_edge(GraphEdge(source=f"{sid}_a", target=f"{sid}_b", type=RELATED))
    pruned = await seed_subject(graph_repo, doc_for(sid, [("a", "b"), ("b", "c")]), prune=True)
    assert pruned.pruned_edges == 1


async def test_seed_rejects_invalid_graph_and_writes_nothing(
    graph_repo: GraphRepository, neo4j_driver: object
) -> None:
    doc = load_concept_file(FIXTURES / "cyclic_concepts.yaml")
    with pytest.raises(InvalidGraphError):
        await seed_subject(graph_repo, doc)
    assert await graph_repo.list_concepts("fixture") == []


# ----------------------------------------------------------------------- the real DSA graph
async def test_real_dsa_graph_seeds_and_traverses(graph_repo: GraphRepository) -> None:
    doc = load_subject("dsa")
    result = await seed_subject(graph_repo, doc)
    assert (result.concepts, result.prerequisite_edges, result.related_edges) == (
        69,
        111,
        15,
    )  # 15 since BUG-042
    again = await seed_subject(graph_repo, doc)
    assert again == result
    assert len(await graph_repo.list_concepts("dsa")) == 69
    edges = await graph_repo.list_edges("dsa")
    assert sum(e.type == PREREQUISITE for e in edges) == 111
    assert sum(e.type == RELATED for e in edges) == 15  # BUG-042

    # the canonical demo chain: functions -> call_stack -> recursion -> dfs_tree_traversals
    deps = {p.concept.id: p.depth for p in await graph_repo.get_dependents("call_stack", depth=3)}
    assert deps["recursion"] == 1
    assert deps["dfs_tree_traversals"] == 2
    prereqs = {p.concept.id for p in await graph_repo.get_prerequisites("dfs_tree_traversals", 4)}
    assert {"recursion", "call_stack", "functions"} <= prereqs

    order = await graph_repo.topological_order("dsa")
    assert len(order) == 69
    pos = {c: i for i, c in enumerate(order)}
    for c in doc.concepts:
        for p in c.prerequisites:
            assert pos[p] < pos[c.id]


# ----------------------------------------------------------------------- chunk seeding
async def test_seed_chunks_is_idempotent_and_removes_stale_chunks(
    graph_repo: GraphRepository, isolated_subject: str
) -> None:
    from app.content.notes import Chunk
    from app.graph.seed import seed_chunks

    sid = isolated_subject
    await seed_subject(graph_repo, doc_for(sid, [("a", "b")]))

    def chunk(concept: str, kind: str, order: int) -> Chunk:
        return Chunk(
            id=f"{sid}_{concept}#{kind}",
            concept_id=f"{sid}_{concept}",
            subject_id=sid,
            kind=kind,
            heading=kind.title(),
            text=f"{kind} text",
            order=order,
            reviewed=False,
        )

    first = [chunk("a", "overview", 0), chunk("a", "intuition", 1), chunk("b", "overview", 0)]
    assert await seed_chunks(graph_repo, first) == (3, 0)
    assert await seed_chunks(graph_repo, first) == (3, 0)
    got = await graph_repo.get_chunks([f"{sid}_a", f"{sid}_b"])
    assert len(got) == 3
    # the 'intuition' section was removed from the note: its chunk must disappear
    assert await seed_chunks(graph_repo, [first[0], first[2]]) == (2, 1)
    assert [c.kind for c in await graph_repo.get_chunks([f"{sid}_a"])] == ["overview"]
