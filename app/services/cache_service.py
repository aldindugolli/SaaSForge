import json
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis_client=None):
        self._client = redis_client
        self._local = {}

    def init_app(self, app):
        try:
            from redis import Redis
            url = app.config.get("REDIS_URL")
            if url:
                self._client = Redis.from_url(url, decode_responses=True)
                self._client.ping()
                logger.info("Redis cache connected")
            else:
                self._client = None
        except Exception:
            self._client = None
            logger.warning("Redis unavailable, using in-memory cache fallback")

    @property
    def available(self):
        return self._client is not None

    def _make_key(self, prefix: str, key: str) -> str:
        return f"saasforge:{prefix}:{key}"

    def get(self, prefix: str, key: str) -> Any | None:
        full_key = self._make_key(prefix, key)
        if self._client:
            try:
                val = self._client.get(full_key)
                return json.loads(val) if val else None
            except Exception:
                return None
        return self._local.get(full_key)

    def set(self, prefix: str, key: str, value: Any, ttl: int = 300) -> None:
        full_key = self._make_key(prefix, key)
        if self._client:
            try:
                self._client.setex(full_key, ttl, json.dumps(value, default=str))
            except Exception:
                pass
        self._local[full_key] = value

    def delete(self, prefix: str, key: str) -> None:
        full_key = self._make_key(prefix, key)
        if self._client:
            try:
                self._client.delete(full_key)
            except Exception:
                pass
        self._local.pop(full_key, None)

    def invalidate(self, prefix: str, key: str) -> None:
        self.delete(prefix, key)

    def invalidate_pattern(self, pattern: str) -> None:
        full_pattern = f"saasforge:{pattern}*"
        if self._client:
            try:
                keys = self._client.keys(full_pattern)
                if keys:
                    self._client.delete(*keys)
            except Exception:
                pass
        self._local = {k: v for k, v in self._local.items() if not k.startswith(f"saasforge:{pattern.split(':')[0]}")}

    def get_or_set(self, prefix: str, key: str, fn: Callable, ttl: int = 300) -> Any:
        cached = self.get(prefix, key)
        if cached is not None:
            return cached
        value = fn()
        self.set(prefix, key, value, ttl)
        return value

    def clear(self):
        if self._client:
            try:
                self._client.flushdb()
            except Exception:
                pass
        self._local.clear()


class CacheService:
    def __init__(self, cache: RedisCache):
        self.cache = cache

    def cached(self, prefix: str, ttl: int = 300):
        def decorator(fn):
            def wrapper(*args, **kwargs):
                key_parts = [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
                cache_key = ":".join(key_parts) if key_parts else "default"
                return self.cache.get_or_set(prefix, cache_key, lambda: fn(*args, **kwargs), ttl)
            wrapper.__name__ = fn.__name__
            wrapper.__qualname__ = fn.__qualname__
            return wrapper
        return decorator

    def invalidate_org_data(self, org_id: str) -> None:
        self.cache.invalidate_pattern(f"org:{org_id}:*")

    def invalidate_user_data(self, user_id: str) -> None:
        self.cache.invalidate_pattern(f"user:{user_id}:*")

    def invalidate_analytics(self) -> None:
        self.cache.invalidate_pattern("analytics:*")
