"""Async SQLAlchemy engine / session factory, safe behind the Supabase transaction pooler.

CLAUDE.md rule 6: with pgbouncer in transaction mode, prepared statements break, so asyncpg's
statement cache is disabled (`statement_cache_size=0`) as is SQLAlchemy's
(`prepared_statement_cache_size=0`). This is the ONE place engines are built; the health check
reuses it.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


class DatabaseNotConfiguredError(RuntimeError):
    pass


def to_async_url(url: str) -> str:
    """Normalise a Postgres URL to the SQLAlchemy asyncpg driver form."""
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+asyncpg://" + url[len(prefix) :]
    return url


def to_asyncpg_dsn(url: str) -> str:
    """Plain DSN for asyncpg.connect (no SQLAlchemy driver suffix)."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "postgres://", "postgresql://", 1
    )


def create_engine(url: str, *, pool_size: int = 5, max_overflow: int = 5) -> AsyncEngine:
    return create_async_engine(
        to_async_url(url),
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
    )


def engine_from_settings(settings: Settings) -> AsyncEngine:
    if not settings.database_url:
        raise DatabaseNotConfiguredError("DATABASE_URL is not set")
    return create_engine(settings.database_url)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
