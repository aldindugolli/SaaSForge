import pytest
from app.services.cache_service import RedisCache, CacheService


class TestRedisCache:
    @pytest.fixture
    def cache(self):
        return RedisCache()

    def test_get_set(self, cache):
        cache.set("test", "key1", "value1")
        assert cache.get("test", "key1") == "value1"

    def test_get_missing(self, cache):
        assert cache.get("test", "nonexistent") is None

    def test_delete(self, cache):
        cache.set("test", "key1", "value1")
        cache.delete("test", "key1")
        assert cache.get("test", "key1") is None

    def test_clear(self, cache):
        cache.set("test", "key1", "value1")
        cache.set("test", "key2", "value2")
        cache.clear()
        assert cache.get("test", "key1") is None
        assert cache.get("test", "key2") is None

    def test_get_or_set(self, cache):
        fn = lambda: "computed"
        result = cache.get_or_set("test", "key1", fn)
        assert result == "computed"
        assert cache.get("test", "key1") == "computed"

    def test_get_or_set_caches(self, cache):
        call_count = 0
        def fn():
            nonlocal call_count
            call_count += 1
            return "value"
        cache.get_or_set("test", "key1", fn)
        cache.get_or_set("test", "key1", fn)
        assert call_count == 1

    def test_invalidate_pattern(self, cache):
        cache.set("analytics", "dashboard_stats", {})
        cache.set("analytics", "user_growth", [])
        cache.set("org", "members:123", [])
        cache.invalidate_pattern("analytics:*")
        assert cache.get("analytics", "dashboard_stats") is None
        assert cache.get("analytics", "user_growth") is None
        assert cache.get("org", "members:123") is not None

    def test_invalidate(self, cache):
        cache.set("test", "key1", "value1")
        cache.invalidate("test", "key1")
        assert cache.get("test", "key1") is None


class TestCacheService:
    @pytest.fixture
    def cache_service(self):
        return CacheService(RedisCache())

    def test_invalidate_org_data(self, cache_service):
        cache_service.cache.set("org", "members:org123", ["m1"])
        cache_service.cache.set("org", "subscriptions:org123", ["s1"])
        cache_service.invalidate_org_data("org123")
        assert cache_service.cache.get("org", "members:org123") is None
        assert cache_service.cache.get("org", "subscriptions:org123") is None

    def test_invalidate_analytics(self, cache_service):
        cache_service.cache.set("analytics", "dashboard_stats", {})
        cache_service.invalidate_analytics()
        assert cache_service.cache.get("analytics", "dashboard_stats") is None

    def test_cached_decorator(self, cache_service):
        call_count = 0
        @cache_service.cached("test", ttl=60)
        def compute(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        assert compute(5) == 10
        assert call_count == 1
        assert compute(5) == 10
        assert call_count == 1
