from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import get_settings

# Module-level singleton pool — shared across the process to avoid repeatedly
# creating/closing TCP connections for every request.
_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        # decode_responses=True means Redis returns str instead of bytes,
        # which is what all callers in this codebase expect.
        _pool = aioredis.ConnectionPool.from_url(get_settings().redis_url, decode_responses=True)
    return _pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    """FastAPI dependency that yields a Redis client and always closes it after the request."""
    client: aioredis.Redis = aioredis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        # aclose() returns the connection to the pool; it does not destroy the pool itself
        await client.aclose()
