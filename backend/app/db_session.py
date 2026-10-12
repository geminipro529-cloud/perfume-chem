"""Database session management"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Enable SQLite referential integrity for every newly opened connection."""

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# How long a connection waits for another connection's write lock before SQLite
# gives up with "database is locked". The API and the engine worker share one
# file; with SQLite's 5 s default, a worker saving a finished job under load gave
# up and the job was lost (stress test 2026-10-11).
SQLITE_BUSY_TIMEOUT_MS = 30_000


def _wait_for_sqlite_write_lock(dbapi_connection, _connection_record) -> None:
    """Make every newly opened connection wait for a held write lock."""

    cursor = dbapi_connection.cursor()
    cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
    cursor.close()

# Create async engine (SQLite doesn't support pool_size/max_overflow)
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_async_engine(settings.DATABASE_URL, echo=settings.DB_ECHO)
    event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
    event.listen(engine.sync_engine, "connect", _wait_for_sqlite_write_lock)
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )

# Create session factory
async_session_maker = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with async_session_maker() as session:
        yield session
