from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from redis.asyncio import ConnectionPool, Redis

from app.config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# ── Connection pool (shared across the app) ───────────────────────────────────

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> AsyncGenerator[Redis, None]:
    client: Redis = Redis(connection_pool=get_pool())
    try:
        yield client
    finally:
        await client.aclose()


# ── Health check ─────────────────────────────────────────────────────────────

async def check_redis_health() -> bool:
    try:
        client: Redis = Redis(connection_pool=get_pool())
        await client.ping()
        await client.aclose()
        return True
    except Exception:
        log.exception("Redis health check failed")
        return False


# ── High-level cache helpers ──────────────────────────────────────────────────

class CacheService:
    def __init__(self, redis: Redis, default_ttl: int = settings.redis_cache_ttl) -> None:
        self._r = redis
        self._ttl = default_ttl

    async def get(self, key: str) -> str | None:
        return await self._r.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self._r.set(key, value, ex=ttl or self._ttl)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        keys: list[str] = await self._r.keys(pattern)
        if keys:
            return await self._r.delete(*keys)
        return 0

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        val = await self._r.incrby(key, amount)
        if ttl and val == amount:
            await self._r.expire(key, ttl)
        return val

    async def get_int(self, key: str) -> int:
        val = await self._r.get(key)
        return int(val) if val else 0

    async def ttl(self, key: str) -> int:
        return await self._r.ttl(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._r.exists(key))

    # ── Rate limiting via atomic sliding window (Lua) ────────────────────────

    # Lua script: sorted-set sliding window. Atomic, no TOCTOU race.
    _SLIDING_WINDOW_LUA = """
local key     = KEYS[1]
local limit   = tonumber(ARGV[1])
local window  = tonumber(ARGV[2])
local now_ms  = tonumber(ARGV[3])
local member  = ARGV[4]
local cutoff  = now_ms - (window * 1000)
redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now_ms, member)
    redis.call('PEXPIRE', key, window * 1000)
    return {1, count + 1, 0}
end
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local retry_after = math.ceil((tonumber(oldest[2]) + window * 1000 - now_ms) / 1000)
return {0, count, math.max(retry_after, 1)}
"""

    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Returns (allowed, current_count, retry_after_seconds).
        Uses an atomic sliding window via a Lua script — no fixed-window
        boundary burst and no TOCTOU race between INCR and EXPIRE.
        """
        import time
        import uuid as _uuid

        now_ms = int(time.time() * 1000)
        member = f"{now_ms}-{_uuid.uuid4().hex[:8]}"

        result = await self._r.eval(
            self._SLIDING_WINDOW_LUA,
            1,
            key,
            str(limit),
            str(window_seconds),
            str(now_ms),
            member,
        )
        allowed = bool(result[0])
        count = int(result[1])
        retry_after = int(result[2])
        return allowed, count, retry_after
