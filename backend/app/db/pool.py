import logging
from pathlib import Path

import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Return the application Postgres connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL, min_size=1, max_size=5)
    return _pool


async def init_db() -> None:
    """Apply the idempotent schema migration if Postgres is available."""
    try:
        pool = await get_pool()
        schema = Path(__file__).with_name("schema.sql").read_text()
        async with pool.acquire() as conn:
            await conn.execute(schema)
        logger.info("Database schema is up to date")
    except Exception as exc:
        logger.warning("Database initialization skipped: %s", exc)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
