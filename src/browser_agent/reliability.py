from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

from .config import Settings, get_settings


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_seconds: int


class MemoryReliabilityStore:
    backend = "memory"

    def __init__(self):
        self._lock = Lock()
        self._counters: dict[str, tuple[int, float]] = {}
        self._locks: dict[str, tuple[str, float]] = {}

    def check_rate_limit(self, scope: str, limit: int, window_seconds: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(True, 0, window_seconds)
        now = time.monotonic()
        with self._lock:
            count, expires_at = self._counters.get(scope, (0, now + window_seconds))
            if expires_at <= now:
                count = 0
                expires_at = now + window_seconds
            count += 1
            self._counters[scope] = (count, expires_at)
            remaining = max(limit - count, 0)
            return RateLimitResult(count <= limit, remaining, max(1, int(expires_at - now)))

    def acquire_lock(self, key: str, owner: str, ttl_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            current = self._locks.get(key)
            if current and current[1] > now:
                return False
            self._locks[key] = (owner, now + ttl_seconds)
            return True

    def release_lock(self, key: str, owner: str) -> bool:
        with self._lock:
            current = self._locks.get(key)
            if not current or current[0] != owner:
                return False
            del self._locks[key]
            return True

    def status(self) -> dict:
        return {"backend": self.backend, "available": True}


class RedisReliabilityStore:
    backend = "redis"

    def __init__(self, redis_url: str):
        from redis import Redis

        self.redis_url = redis_url
        self.client = Redis.from_url(redis_url, decode_responses=True)

    def check_rate_limit(self, scope: str, limit: int, window_seconds: int) -> RateLimitResult:
        if limit <= 0:
            return RateLimitResult(True, 0, window_seconds)
        key = f"rate:{scope}:{int(time.time() // window_seconds)}"
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        count, _ = pipe.execute()
        count = int(count)
        return RateLimitResult(
            allowed=count <= limit,
            remaining=max(limit - count, 0),
            reset_seconds=window_seconds,
        )

    def acquire_lock(self, key: str, owner: str, ttl_seconds: int) -> bool:
        return bool(self.client.set(f"lock:{key}", owner, nx=True, ex=ttl_seconds))

    def release_lock(self, key: str, owner: str) -> bool:
        redis_key = f"lock:{key}"
        if self.client.get(redis_key) != owner:
            return False
        return bool(self.client.delete(redis_key))

    def status(self) -> dict:
        try:
            self.client.ping()
            return {"backend": self.backend, "available": True, "url": self.redis_url}
        except Exception as exc:
            return {"backend": self.backend, "available": False, "error": str(exc)}


_memory_store = MemoryReliabilityStore()
_redis_stores: dict[str, RedisReliabilityStore] = {}


def get_reliability_store(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.reliability_store.lower() == "redis":
        store = _redis_stores.get(settings.redis_url)
        if store is None:
            store = RedisReliabilityStore(settings.redis_url)
            _redis_stores[settings.redis_url] = store
        return store
    return _memory_store
