"""Redis 客户端：分布式锁 + 心跳缓存 + 频率限制."""
import time
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_pool: redis.ConnectionPool | None = None


async def get_redis_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    pool = await get_redis_pool()
    async with redis.Redis(connection_pool=pool) as client:
        yield client


class RedisLock:
    """SETNX 分布式锁."""

    def __init__(self, client: redis.Redis, key: str, ttl_sec: int = 60):
        self.client = client
        self.key = key
        self.ttl = ttl_sec
        self._token: str | None = None

    async def acquire(self) -> bool:
        self._token = str(time.time_ns())
        return bool(await self.client.set(self.key, self._token, nx=True, ex=self.ttl))

    async def release(self) -> None:
        if self._token is None:
            return
        # Lua script: only delete if value matches (we own the lock)
        lua = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
        await self.client.eval(lua, 1, self.key, self._token)

    async def extend(self, extra_sec: int) -> None:
        if self._token is None:
            return
        lua = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('expire', KEYS[1], ARGV[2]) else return 0 end"
        await self.client.eval(lua, 1, self.key, self._token, extra_sec)


class RateLimiter:
    """滑动窗口频率限制."""

    def __init__(self, client: redis.Redis, key: str, limit: int, window_sec: int = 60):
        self.client = client
        self.key = key
        self.limit = limit
        self.window = window_sec

    async def is_allowed(self) -> bool:
        now = time.time_ns()
        window_start = now - self.window * 1_000_000_000
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(self.key, "-inf", window_start)
        pipe.zcard(self.key)
        pipe.zadd(self.key, {str(now): now})
        pipe.expire(self.key, self.window + 1)
        counts = await pipe.execute()
        return counts[1] < self.limit
