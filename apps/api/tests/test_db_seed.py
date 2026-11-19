"""Postgres seeding: concept mirror + default app settings, on a throwaway database."""

from __future__ import annotations

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import create_engine, session_factory
from app.db.migrate import apply_migrations
from app.db.repositories import DEFAULT_APP_SETTINGS, AppSettingsRepository, ConceptMirrorRepository
from app.db.tables import concepts, content_chunks, subjects
from app.graph.loader import load_subject

from .conftest import requires_postgres

pytestmark = requires_postgres


@pytest.fixture
async def session(fresh_db_url: str):  # type: ignore[no-untyped-def]
    await apply_migrations(fresh_db_url)
    engine = create_engine(fresh_db_url)
    async with session_factory(engine)() as s:
        yield s
    await engine.dispose()


async def seed(s: AsyncSession) -> tuple[int, int]:
    doc = load_subject("dsa")
    async with s.begin():
        _, n = await ConceptMirrorRepository(s).upsert_from_file(doc)
        inserted = await AppSettingsRepository(s).ensure_defaults()
    return n, inserted


async def test_seed_twice_creates_no_duplicates(session: AsyncSession) -> None:
    first = await seed(session)
    second = await seed(session)
    assert first == (69, len(DEFAULT_APP_SETTINGS))
    assert second == (69, 0)
    assert (await session.execute(select(func.count()).select_from(concepts))).scalar_one() == 69
    assert (await session.execute(select(func.count()).select_from(subjects))).scalar_one() == 1


async def test_mirror_matches_the_yaml(session: AsyncSession) -> None:
    await seed(session)
    doc = load_subject("dsa")
    repo = ConceptMirrorRepository(session)
    assert await repo.count("dsa") == 69
    assert await repo.concept_ids("dsa") == [
        c.id for c in sorted(doc.concepts, key=lambda c: c.order_index or 0)
    ]
    row = (
        (await session.execute(select(concepts).where(concepts.c.id == "call_stack")))
        .mappings()
        .one()
    )
    assert row["cluster"] == "foundations" and row["subject_id"] == "dsa"


async def test_reseed_updates_changed_fields(session: AsyncSession) -> None:
    await seed(session)
    async with session.begin():
        await session.execute(
            concepts.update().where(concepts.c.id == "recursion").values(name="stale name")
        )
    await seed(session)
    name = (
        await session.execute(select(concepts.c.name).where(concepts.c.id == "recursion"))
    ).scalar_one()
    assert name == "Recursion"


async def test_default_settings_values(session: AsyncSession) -> None:
    await seed(session)
    repo = AppSettingsRepository(session)
    student = await repo.get("quota.student")
    assert student == {
        "daily_ai_requests": 40,
        "per_minute": 6,
        "max_input_chars": 2000,
        "max_output_tokens": 900,
    }
    assert await repo.get("quota.global_daily_cap") == {"ai_requests": 1500}
    assert await repo.get("quota.role_multipliers") == {"student": 1, "reviewer": 5, "admin": 5}
    assert await repo.get("does.not.exist") is None


async def test_admin_edits_survive_reseeding(session: AsyncSession) -> None:
    await seed(session)
    repo = AppSettingsRepository(session)
    async with session.begin():
        await repo.set("quota.global_daily_cap", {"ai_requests": 99})
    await seed(session)
    assert await repo.get("quota.global_daily_cap") == {"ai_requests": 99}


async def test_chunks_can_reference_seeded_concepts_but_not_unknown_ones(
    session: AsyncSession,
) -> None:
    await seed(session)
    async with session.begin():
        await session.execute(
            insert(content_chunks).values(
                id="call_stack#overview",
                concept_id="call_stack",
                subject_id="dsa",
                kind="overview",
                text="x",
            )
        )
    with pytest.raises(Exception, match="foreign key"):
        async with session.begin():
            await session.execute(
                insert(content_chunks).values(
                    id="ghost#overview",
                    concept_id="ghost",
                    subject_id="dsa",
                    kind="overview",
                    text="x",
                )
            )
