"""Queries are parameterised: f-strings that build SQL or Cypher may only interpolate trusted
constants (Phase 13 security review). Values always travel as driver parameters ($id, :name).

Any new interpolated name inside a query string fails this test until it is reviewed and added to
ALLOWED with the reason it cannot carry user input.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
# Cypher keywords (always upper case in this code base) or the shape of an SQL statement.
QUERY = re.compile(
    r"\b(MATCH|MERGE|DETACH DELETE|UNWIND)\b"
    r"|(?i:\bselect\b.+\bfrom\b|\binsert\s+into\b|\bupdate\s+\w+\s+set\b|\bdelete\s+from\b)"
)
ALLOWED = {
    "PREREQUISITE",  # relationship type constants
    "RELATED",
    "MAX_CYCLE_SEARCH",  # int constant
    "d",  # depth, clamped to an int by _depth()
    "pattern",  # built only from the names above
    "table_ident",  # scripts/backup.py: a pg_tables name checked against a strict identifier regex
}


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {
        n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)
    }


def query_fstring_problems(source: str, label: str) -> list[str]:
    problems: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.JoinedStr):
            continue
        literal = "".join(
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
        if not QUERY.search(literal):
            continue
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                bad = _names(value.value) - ALLOWED
                if bad:
                    problems.append(f"{label}:{node.lineno} interpolates {sorted(bad)}")
    return problems


def test_query_fstrings_only_interpolate_trusted_constants() -> None:
    problems: list[str] = []
    for base in (APP, SCRIPTS):
        for path in base.rglob("*.py"):
            problems += query_fstring_problems(path.read_text(encoding="utf-8"), path.name)
    assert problems == [], "\n".join(problems)


def test_the_check_catches_interpolated_values() -> None:
    bad = "q = f\"MATCH (c:Concept {{id: '{concept_id}'}}) RETURN c\"\n"
    bad += "r = f\"select * from users where email = '{email}'\"\n"
    assert len(query_fstring_problems(bad, "x")) == 2
    ok = 'q = f"MATCH (a)-[:{PREREQUISITE}*1..{d}]->(b) WHERE b.id = $id RETURN a"\n'
    ok += 'm = f"please update {thing} later"\n'
    assert query_fstring_problems(ok, "x") == []
