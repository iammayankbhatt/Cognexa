"""Graph validation rules for concepts.yaml (CLAUDE.md rule 3: PREREQUISITE_OF must stay a DAG).

Pure Python so it is shared by scripts/validate_graph.py, the admin edge editor and tests.
"""

from __future__ import annotations

import contextlib
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field

from app.graph.models import ConceptDef, ConceptFile


@dataclass
class GraphStats:
    nodes: int = 0
    prerequisite_edges: int = 0
    related_edges: int = 0
    max_depth: int = 0
    roots: list[str] = field(default_factory=list)
    leaves: list[str] = field(default_factory=list)
    clusters: dict[str, int] = field(default_factory=dict)


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    stats: GraphStats = field(default_factory=GraphStats)

    @property
    def ok(self) -> bool:
        return not self.errors


def find_cycle(prereqs: dict[str, list[str]]) -> list[str] | None:
    """Return one cycle as [a, b, ..., a] if the prerequisite graph has one, else None.

    `prereqs[x]` lists the concepts that must come before x. Iterative DFS (no recursion limit).
    """
    white, gray, black = 0, 1, 2
    color: dict[str, int] = {n: white for n in prereqs}
    for start in prereqs:
        if color[start] != white:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = []
        while stack:
            node, idx = stack.pop()
            if idx == 0:
                color[node] = gray
                path.append(node)
            deps = [d for d in prereqs.get(node, []) if d in color]
            if idx < len(deps):
                stack.append((node, idx + 1))
                nxt = deps[idx]
                if color[nxt] == gray:
                    return [*path[path.index(nxt) :], nxt]
                if color[nxt] == white:
                    stack.append((nxt, 0))
            else:
                color[node] = black
                path.pop()
    return None


def topological_order(concepts: list[ConceptDef]) -> list[str]:
    """Deterministic teaching order: Kahn's algorithm, ties broken by cluster then file order.

    Raises ValueError if the prerequisite graph has a cycle.
    """
    ids = [c.id for c in concepts]
    known = set(ids)
    cluster_rank: dict[str, int] = {}
    for c in concepts:
        cluster_rank.setdefault(c.cluster, len(cluster_rank))
    file_pos = {c.id: i for i, c in enumerate(concepts)}
    indeg = {c.id: len([p for p in c.prerequisites if p in known]) for c in concepts}
    dependents: dict[str, list[str]] = defaultdict(list)
    for c in concepts:
        for p in c.prerequisites:
            if p in known:
                dependents[p].append(c.id)
    by_id = {c.id: c for c in concepts}

    def key(i: str) -> tuple[int, int]:
        return (cluster_rank[by_id[i].cluster], file_pos[i])

    ready = sorted((i for i, d in indeg.items() if d == 0), key=key)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for dep in dependents[node]:
            indeg[dep] -= 1
            if indeg[dep] == 0:
                ready.append(dep)
        ready.sort(key=key)
    if len(order) != len(ids):
        raise ValueError("prerequisite graph contains a cycle")
    return order


def _max_depth(prereqs: dict[str, list[str]], order: list[str]) -> int:
    depth: dict[str, int] = {}
    for node in order:
        depth[node] = 1 + max((depth[p] for p in prereqs[node] if p in depth), default=0)
    return max(depth.values(), default=0)


def validate_concept_file(doc: ConceptFile) -> ValidationReport:
    """Run every rule from Phase 2 part B and collect all problems (not just the first)."""
    report = ValidationReport()
    errors = report.errors
    concepts = doc.concepts
    ids = [c.id for c in concepts]
    known = set(ids)

    # duplicate ids
    for cid, n in Counter(ids).items():
        if n > 1:
            errors.append(f"duplicate id: {cid} appears {n} times")

    by_id = {c.id: c for c in concepts}

    # unknown references, self references, duplicate refs inside one list
    for c in concepts:
        for field_name, refs in (("prerequisites", c.prerequisites), ("related", c.related)):
            for ref in refs:
                if ref not in known:
                    errors.append(f"{c.id}: unknown id '{ref}' in {field_name}")
                elif ref == c.id:
                    kind = "prerequisite" if field_name == "prerequisites" else "related concept"
                    errors.append(f"{c.id}: is its own {kind}")
            for ref, n in Counter(refs).items():
                if n > 1:
                    errors.append(f"{c.id}: '{ref}' listed {n} times in {field_name}")
        overlap = set(c.prerequisites) & set(c.related)
        for ref in sorted(overlap):
            errors.append(f"{c.id}: '{ref}' is both a prerequisite and related")

    # unknown roots
    for r in doc.roots:
        if r not in known:
            errors.append(f"roots: unknown id '{r}'")

    prereqs = {c.id: [p for p in c.prerequisites if p in known and p != c.id] for c in concepts}

    # cycles
    cycle = find_cycle(prereqs)
    if cycle:
        errors.append("prerequisite cycle: " + " -> ".join(cycle))

    # dependents / orphans / roots
    dependents: dict[str, list[str]] = defaultdict(list)
    for cid, deps in prereqs.items():
        for p in deps:
            dependents[p].append(cid)
    designated = set(doc.roots)
    for c in concepts:
        if not prereqs[c.id] and c.id not in designated:
            errors.append(f"{c.id}: has no prerequisites but is not a designated root")
        if not prereqs[c.id] and not dependents[c.id] and c.id not in designated:
            errors.append(f"{c.id}: orphan (no prerequisites and nothing depends on it)")
    for r in designated:
        if r in by_id and prereqs[r]:
            errors.append(f"roots: '{r}' is designated a root but has prerequisites")

    # order_index: present, unique, respects prerequisite order
    missing = [c.id for c in concepts if c.order_index is None]
    if missing:
        errors.append(
            f"order_index missing for: {', '.join(missing[:8])}{' ...' if len(missing) > 8 else ''}"
        )
    else:
        for oi, n in Counter(c.order_index for c in concepts).items():
            if n > 1:
                errors.append(f"order_index {oi} used by {n} concepts")
        for c in concepts:
            for p in prereqs[c.id]:
                po, co = by_id[p].order_index, c.order_index
                if po is not None and co is not None and po >= co:
                    errors.append(
                        f"order_index violation: prerequisite '{p}' ({po}) "
                        f"must come before '{c.id}' ({co})"
                    )

    # stats (best effort even when errors exist)
    stats = report.stats
    stats.nodes = len(concepts)
    stats.prerequisite_edges = sum(len(v) for v in prereqs.values())
    related_pairs = {
        frozenset((c.id, r)) for c in concepts for r in c.related if r in known and r != c.id
    }
    stats.related_edges = len(related_pairs)
    stats.roots = sorted(c.id for c in concepts if not prereqs[c.id])
    stats.leaves = sorted(c.id for c in concepts if prereqs[c.id] and not dependents[c.id])
    stats.clusters = dict(Counter(c.cluster for c in concepts))
    if not cycle:
        with contextlib.suppress(ValueError):
            stats.max_depth = _max_depth(prereqs, topological_order(concepts))
    return report


def would_create_cycle(prereqs: dict[str, list[str]], before: str, after: str) -> bool:
    """True if adding `before` -[:PREREQUISITE_OF]-> `after` would create a cycle.

    A cycle appears iff `before` is already reachable from `after` by following dependents,
    i.e. `after` is already a (transitive) prerequisite of `before`, or they are the same node.
    """
    if before == after:
        return True
    seen = {before}
    queue = deque([before])
    while queue:
        node = queue.popleft()
        for p in prereqs.get(node, []):
            if p == after:
                return True
            if p not in seen:
                seen.add(p)
                queue.append(p)
    return False
