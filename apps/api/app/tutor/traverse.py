"""Stage 2: walk the prerequisite graph from the matched concepts and personalise the result.

For each matched concept: prerequisites up to `depth` hops (PREREQUISITE_OF walked backwards) and
related concepts one hop away, approved edges only. A prerequisite is *weak* when the student's
mastery score is below WEAK_THRESHOLD or they never practised it. Order:
matched concepts → weak prerequisites (nearest first) → other prerequisites → related.
The exact edge path from each prerequisite to its matched concept is recorded for the trace.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence

from app.tutor.graph_source import TutorGraph
from app.tutor.trace import ConceptMatch, TraceConcept, TraceEdge

WEAK_THRESHOLD = 0.6
PREREQUISITE_OF = "PREREQUISITE_OF"
RELATED_TO = "RELATED_TO"


def is_weak(concept_id: str, mastery: Mapping[str, float]) -> bool:
    score = mastery.get(concept_id)
    return score is None or score < WEAK_THRESHOLD


def path_edges(ids: Sequence[str]) -> list[TraceEdge]:
    return [TraceEdge(source=a, target=b, type=PREREQUISITE_OF) for a, b in itertools.pairwise(ids)]


async def traverse(
    graph: TutorGraph,
    matched: Sequence[ConceptMatch],
    mastery: Mapping[str, float],
    *,
    depth: int = 2,
) -> list[TraceConcept]:
    matched_ids = [m.id for m in matched]
    out: list[TraceConcept] = [
        TraceConcept(id=m.id, name=m.name, role="matched", depth=0, mastery=mastery.get(m.id))
        for m in matched
    ]
    prereqs: dict[str, TraceConcept] = {}
    order: dict[str, int] = {}
    for m in matched:
        for p in await graph.get_prerequisites(m.id, depth):
            cid = p.concept.id
            if cid in matched_ids:
                # One matched concept can be a prerequisite of another: it stays matched, and the
                # direct edge between them is recorded so the trace graph can draw it.
                if p.depth == 1:
                    out[matched_ids.index(cid)].path.extend(path_edges(p.path_ids))
                continue
            known = prereqs.get(cid)
            if known is not None and known.depth <= p.depth:
                continue
            prereqs[cid] = TraceConcept(
                id=cid,
                name=p.concept.name,
                role="prerequisite",
                depth=p.depth,
                weak=is_weak(cid, mastery),
                mastery=mastery.get(cid),
                path=path_edges(p.path_ids),
            )
            order[cid] = p.concept.order_index
    ranked = sorted(
        prereqs.values(),
        # weak first; nearest first; then the further-down-the-syllabus concept first, because it
        # is the more specific cause (call_stack before functions for recursion)
        key=lambda c: (not c.weak, c.depth, -order.get(c.id, 0), c.id),
    )
    out.extend(ranked)
    seen = set(matched_ids) | set(prereqs)
    for m in matched:
        for r in await graph.get_related(m.id):
            if r.id in seen:
                continue
            seen.add(r.id)
            out.append(
                TraceConcept(
                    id=r.id,
                    name=r.name,
                    role="related",
                    depth=1,
                    mastery=mastery.get(r.id),
                    path=[TraceEdge(source=m.id, target=r.id, type=RELATED_TO)],
                )
            )
    return out
