from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

_redis_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    client = get_redis_pool()
    try:
        yield client
    finally:
        pass  # pool manages connections


async def cache_get(key: str) -> str | None:
    client = get_redis_pool()
    return await client.get(key)


async def cache_set(key: str, value: str, ttl: int = 300) -> None:
    client = get_redis_pool()
    await client.set(key, value, ex=ttl)


async def cache_delete(key: str) -> None:
    client = get_redis_pool()
    await client.delete(key)


async def cache_delete_pattern(pattern: str) -> None:
    client = get_redis_pool()
    cursor = 0
    while True:
        cursor, keys = await client.scan(cursor, match=pattern, count=100)
        if keys:
            await client.delete(*keys)
        if cursor == 0:
            break
