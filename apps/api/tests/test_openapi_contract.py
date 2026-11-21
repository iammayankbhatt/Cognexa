"""The committed OpenAPI schema (source of the web app's generated types) matches the API."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "export_openapi.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_openapi", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_schema_export_is_deterministic() -> None:
    mod = _load()
    assert mod.schema_text() == mod.schema_text()


def test_committed_schema_is_current() -> None:
    mod = _load()
    committed = mod.OUT.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == mod.schema_text(), (
        "apps/web/src/lib/api-contract/openapi.json is stale: run scripts/export_openapi.py "
        "and `npm run api:types` in apps/web"
    )


def test_request_bodies_reject_unknown_fields() -> None:
    """Web call sites rely on `satisfies Body<...>`; extra='forbid' keeps both sides strict."""
    schema = json.loads(_load().schema_text())
    used_by_web = ["MePatch", "OnboardingIn", "SessionIn", "AnswerIn", "EdgeIn", "DecisionIn"]
    for name in used_by_web:
        assert schema["components"]["schemas"][name].get("additionalProperties") is False, name


def test_api_docs_reference_is_current() -> None:
    """docs/API.md's generated half matches the app (scripts/gen_api_docs.py)."""
    script = SCRIPT.parent / "gen_api_docs.py"
    spec = importlib.util.spec_from_file_location("gen_api_docs", script)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    current = mod.DOC.read_text(encoding="utf-8").replace("\r\n", "\n")
    expected = current.split(mod.MARKER, 1)[0] + mod.render()
    assert expected == current, "docs/API.md is stale: run scripts/gen_api_docs.py"
