"""Supabase async client initialisation with connection pool and retry logic."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from supabase._async.client import AsyncClient as SupabaseClient
from supabase._async.client import create_client
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.utils.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/brain_tumor",
)

# ---------------------------------------------------------------------------
# SQLAlchemy async engine
# ---------------------------------------------------------------------------

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Supabase client (singleton)
# ---------------------------------------------------------------------------

_supabase_client: SupabaseClient | None = None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def get_supabase() -> SupabaseClient:
    """Return a cached Supabase async client with retry logic."""
    global _supabase_client  # noqa: PLW0603
    if _supabase_client is None:
        logger.info("supabase_client_init", url=SUPABASE_URL[:30] + "…")
        _supabase_client = await create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ---------------------------------------------------------------------------
# Health / warmup
# ---------------------------------------------------------------------------


async def warmup() -> None:
    """Verify DB connectivity at startup."""
    async with async_session_factory() as session:
        await session.execute(text("SELECT 1"))
    logger.info("database_warmup_ok")


async def shutdown() -> None:
    """Dispose of the connection pool on shutdown."""
    await engine.dispose()
    logger.info("database_shutdown")
