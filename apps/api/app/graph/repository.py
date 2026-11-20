"""GraphRepository: every Neo4j query the application needs, typed and parameterised.

Rules (CLAUDE.md): `(A)-[:PREREQUISITE_OF]->(B)` means A is learned before B and the graph must
stay a DAG. No Cypher is built from user text. The only interpolated values are integer
path-length bounds, because Cypher cannot parameterise `*1..N`; they are clamped integers.
"""

from __future__ import annotations

import heapq
import re
from collections.abc import Iterable
from typing import Any

from neo4j import AsyncDriver, AsyncManagedTransaction
from neo4j import exceptions as neo4j_exceptions
from pydantic import BaseModel

from app.graph.models import ConceptDef, GraphConcept, GraphEdge, Subgraph

PREREQUISITE = "PREREQUISITE_OF"
RELATED = "RELATED_TO"

# Errors that mean "the graph database cannot be reached right now" (paused Aura instance, network
# failure, expired session), as opposed to a bug in a query. Callers may degrade on these.
GRAPH_UNAVAILABLE: tuple[type[BaseException], ...] = (
    neo4j_exceptions.ServiceUnavailable,
    neo4j_exceptions.SessionExpired,
    neo4j_exceptions.DatabaseUnavailable,
    ConnectionError,
    TimeoutError,
)
MAX_DEPTH = 10
MAX_CYCLE_SEARCH = 100


class CycleError(ValueError):
    """Adding the edge would make PREREQUISITE_OF cyclic."""


class UnknownConceptError(KeyError):
    pass


class PathConcept(BaseModel):
    """A concept reached by walking prerequisite edges, with its distance from the start."""

    concept: GraphConcept
    depth: int
    # Concept ids along one shortest path, in edge direction (prerequisite first), e.g. walking
    # prerequisites of recursion: ["functions", "call_stack", "recursion"].
    path_ids: list[str] = []


class ChunkRecord(BaseModel):
    id: str
    concept_id: str
    subject_id: str
    kind: str
    heading: str
    text: str
    order: int = 0
    reviewed: bool = False
    source: str = "notes"  # notes | llm | admin; seeding only replaces "notes" chunks


_LUCENE_WORD = re.compile(r"[a-z0-9]+")
# Common English words carry no topic signal and would match many concepts in fulltext search.
STOPWORDS = frozenset(
    "the and for are but not you your with what why how does did can could would should when "  # noqa: SIM905
    "where which who whom this that these those there their them they then than its it's "
    "into from about over under have has had was were been being will just like get got make "
    "made use using used best good bad very much many more most some any all one two way "
    "thing things want need help please tell explain show give know think mean means work "
    "works ".split()
)


def _depth(value: int) -> int:
    return max(1, min(int(value), MAX_DEPTH))


def _concept(node: dict[str, Any]) -> GraphConcept:
    return GraphConcept(
        id=node["id"],
        subject_id=node["subject_id"],
        name=node["name"],
        cluster=node["cluster"],
        difficulty=node["difficulty"],
        order_index=node.get("order_index", 0),
        description=node.get("description", ""),
        aliases=list(node.get("aliases") or []),
        keywords=list(node.get("keywords") or []),
        status=node.get("status", "approved"),
    )


SCHEMA_STATEMENTS = [
    "CREATE CONSTRAINT subject_id IF NOT EXISTS FOR (s:Subject) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (k:Chunk) REQUIRE k.id IS UNIQUE",
    "CREATE INDEX concept_subject IF NOT EXISTS FOR (c:Concept) ON (c.subject_id)",
    "CREATE INDEX chunk_concept IF NOT EXISTS FOR (k:Chunk) ON (k.concept_id)",
    (
        "CREATE FULLTEXT INDEX concept_text IF NOT EXISTS FOR (c:Concept) "
        "ON EACH [c.name, c.aliases, c.keywords]"
    ),
]


class GraphRepository:
    def __init__(self, driver: AsyncDriver, database: str | None = None) -> None:
        self._driver = driver
        self._database = database

    def _session(self) -> Any:
        return (
            self._driver.session(database=self._database)
            if self._database
            else (self._driver.session())
        )

    async def _read(self, query: str, **params: Any) -> list[dict[str, Any]]:
        async with self._session() as session:

            async def work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
                result = await tx.run(query, **params)
                return [dict(r) async for r in result]

            rows: list[dict[str, Any]] = await session.execute_read(work)
            return rows

    async def _write(self, query: str, **params: Any) -> list[dict[str, Any]]:
        async with self._session() as session:

            async def work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
                result = await tx.run(query, **params)
                return [dict(r) async for r in result]

            rows: list[dict[str, Any]] = await session.execute_write(work)
            return rows

    # ------------------------------------------------------------------ schema
    async def ensure_schema(self) -> None:
        async with self._session() as session:
            for statement in SCHEMA_STATEMENTS:
                await session.run(statement)

    # ------------------------------------------------------------------ reads
    async def get_concept(self, concept_id: str) -> GraphConcept | None:
        rows = await self._read("MATCH (c:Concept {id: $id}) RETURN c", id=concept_id)
        return _concept(dict(rows[0]["c"])) if rows else None

    async def list_concepts(self, subject_id: str) -> list[GraphConcept]:
        rows = await self._read(
            "MATCH (c:Concept {subject_id: $sid}) RETURN c ORDER BY c.order_index", sid=subject_id
        )
        return [_concept(dict(r["c"])) for r in rows]

    async def _walk(self, concept_id: str, depth: int, *, toward: bool) -> list[PathConcept]:
        d = _depth(depth)
        pattern = (
            f"(o:Concept)-[:{PREREQUISITE}*1..{d}]->(c:Concept {{id: $id}})"
            if toward
            else f"(c:Concept {{id: $id}})-[:{PREREQUISITE}*1..{d}]->(o:Concept)"
        )
        rows = await self._read(
            f"MATCH path = {pattern} "
            "WHERE ALL(r IN relationships(path) WHERE r.status = 'approved') "
            "WITH o, path ORDER BY length(path) "
            "WITH o, collect(path)[0] AS p "
            "RETURN o AS concept, length(p) AS depth, [n IN nodes(p) | n.id] AS ids "
            "ORDER BY depth, o.order_index",
            id=concept_id,
        )
        return [
            PathConcept(
                concept=_concept(dict(r["concept"])), depth=r["depth"], path_ids=list(r["ids"])
            )
            for r in rows
        ]

    async def get_prerequisites(self, concept_id: str, depth: int = 2) -> list[PathConcept]:
        """Concepts that must be learned before `concept_id`, nearest first, up to `depth` hops."""
        return await self._walk(concept_id, depth, toward=True)

    async def get_dependents(self, concept_id: str, depth: int = 1) -> list[PathConcept]:
        """Concepts that build on `concept_id`, nearest first, up to `depth` hops."""
        return await self._walk(concept_id, depth, toward=False)

    async def get_related(self, concept_id: str) -> list[GraphConcept]:
        rows = await self._read(
            f"MATCH (c:Concept {{id: $id}})-[r:{RELATED}]-(o:Concept) "
            "WHERE r.status = 'approved' RETURN DISTINCT o ORDER BY o.order_index",
            id=concept_id,
        )
        return [_concept(dict(r["o"])) for r in rows]

    async def get_subgraph(self, concept_ids: Iterable[str], depth: int = 2) -> Subgraph:
        """The given concepts, their prerequisites up to `depth` hops and their direct related
        concepts, with all approved edges among those nodes."""
        seeds = list(dict.fromkeys(concept_ids))
        if not seeds:
            return Subgraph(concepts=[], edges=[])
        d = _depth(depth)
        node_ids: set[str] = set(seeds)
        pre = await self._read(
            f"MATCH path = (o:Concept)-[:{PREREQUISITE}*1..{d}]->(c:Concept) WHERE c.id IN $ids "
            "AND ALL(r IN relationships(path) WHERE r.status = 'approved') "
            "RETURN DISTINCT o.id AS id",
            ids=seeds,
        )
        node_ids.update(r["id"] for r in pre)
        rel = await self._read(
            f"MATCH (c:Concept)-[r:{RELATED}]-(o:Concept) WHERE c.id IN $ids "
            "AND r.status = 'approved' RETURN DISTINCT o.id AS id",
            ids=seeds,
        )
        node_ids.update(r["id"] for r in rel)

        concept_rows = await self._read(
            "MATCH (c:Concept) WHERE c.id IN $ids RETURN c ORDER BY c.order_index",
            ids=sorted(node_ids),
        )
        edge_rows = await self._read(
            f"MATCH (a:Concept)-[r:{PREREQUISITE}|{RELATED}]->(b:Concept) "
            "WHERE a.id IN $ids AND b.id IN $ids AND r.status = 'approved' "
            "RETURN a.id AS source, b.id AS target, type(r) AS type, r.weight AS weight, "
            "r.source AS source_kind, r.status AS status, r.rationale AS rationale "
            "ORDER BY type, source, target",
            ids=sorted(node_ids),
        )
        return Subgraph(
            concepts=[_concept(dict(r["c"])) for r in concept_rows],
            edges=[
                GraphEdge(
                    source=r["source"],
                    target=r["target"],
                    type=r["type"],
                    weight=r["weight"] if r["weight"] is not None else 1.0,
                    source_kind=r["source_kind"] or "human",
                    status=r["status"] or "approved",
                    rationale=r["rationale"],
                )
                for r in edge_rows
            ],
        )

    async def list_edges(self, subject_id: str) -> list[GraphEdge]:
        """Every edge between concepts of a subject, of any status (used by seeding and admin)."""
        rows = await self._read(
            f"MATCH (a:Concept {{subject_id: $sid}})-[r:{PREREQUISITE}|{RELATED}]->(b:Concept) "
            "RETURN a.id AS source, b.id AS target, type(r) AS type, r.weight AS weight, "
            "r.source AS source_kind, r.status AS status, r.rationale AS rationale "
            "ORDER BY type, source, target",
            sid=subject_id,
        )
        return [
            GraphEdge(
                source=r["source"],
                target=r["target"],
                type=r["type"],
                weight=r["weight"] if r["weight"] is not None else 1.0,
                source_kind=r["source_kind"] or "human",
                status=r["status"] or "approved",
                rationale=r["rationale"],
            )
            for r in rows
        ]

    async def search_concepts(
        self, subject_id: str, text: str, limit: int = 10
    ) -> list[tuple[str, float]]:
        """Fulltext search over concept name, aliases and keywords. Returns (id, score), best
        first. User text is reduced to plain words, so Lucene syntax cannot be injected."""
        words = [
            w for w in _LUCENE_WORD.findall(text.lower()) if len(w) > 2 and w not in STOPWORDS
        ][:30]
        if not words:
            return []
        rows = await self._read(
            "CALL db.index.fulltext.queryNodes('concept_text', $q) YIELD node, score "
            "WHERE node.subject_id = $sid AND coalesce(node.status, 'approved') = 'approved' "
            "RETURN node.id AS id, score ORDER BY score DESC LIMIT $limit",
            q=" OR ".join(words),
            sid=subject_id,
            limit=max(1, min(int(limit), 50)),
        )
        return [(r["id"], float(r["score"])) for r in rows]

    async def get_chunks(
        self, concept_ids: Iterable[str], kinds: Iterable[str] | None = None, limit: int = 50
    ) -> list[ChunkRecord]:
        rows = await self._read(
            "MATCH (c:Concept)-[:HAS_CHUNK]->(k:Chunk) "
            "WHERE c.id IN $ids AND ($kinds IS NULL OR k.kind IN $kinds) "
            "RETURN k ORDER BY c.order_index, k.`order` LIMIT $limit",
            ids=list(concept_ids),
            kinds=list(kinds) if kinds is not None else None,
            limit=max(1, min(int(limit), 500)),
        )
        return [ChunkRecord(**dict(r["k"])) for r in rows]

    async def topological_order(self, subject_id: str) -> list[str]:
        """Concept ids in a valid teaching order (every prerequisite before its dependents).

        Computed from the stored edges, ties broken by order_index. Raises CycleError on a cycle.
        """
        concepts = await self.list_concepts(subject_id)
        edge_rows = await self._read(
            f"MATCH (a:Concept {{subject_id: $sid}})-[r:{PREREQUISITE}]->(b:Concept) "
            "WHERE r.status = 'approved' RETURN a.id AS a, b.id AS b",
            sid=subject_id,
        )
        rank = {c.id: c.order_index for c in concepts}
        indeg = dict.fromkeys(rank, 0)
        out: dict[str, list[str]] = {c: [] for c in rank}
        for r in edge_rows:
            if r["a"] in rank and r["b"] in rank:
                out[r["a"]].append(r["b"])
                indeg[r["b"]] += 1
        heap = [(rank[c], c) for c, n in indeg.items() if n == 0]
        heapq.heapify(heap)
        order: list[str] = []
        while heap:
            _, node = heapq.heappop(heap)
            order.append(node)
            for nxt in out[node]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    heapq.heappush(heap, (rank[nxt], nxt))
        if len(order) != len(rank):
            raise CycleError("prerequisite graph contains a cycle")
        return order

    async def would_create_cycle(self, before: str, after: str) -> bool:
        """True if adding `before -[:PREREQUISITE_OF]-> after` would create a cycle.

        That happens when `after` is already (transitively) a prerequisite of `before`, over
        edges of any status (proposed edges count too, so approving them later can never
        create a cycle).
        """
        if before == after:
            return True
        rows = await self._read(
            f"MATCH p = (a:Concept {{id: $after}})-[:{PREREQUISITE}*1..{MAX_CYCLE_SEARCH}]->"
            "(b:Concept {id: $before}) RETURN count(p) > 0 AS cyclic",
            after=after,
            before=before,
        )
        return bool(rows and rows[0]["cyclic"])

    async def prerequisite_path(self, start: str, end: str) -> list[str]:
        """Concept ids on the shortest PREREQUISITE_OF chain start -> ... -> end ([] if none).

        Used to explain a rejected edge: adding end -> start would close this chain into a cycle.
        """
        if start == end:
            return [start]
        rows = await self._read(
            f"MATCH p = shortestPath((a:Concept {{id: $start}})"
            f"-[:{PREREQUISITE}*1..{MAX_CYCLE_SEARCH}]->(b:Concept {{id: $end}})) "
            "RETURN [n IN nodes(p) | n.id] AS ids",
            start=start,
            end=end,
        )
        return list(rows[0]["ids"]) if rows else []

    async def subject_name(self, subject_id: str) -> str | None:
        rows = await self._read("MATCH (s:Subject {id: $id}) RETURN s.name AS name", id=subject_id)
        return str(rows[0]["name"]) if rows and rows[0]["name"] is not None else None

    # ------------------------------------------------------------------ writes
    async def upsert_subject(self, subject_id: str, name: str) -> None:
        async with self._session() as session:
            await session.run(
                "MERGE (s:Subject {id: $id}) SET s.name = $name", id=subject_id, name=name
            )

    async def upsert_concept(self, subject_id: str, concept: ConceptDef) -> None:
        async with self._session() as session:
            await session.run(
                "MERGE (s:Subject {id: $sid}) "
                "MERGE (c:Concept {id: $id}) "
                "SET c.subject_id = $sid, c.name = $name, c.cluster = $cluster, "
                "c.difficulty = $difficulty, c.order_index = $order_index, "
                "c.description = $description, c.aliases = $aliases, c.keywords = $keywords, "
                "c.status = coalesce(c.status, 'approved') "
                "MERGE (s)-[:HAS_CONCEPT]->(c)",
                sid=subject_id,
                id=concept.id,
                name=concept.name,
                cluster=concept.cluster,
                difficulty=concept.difficulty,
                order_index=concept.order_index if concept.order_index is not None else 0,
                description=concept.description,
                aliases=concept.aliases,
                keywords=concept.keywords,
            )

    async def upsert_edge(self, edge: GraphEdge) -> None:
        """Create or update an edge. PREREQUISITE_OF edges that would create a cycle are rejected.

        RELATED_TO is stored once (smaller id -> larger id) and queried undirected.
        """
        if edge.type not in (PREREQUISITE, RELATED):
            raise ValueError(f"unknown edge type: {edge.type}")
        if edge.source == edge.target:
            raise ValueError("an edge cannot connect a concept to itself")

        async def work(tx: AsyncManagedTransaction) -> None:
            exists = await (
                await tx.run(
                    "MATCH (a:Concept {id: $a}), (b:Concept {id: $b}) RETURN count(*) AS n",
                    a=edge.source,
                    b=edge.target,
                )
            ).single()
            if exists is None or exists["n"] == 0:
                raise UnknownConceptError(f"{edge.source} or {edge.target}")
            props: dict[str, Any] = {
                "weight": edge.weight,
                "src": edge.source_kind,
                "status": edge.status,
                "rationale": edge.rationale,
            }
            if edge.type == PREREQUISITE:
                cyc = await (
                    await tx.run(
                        f"MATCH p = (a:Concept {{id: $target}})"
                        f"-[:{PREREQUISITE}*1..{MAX_CYCLE_SEARCH}]->"
                        "(b:Concept {id: $source}) RETURN count(p) > 0 AS cyclic",
                        target=edge.target,
                        source=edge.source,
                    )
                ).single()
                if cyc is not None and cyc["cyclic"]:
                    raise CycleError(f"{edge.source} -> {edge.target} would create a cycle")
                await tx.run(
                    f"MATCH (a:Concept {{id: $a}}), (b:Concept {{id: $b}}) "
                    f"MERGE (a)-[r:{PREREQUISITE}]->(b) "
                    "SET r.weight = $weight, r.source = $src, r.status = $status, "
                    "r.rationale = $rationale",
                    a=edge.source,
                    b=edge.target,
                    **props,
                )
            else:
                lo, hi = sorted((edge.source, edge.target))
                await tx.run(
                    f"MATCH (a:Concept {{id: $lo}}), (b:Concept {{id: $hi}}) "
                    f"OPTIONAL MATCH (a)-[old:{RELATED}]-(b) DELETE old "
                    f"CREATE (a)-[r:{RELATED}]->(b) "
                    "SET r.weight = $weight, r.source = $src, r.status = $status, "
                    "r.rationale = $rationale",
                    lo=lo,
                    hi=hi,
                    **props,
                )

        async with self._session() as session:
            await session.execute_write(work)

    async def delete_edge(self, source: str, target: str, edge_type: str) -> bool:
        if edge_type not in (PREREQUISITE, RELATED):
            raise ValueError(f"unknown edge type: {edge_type}")
        pattern = (
            f"(a:Concept {{id: $a}})-[r:{PREREQUISITE}]->(b:Concept {{id: $b}})"
            if edge_type == PREREQUISITE
            else f"(a:Concept {{id: $a}})-[r:{RELATED}]-(b:Concept {{id: $b}})"
        )

        async def work(tx: AsyncManagedTransaction) -> int:
            result = await tx.run(
                f"MATCH {pattern} DELETE r RETURN count(r) AS n", a=source, b=target
            )
            row = await result.single()
            return int(row["n"]) if row else 0

        async with self._session() as session:
            deleted: int = await session.execute_write(work)
            return deleted > 0

    async def upsert_chunk(self, chunk: ChunkRecord) -> None:
        """Create or update a chunk. Seeding from the notes (source 'notes') never overwrites a
        chunk that an admin edited (source 'admin') or that came from an approved proposal."""
        async with self._session() as session:
            await session.run(
                "MATCH (c:Concept {id: $concept_id}) "
                "MERGE (k:Chunk {id: $id}) "
                "WITH c, k WHERE $source <> 'notes' OR coalesce(k.source, 'notes') = 'notes' "
                "SET k.concept_id = $concept_id, k.subject_id = $subject_id, k.kind = $kind, "
                "k.heading = $heading, k.text = $text, k.`order` = $order, k.reviewed = $reviewed, "
                "k.source = $source "
                "MERGE (c)-[:HAS_CHUNK]->(k)",
                **chunk.model_dump(),
            )

    async def delete_stale_chunks(self, keep_ids_by_concept: dict[str, list[str]]) -> int:
        """Delete chunks of the given concepts that are not in the keep lists. Returns the count."""
        if not keep_ids_by_concept:
            return 0
        rows = await self._write(
            "MATCH (c:Concept)-[:HAS_CHUNK]->(k:Chunk) WHERE c.id IN $concepts "
            "AND NOT k.id IN $keep AND coalesce(k.source, 'notes') = 'notes' "
            "WITH k, k.id AS id DETACH DELETE k RETURN count(id) AS n",
            concepts=list(keep_ids_by_concept),
            keep=[i for ids in keep_ids_by_concept.values() for i in ids],
        )
        return int(rows[0]["n"]) if rows else 0

    async def wipe(self) -> None:
        """Delete every node and relationship. Destructive: callers must confirm first."""
        async with self._session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
