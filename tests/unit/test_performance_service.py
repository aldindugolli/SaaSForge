"""Unit tests for the performance service."""


class TestPerformanceMetrics:
    def test_get_average_response_time_returns_float(self, app, db):
        from app.services.performance_service import PerformanceMetrics
        result = PerformanceMetrics.get_average_response_time(days=30)
        assert isinstance(result, float)

    def test_get_slowest_endpoints_returns_list(self, app, db):
        from app.services.performance_service import PerformanceMetrics
        result = PerformanceMetrics.get_slowest_endpoints(limit=5, days=30)
        assert isinstance(result, list)

    def test_get_dashboard_data_has_required_keys(self, app, db):
        from app.services.performance_service import PerformanceMetrics
        data = PerformanceMetrics.get_dashboard_data()
        assert "avg_response_ms" in data
        assert "p95_response_ms" in data
        assert "total_requests_7d" in data
        assert "error_count_7d" in data
        assert "slowest_endpoints" in data
        assert "cache_available" in data

    def test_monitor_query_decorator(self):
        from app.services.performance_service import monitor_query, get_slow_queries

        @monitor_query(name="test_fn", threshold_ms=0)
        def slow_fn():
            import time
            time.sleep(0.01)

        slow_fn()
        slow_queries = get_slow_queries(5)
        assert len(slow_queries) >= 1
        assert slow_queries[0]["function"] == "test_fn"

    def test_get_cache_analytics(self, app, db):
        from app.services.performance_service import get_cache_analytics
        result = get_cache_analytics()
        assert "available" in result
