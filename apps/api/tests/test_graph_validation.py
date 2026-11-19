import itertools
import subprocess
import sys
from pathlib import Path

import pytest

from app.graph.loader import REPO_ROOT, concepts_path, load_concept_file, load_subject
from app.graph.models import ConceptDef, ConceptFile, SubjectDef
from app.graph.validation import (
    find_cycle,
    topological_order,
    validate_concept_file,
    would_create_cycle,
)

FIXTURES = Path(__file__).parent / "fixtures"


def mk(
    cid: str,
    prereqs: list[str] | None = None,
    related: list[str] | None = None,
    cluster: str = "c",
    oi: int | None = None,
) -> ConceptDef:
    return ConceptDef(
        id=cid,
        name=cid.upper(),
        cluster=cluster,
        difficulty=1,
        order_index=oi,
        description="A concept used in a validation test.",
        prerequisites=prereqs or [],
        related=related or [],
    )


def doc(*concepts: ConceptDef, roots: list[str] | None = None) -> ConceptFile:
    return ConceptFile(
        subject=SubjectDef(id="t", name="T"), roots=roots or [], concepts=list(concepts)
    )


def errors(d: ConceptFile) -> str:
    return "\n".join(validate_concept_file(d).errors)


# ----------------------------------------------------------------- the real graph
def test_real_dsa_graph_is_valid() -> None:
    report = validate_concept_file(load_subject("dsa"))
    assert report.errors == []
    assert report.stats.nodes == 69
    assert len(report.stats.clusters) == 8
    assert report.stats.roots == ["discrete_math_basics", "variables_memory"]
    assert report.stats.max_depth >= 8


def test_canonical_demo_chain_is_ordered() -> None:
    by_id = {c.id: c for c in load_subject("dsa").concepts}
    chain = ["functions", "call_stack", "recursion", "dfs_tree_traversals"]
    indexes = [by_id[c].order_index for c in chain]
    assert None not in indexes
    assert indexes == sorted(indexes)
    for a, b in itertools.pairwise(chain):
        assert a in by_id[b].prerequisites


def test_call_stack_keywords_cover_unnamed_prerequisite_symptoms() -> None:
    call_stack = next(c for c in load_subject("dsa").concepts if c.id == "call_stack")
    kws = " ".join(call_stack.keywords).lower()
    assert "recursionerror" in kws and "stack overflow" in kws


def test_order_index_file_is_up_to_date() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "assign_order_index.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout


# ----------------------------------------------------------------- individual rules
def test_duplicate_ids_rejected() -> None:
    d = doc(mk("a", oi=0), mk("a", oi=1), roots=["a"])
    assert "duplicate id: a" in errors(d)


def test_unknown_reference_rejected() -> None:
    d = doc(mk("a", oi=0), mk("b", ["ghost"], oi=1), roots=["a"])
    assert "unknown id 'ghost' in prerequisites" in errors(d)
    d2 = doc(mk("a", oi=0), mk("b", ["a"], ["ghost"], oi=1), roots=["a"])
    assert "unknown id 'ghost' in related" in errors(d2)


def test_cycle_is_reported_with_path() -> None:
    d = doc(
        mk("root", oi=0),
        mk("a", ["root", "c"], oi=1),
        mk("b", ["a"], oi=2),
        mk("c", ["b"], oi=3),
        roots=["root"],
    )
    msg = errors(d)
    assert "prerequisite cycle:" in msg
    assert " -> " in msg


def test_self_prerequisite_and_self_related_rejected() -> None:
    d = doc(mk("a", oi=0), mk("b", ["a", "b"], oi=1), roots=["a"])
    assert "b: is its own prerequisite" in errors(d)
    d2 = doc(mk("a", oi=0), mk("b", ["a"], ["b"], oi=1), roots=["a"])
    assert "b: is its own related concept" in errors(d2)


def test_orphan_rejected_unless_designated_root() -> None:
    d = doc(mk("a", oi=0), mk("lonely", oi=1), roots=["a"])
    assert "lonely: orphan" in errors(d)
    d2 = doc(mk("a", oi=0), mk("lonely", oi=1), roots=["a", "lonely"])
    assert "orphan" not in errors(d2)


def test_non_root_without_prerequisites_rejected() -> None:
    d = doc(mk("a", oi=0), mk("b", ["a"], oi=1), mk("c", oi=2), roots=["a"])
    assert "c: has no prerequisites but is not a designated root" in errors(d)


def test_designated_root_with_prerequisites_rejected() -> None:
    d = doc(mk("a", oi=0), mk("b", ["a"], oi=1), roots=["a", "b"])
    assert "'b' is designated a root but has prerequisites" in errors(d)


def test_order_index_violation_rejected() -> None:
    d = doc(mk("a", oi=5), mk("b", ["a"], oi=2), roots=["a"])
    assert "order_index violation: prerequisite 'a' (5) must come before 'b' (2)" in errors(d)


def test_order_index_missing_and_duplicate_rejected() -> None:
    assert "order_index missing" in errors(doc(mk("a"), mk("b", ["a"]), roots=["a"]))
    assert "order_index 1 used by 2" in errors(
        doc(mk("a", oi=1), mk("b", ["a"], oi=1), roots=["a"])
    )


def test_prerequisite_and_related_overlap_rejected() -> None:
    d = doc(mk("a", oi=0), mk("b", ["a"], ["a"], oi=1), roots=["a"])
    assert "both a prerequisite and related" in errors(d)


def test_multiple_problems_are_all_reported() -> None:
    d = doc(mk("a", oi=0), mk("a", oi=1), mk("b", ["ghost"], oi=2), roots=["a"])
    assert len(validate_concept_file(d).errors) >= 2


def test_bad_schema_values_rejected_by_model() -> None:
    with pytest.raises(ValueError):
        mk("Bad-Id")
    with pytest.raises(ValueError):
        ConceptDef(
            id="x1", name="X", cluster="c", difficulty=9, description="long enough text here"
        )


# ----------------------------------------------------------------- algorithms
def test_topological_order_respects_edges_and_is_deterministic() -> None:
    concepts = [mk("c", ["b"]), mk("a"), mk("b", ["a"]), mk("d", ["a"], cluster="other")]
    first = topological_order(concepts)
    assert first == topological_order(concepts)
    pos = {x: i for i, x in enumerate(first)}
    assert pos["a"] < pos["b"] < pos["c"]
    assert pos["a"] < pos["d"]


def test_topological_order_raises_on_cycle() -> None:
    with pytest.raises(ValueError, match="cycle"):
        topological_order([mk("a", ["b"]), mk("b", ["a"])])


def test_find_cycle_none_for_dag_and_path_for_cycle() -> None:
    assert find_cycle({"a": [], "b": ["a"], "c": ["a", "b"]}) is None
    cyc = find_cycle({"a": ["c"], "b": ["a"], "c": ["b"]})
    assert cyc is not None and cyc[0] == cyc[-1]


def test_would_create_cycle() -> None:
    prereqs = {"a": [], "b": ["a"], "c": ["b"], "d": []}
    assert would_create_cycle(prereqs, "c", "a")  # c before a, but a is already before c
    assert would_create_cycle(prereqs, "a", "a")
    assert not would_create_cycle(prereqs, "a", "c")  # redundant but acyclic
    assert not would_create_cycle(prereqs, "d", "a")


# ----------------------------------------------------------------- the CLI script
def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_graph.py"), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_script_passes_on_real_file() -> None:
    result = run_script()
    assert result.returncode == 0, result.stdout
    assert "Nodes: 69" in result.stdout
    assert "OK: graph is valid" in result.stdout


def test_script_fails_on_cyclic_fixture() -> None:
    result = run_script(str(FIXTURES / "cyclic_concepts.yaml"))
    assert result.returncode == 1
    assert "prerequisite cycle:" in result.stdout


def test_script_missing_file_is_a_clear_error() -> None:
    result = run_script(str(FIXTURES / "nope.yaml"))
    assert result.returncode == 2
    assert "file not found" in result.stdout


def test_cyclic_fixture_loads_but_does_not_validate() -> None:
    d = load_concept_file(FIXTURES / "cyclic_concepts.yaml")
    assert not validate_concept_file(d).ok
    assert concepts_path("dsa").exists()
