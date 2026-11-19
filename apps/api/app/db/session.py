"""Per-application database handle and the FastAPI session dependency.

The engine is created lazily on first use (so importing the app never connects) and disposed on
shutdown. Endpoints that need Postgres depend on `get_session`; if DATABASE_URL is not configured
they fail with a clean 503 instead of a stack trace.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.db.engine import create_engine, session_factory


class Database:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

    @property
    def configured(self) -> bool:
        return bool(self._url)

    def sessions(self) -> async_sessionmaker[AsyncSession]:
        if not self._url:
            raise AppError("database_not_configured", "The database is not configured.", 503)
        if self._sessions is None:
            self._engine = create_engine(self._url)
            self._sessions = session_factory(self._engine)
        return self._sessions

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessions = None


def get_database(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request; commits on success, rolls back on error."""
    sessions = get_database(request).sessions()
    async with sessions() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
