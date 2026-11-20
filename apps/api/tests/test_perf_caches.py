"""Phase 13 performance caches: the per-request app_settings snapshot and the syllabus cache."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.core.config import Settings
from app.db.repositories import (
    AppSettingsRepository,
    close_settings_snapshot,
    open_settings_snapshot,
)
from app.graph.models import GraphConcept, GraphEdge
from app.graph.provider import SYLLABUS_TTL_S, GraphProvider


class FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def __iter__(self) -> Any:
        return iter(self._rows)


class FakeSession:
    """Counts statements; answers both the single-key and the whole-table query."""

    def __init__(self, table: dict[str, dict[str, Any]]) -> None:
        self.table = table
        self.statements = 0

    async def execute(self, stmt: Any) -> FakeResult:
        self.statements += 1
        sql = str(stmt)
        if "app_settings.key, app_settings.value" in sql:
            return FakeResult([SimpleNamespace(key=k, value=v) for k, v in self.table.items()])
        if sql.startswith("INSERT"):
            return FakeResult([])
        key = stmt.compile().params["key_1"]
        return FakeResult([(self.table[key],)] if key in self.table else [])


TABLE = {"quota": {"daily": 30}, "features": {"AGENTIC_MODE": True}, "cache": {"ttl": 3600}}


async def test_outside_a_request_every_read_hits_the_database() -> None:
    session = FakeSession(TABLE)
    repo = AppSettingsRepository(session)  # type: ignore[arg-type]
    assert await repo.get("quota") == {"daily": 30}
    assert await repo.get("quota") == {"daily": 30}
    assert session.statements == 2


async def test_inside_a_request_the_table_is_read_once() -> None:
    session = FakeSession(TABLE)
    token = open_settings_snapshot()
    try:
        for _ in range(3):  # three different callers, as in /me before the fix
            repo = AppSettingsRepository(session)  # type: ignore[arg-type]
            assert await repo.get("quota") == {"daily": 30}
            assert await repo.get("features") == {"AGENTIC_MODE": True}
            assert await repo.get("missing") is None
        assert session.statements == 1
        # a write in the same request is visible to later reads of that request
        await repo.set("quota", {"daily": 5})
        assert await repo.get("quota") == {"daily": 5}
        # callers cannot corrupt the snapshot by mutating what they got back
        got = await repo.get("cache")
        assert got is not None
        got["ttl"] = 0
        assert await repo.get("cache") == {"ttl": 3600}
    finally:
        close_settings_snapshot(token)
    # the next request starts fresh
    token = open_settings_snapshot()
    try:
        await AppSettingsRepository(session).get("quota")  # type: ignore[arg-type]
        assert session.statements == 3  # 1 (first request) + 1 insert + 1 reload
    finally:
        close_settings_snapshot(token)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class CountingRepo:
    def __init__(self) -> None:
        self.calls = 0

    async def list_concepts(self, subject_id: str) -> list[GraphConcept]:
        self.calls += 1
        return [GraphConcept(id="stack", subject_id=subject_id, name="Stack", cluster="linear",
                             difficulty=1, order_index=1, description="LIFO")]  # fmt: skip

    async def list_edges(self, subject_id: str) -> list[GraphEdge]:
        return []

    async def get_concept(self, concept_id: str) -> str:
        return f"passthrough:{concept_id}"


def provider_with(repo: CountingRepo, clock: Clock) -> GraphProvider:
    p = GraphProvider(Settings(_env_file=None), clock=clock)
    p.repository = lambda: repo  # type: ignore[assignment,return-value]
    return p


async def test_syllabus_is_cached_until_ttl_or_invalidation() -> None:
    repo, clock = CountingRepo(), Clock()
    provider = provider_with(repo, clock)
    for _ in range(5):
        concepts = await provider.syllabus().list_concepts("dsa")
        assert [c.id for c in concepts] == ["stack"]
    assert repo.calls == 1
    assert await provider.syllabus().get_concept("stack") == "passthrough:stack"
    provider.invalidate("dsa")  # the admin graph editor does this after every change
    await provider.syllabus().list_concepts("dsa")
    assert repo.calls == 2
    clock.now += SYLLABUS_TTL_S + 1  # other writers (seed scripts) appear after the TTL
    await provider.syllabus().list_edges("dsa")
    assert repo.calls == 3
    # callers get their own list, so mutating it cannot change the cache
    mine = await provider.syllabus().list_concepts("dsa")
    mine.clear()
    assert len(await provider.syllabus().list_concepts("dsa")) == 1
