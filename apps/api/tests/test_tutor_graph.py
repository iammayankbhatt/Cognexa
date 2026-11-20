"""Neo4j-backed tutor queries (fulltext search, exact prerequisite paths) and their parity with the
in-memory graph used by offline evaluation; the concept catalogue and its cache."""

from __future__ import annotations

import pytest

from app.graph.memory import InMemoryGraph
from app.graph.models import ConceptDef, ConceptFile, GraphEdge, SubjectDef
from app.graph.repository import PREREQUISITE, GraphRepository
from app.graph.seed import seed_subject
from app.llm.embeddings import FakeEmbeddingProvider
from app.tutor.catalogue import CATALOGUE_HEADER, CatalogueCache
from app.tutor.trace import ConceptMatch
from app.tutor.traverse import traverse


def concept_file(sid: str) -> ConceptFile:
    """loops → recursion → memo;  frames → recursion;  loops → trees;  recursion ~ trees."""

    def c(name: str, order: int, aliases: list[str], keywords: list[str], prereqs: list[str],
          related: list[str] | None = None) -> ConceptDef:  # fmt: skip
        return ConceptDef(
            id=f"{sid}_{name}", name=name.replace("_", " ").title(), cluster="test", difficulty=1,
            order_index=order, description=f"Test concept {name} for the tutor graph tests.",
            aliases=aliases, keywords=keywords, prerequisites=[f"{sid}_{p}" for p in prereqs],
            related=[f"{sid}_{r}" for r in related or []],
        )  # fmt: skip

    return ConceptFile(
        subject=SubjectDef(id=sid, name="Tutor test subject"),
        roots=[f"{sid}_loops", f"{sid}_frames"],
        concepts=[
            c("loops", 0, ["iteration"], ["for loop"], []),
            c("frames", 1, ["stack frames"], ["maximum recursion depth exceeded"], []),
            c(
                "recursion",
                2,
                ["recursive function"],
                ["base case"],
                ["loops", "frames"],
                ["trees"],
            ),
            c("memo", 3, ["memoization"], ["cache results"], ["recursion"]),
            c("trees", 4, ["tree"], ["root node"], ["loops"]),
        ],
    )


@pytest.fixture
async def seeded(graph_repo: GraphRepository, isolated_subject: str) -> tuple[str, ConceptFile]:
    doc = concept_file(isolated_subject)
    await seed_subject(graph_repo, doc)
    return isolated_subject, doc


async def test_prerequisite_paths_match_in_memory_graph(
    graph_repo: GraphRepository, seeded: tuple[str, ConceptFile]
) -> None:
    sid, doc = seeded
    mem = InMemoryGraph(doc)
    for cid in (f"{sid}_memo", f"{sid}_recursion"):
        neo = await graph_repo.get_prerequisites(cid, depth=2)
        ram = await mem.get_prerequisites(cid, depth=2)
        assert [(p.concept.id, p.depth, p.path_ids) for p in neo] == [
            (p.concept.id, p.depth, p.path_ids) for p in ram
        ]
    deep = await graph_repo.get_prerequisites(f"{sid}_memo", depth=2)
    loops = next(p for p in deep if p.concept.id == f"{sid}_loops")
    assert loops.path_ids == [f"{sid}_loops", f"{sid}_recursion", f"{sid}_memo"]


async def test_traverse_on_neo4j_ignores_proposed_edges(
    graph_repo: GraphRepository, seeded: tuple[str, ConceptFile]
) -> None:
    sid, _ = seeded
    await graph_repo.upsert_edge(
        GraphEdge(
            source=f"{sid}_trees",
            target=f"{sid}_memo",
            type=PREREQUISITE,
            status="proposed",
            source_kind="llm",
        )
    )
    matched = [ConceptMatch(id=f"{sid}_memo", name="Memo", confidence=0.9)]
    concepts = await traverse(graph_repo, matched, {f"{sid}_frames": 0.9}, depth=2)
    by_id = {c.id: c for c in concepts}
    assert f"{sid}_trees" not in by_id  # only via a proposed edge (and not related to memo)
    assert by_id[f"{sid}_recursion"].weak is True and by_id[f"{sid}_frames"].weak is False
    prereqs = [c.id for c in concepts if c.role == "prerequisite"]
    assert prereqs.index(f"{sid}_loops") < prereqs.index(f"{sid}_frames")  # weak first


async def test_fulltext_search_finds_aliases_and_keywords(
    graph_repo: GraphRepository, seeded: tuple[str, ConceptFile]
) -> None:
    sid, _ = seeded
    hits = await graph_repo.search_concepts(sid, "my code says maximum recursion depth exceeded")
    assert hits and hits[0][0] in {f"{sid}_frames", f"{sid}_recursion"}
    assert f"{sid}_frames" in [h[0] for h in hits]
    assert (await graph_repo.search_concepts(sid, "memoization"))[0][0] == f"{sid}_memo"
    # Lucene syntax in user text cannot break the query; stopwords alone return nothing
    assert await graph_repo.search_concepts(sid, 'title:"x" AND (* OR ~) \\') == []
    assert await graph_repo.search_concepts(sid, "what is the") == []
    # other subjects are not searched
    assert await graph_repo.search_concepts("no_such_subject", "memoization") == []


async def test_catalogue_cache_formats_and_reuses_vectors(
    graph_repo: GraphRepository, seeded: tuple[str, ConceptFile]
) -> None:
    sid, _ = seeded
    now = [0.0]
    cache = CatalogueCache(ttl_s=10, clock=lambda: now[0])
    cat = await cache.get(graph_repo, sid)
    lines = cat.text.splitlines()
    assert lines[0] == CATALOGUE_HEADER and len(lines) == 6
    assert lines[3].startswith(f"{sid}_recursion | Recursion | recursive function | base case |")
    assert await cache.get(graph_repo, sid) is cat  # cached
    embedder = FakeEmbeddingProvider(dim=32)
    vectors = await cat.ensure_vectors(embedder)
    now[0] = 11.0  # expired, but nothing changed: vectors are kept
    again = await cache.get(graph_repo, sid)
    assert again is not cat and again.vectors is vectors
    nearest = await again.nearest((await embedder.embed(["memoization"]))[0], embedder, k=2)
    assert len(nearest) == 2
    cache.invalidate(sid)
    assert (await cache.get(graph_repo, sid)).vectors is None


async def test_syllabus_queries_match_in_memory_graph(
    graph_repo: GraphRepository, seeded: tuple[str, ConceptFile]
) -> None:
    sid, doc = seeded
    mem = InMemoryGraph(doc)
    assert await graph_repo.topological_order(sid) == await mem.topological_order(sid)
    neo = {(e.source, e.target, e.type) for e in await graph_repo.list_edges(sid)}
    ram = {(e.source, e.target, e.type) for e in await mem.list_edges(sid)}
    assert neo == ram
