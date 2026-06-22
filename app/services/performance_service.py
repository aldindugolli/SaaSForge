"""Performance engineering: slow query monitoring, cache analytics, performance dashboard."""

import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

from flask import g, request
from sqlalchemy import func, text

from app.core.extensions import cache, db
from app.core.models import ApiRequestLog


# ─── Performance Metrics ───────────────────────────────────────────────────────

class PerformanceMetrics:
    """Collect and report performance metrics."""

    @staticmethod
    def get_average_response_time(days: int = 7) -> float:
        """Get average API response time in ms."""
        start_date = datetime.now(UTC) - timedelta(days=days)
        result = db.session.query(
            func.avg(ApiRequestLog.response_time_ms)
        ).filter(
            ApiRequestLog.created_at >= start_date
        ).scalar()
        return float(result or 0)

    @staticmethod
    def get_percentile_response_time(percentile: float = 0.95, days: int = 7) -> float:
        """Get percentile response time using PostgreSQL percentile_cont."""
        start_date = datetime.now(UTC) - timedelta(days=days)
        try:
            result = db.session.execute(
                text(f"""
                    SELECT PERCENTILE_CONT({percentile}) WITHIN GROUP (
                        ORDER BY response_time_ms
                    ) FROM api_request_logs
                    WHERE created_at >= :start_date AND response_time_ms IS NOT NULL
                """),
                {"start_date": start_date},
            ).scalar()
            return float(result or 0)
        except Exception:
            return 0

    @staticmethod
    def get_slowest_endpoints(limit: int = 20, days: int = 7) -> list[dict]:
        """Get endpoints sorted by average response time descending."""
        start_date = datetime.now(UTC) - timedelta(days=days)
        try:
            results = (
                db.session.query(
                    ApiRequestLog.method,
                    ApiRequestLog.endpoint,
                    func.count(ApiRequestLog.id).label("request_count"),
                    func.avg(ApiRequestLog.response_time_ms).label("avg_ms"),
                    func.max(ApiRequestLog.response_time_ms).label("max_ms"),
                    func.percentile_cont(0.95).within_group(
                        ApiRequestLog.response_time_ms
                    ).label("p95_ms"),
                )
                .filter(
                    ApiRequestLog.created_at >= start_date,
                    ApiRequestLog.response_time_ms.isnot(None),
                )
                .group_by(ApiRequestLog.method, ApiRequestLog.endpoint)
                .order_by(func.avg(ApiRequestLog.response_time_ms).desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "method": r.method,
                    "endpoint": r.endpoint,
                    "request_count": r.request_count,
                    "avg_ms": round(float(r.avg_ms or 0), 1),
                    "max_ms": round(float(r.max_ms or 0), 1),
                    "p95_ms": round(float(r.p95_ms or 0), 1),
                }
                for r in results
            ]
        except Exception:
            return []

    @staticmethod
    def get_cache_performance() -> dict:
        """Get cache hit/miss statistics."""
        # Tracked via observability metrics
        from app.observability import metrics_registry
        return {
            "available": cache.available,
            # These are collected at runtime in metrics_registry
        }

    @staticmethod
    def get_db_query_stats() -> list[dict]:
        """Get database query statistics from pg_stat_statements if available."""
        try:
            results = db.session.execute(
                text("""
                    SELECT
                        query,
                        calls,
                        total_exec_time / 1000.0 AS total_ms,
                        mean_exec_time AS mean_ms,
                        rows,
                        shared_blks_hit,
                        shared_blks_read
                    FROM pg_stat_statements
                    ORDER BY total_exec_time DESC
                    LIMIT 20
                """)
            ).fetchall()
            return [
                {
                    "query": r.query[:200],
                    "calls": r.calls,
                    "total_ms": round(r.total_ms, 1),
                    "mean_ms": round(r.mean_ms, 2),
                    "rows": r.rows,
                }
                for r in results
            ]
        except Exception:
            return []

    @staticmethod
    def get_dashboard_data() -> dict:
        """Get performance dashboard data."""
        now = datetime.now(UTC)
        week_ago = now - timedelta(days=7)

        total_requests = ApiRequestLog.query.filter(
            ApiRequestLog.created_at >= week_ago
        ).count()

        error_count = ApiRequestLog.query.filter(
            ApiRequestLog.created_at >= week_ago,
            ApiRequestLog.status_code >= 500,
        ).count()

        return {
            "avg_response_ms": round(PerformanceMetrics.get_average_response_time(), 1),
            "p95_response_ms": round(PerformanceMetrics.get_percentile_response_time(0.95), 1),
            "p99_response_ms": round(PerformanceMetrics.get_percentile_response_time(0.99), 1),
            "total_requests_7d": total_requests,
            "error_count_7d": error_count,
            "error_rate_7d": round((error_count / max(total_requests, 1)) * 100, 2),
            "slowest_endpoints": PerformanceMetrics.get_slowest_endpoints(10),
            "cache_available": cache.available,
        }


# ─── Slow Query Monitoring Decorator ──────────────────────────────────────────

_slow_queries: list[dict] = []


def monitor_query(name: str | None = None, threshold_ms: float = 500):
    """Decorator to monitor service method execution time."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                duration = (time.time() - start) * 1000
                if duration > threshold_ms:
                    func_name = name or f.__qualname__
                    _slow_queries.append({
                        "function": func_name,
                        "duration_ms": round(duration, 1),
                        "threshold_ms": threshold_ms,
                        "timestamp": datetime.now(UTC).isoformat(),
                    })
                    # Keep only last 100
                    if len(_slow_queries) > 100:
                        _slow_queries.pop(0)
        return wrapper
    return decorator


def get_slow_queries(limit: int = 20) -> list[dict]:
    """Get recently detected slow queries."""
    return list(reversed(_slow_queries[-limit:]))


# ─── Cache Analytics ──────────────────────────────────────────────────────────

def track_cache_operation(operation: str, duration_ms: float, hit: bool = False) -> None:
    """Track cache operation for analytics."""
    from app.observability import metrics_registry, track_cache_operation as _track
    _track(operation, hit)


def get_cache_analytics() -> dict:
    """Get cache analytics summary."""
    from app.observability import metrics_registry
    return {
        "available": cache.available,
        "hits": metrics_registry._counters.get("cache_hits_total", 0),
        "misses": metrics_registry._counters.get("cache_misses_total", 0),
        "operations": metrics_registry._counters.get("cache_operations_total{operation=get}", 0) +
                      metrics_registry._counters.get("cache_operations_total{operation=set}", 0),
    }
