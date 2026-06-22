"""Observability platform: structured logging, correlation IDs, metrics, health checks."""

import logging
import os
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from flask import Flask, g, request

from app.core.extensions import cache, db

logger = logging.getLogger(__name__)

# ─── Correlation ID ────────────────────────────────────────────────────────────

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    return _correlation_id.get()


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def generate_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


class CorrelationMiddleware:
    """Assign a correlation ID to every request."""

    def __init__(self, app: Flask | None = None):
        self._header = "X-Correlation-ID"
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self):
        cid = request.headers.get(self._header) or generate_correlation_id()
        set_correlation_id(cid)
        g.correlation_id = cid

    def _after_request(self, response):
        cid = getattr(g, "correlation_id", get_correlation_id())
        if cid:
            response.headers[self._header] = cid
        return response


# ─── Structured Logging ────────────────────────────────────────────────────────

class StructuredFormatter(logging.Formatter):
    """Output logs as JSON lines with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        base = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        cid = get_correlation_id()
        if cid:
            base["correlation_id"] = cid

        if record.exc_info and record.exc_info[0]:
            base["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        if hasattr(record, "structured_data"):
            base.update(record.structured_data)

        return json.dumps(base, default=str)


def setup_logging(app: Flask) -> None:
    """Configure structured JSON logging for the application."""
    log_level = app.config.get("LOG_LEVEL", "INFO").upper()
    log_format = app.config.get("LOG_FORMAT", "json")

    if log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        app.logger.addHandler(handler)
        app.logger.setLevel(log_level)

        # Set root logger to JSON
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(log_level)

        # Silence noisy libs
        logging.getLogger("werkzeug").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
    else:
        logging.basicConfig(level=log_level)


# ─── Prometheus Metrics ────────────────────────────────────────────────────────

class MetricsRegistry:
    """Simple Prometheus-compatible metrics collector."""

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._labels: dict[str, dict[str, str]] = {}

    def counter(self, name: str, labels: dict | None = None) -> None:
        key = self._label_key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + 1

    def gauge(self, name: str, value: float, labels: dict | None = None) -> None:
        key = self._label_key(name, labels)
        self._gauges[key] = value

    def histogram(self, name: str, value: float, labels: dict | None = None) -> None:
        key = self._label_key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        # Keep only last 1000 values
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-1000:]

    def _label_key(self, name: str, labels: dict | None) -> str:
        if labels:
            parts = [f"{k}={v}" for k, v in sorted(labels.items())]
            return f"{name}{{{','.join(parts)}}}"
        return name

    def render(self) -> str:
        lines: list[str] = []
        # Counters
        for key, value in sorted(self._counters.items()):
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")
        # Gauges
        for key, value in sorted(self._gauges.items()):
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")
        # Histograms
        for key, values in sorted(self._histograms.items()):
            name = key.split("{")[0]
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{key}_count {len(values)}")
            if values:
                lines.append(f"{key}_sum {sum(values)}")
        return "\n".join(lines)


metrics_registry = MetricsRegistry()


class MetricsMiddleware:
    """Collect HTTP request metrics."""

    def __init__(self, app: Flask | None = None):
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self):
        g._request_start = time.time()

    def _after_request(self, response):
        if not hasattr(g, "_request_start"):
            return response
        duration = time.time() - g._request_start
        metrics_registry.histogram(
            "http_request_duration_ms",
            duration * 1000,
            {"method": request.method, "endpoint": request.path},
        )
        metrics_registry.counter(
            "http_requests_total",
            {"method": request.method, "endpoint": request.path, "status": str(response.status_code)},
        )
        if response.status_code >= 500:
            metrics_registry.counter(
                "http_errors_total",
                {"method": request.method, "endpoint": request.path, "status": str(response.status_code)},
            )
        return response


def track_db_query(duration_ms: float, query: str = "") -> None:
    """Track a database query execution."""
    metrics_registry.histogram("db_query_duration_ms", duration_ms)
    metrics_registry.counter("db_queries_total")


def track_cache_operation(operation: str, hit: bool = False) -> None:
    """Track a cache operation."""
    metrics_registry.counter("cache_operations_total", {"operation": operation})
    if operation == "get":
        if hit:
            metrics_registry.counter("cache_hits_total")
        else:
            metrics_registry.counter("cache_misses_total")


def track_queue_operation(operation: str, queue: str = "saasforge-jobs") -> None:
    """Track a background queue operation."""
    metrics_registry.counter("queue_operations_total", {"operation": operation, "queue": queue})


def track_worker_throughput(job_name: str, duration_ms: float, success: bool = True) -> None:
    """Track worker job execution."""
    status = "success" if success else "failure"
    metrics_registry.histogram("worker_job_duration_ms", duration_ms, {"job": job_name, "status": status})
    metrics_registry.counter("worker_jobs_total", {"job": job_name, "status": status})


# ─── Health Check Extensions ───────────────────────────────────────────────────

class HealthStatus:
    """Detailed health status for services."""

    def __init__(self):
        self.checks: dict[str, dict] = {}

    def check(self, name: str, fn: Callable[[], bool], description: str = "") -> dict:
        try:
            healthy = fn()
            status = "healthy" if healthy else "unhealthy"
            if not healthy:
                logger.warning(f"Health check failed: {name}")
        except Exception as e:
            healthy = False
            status = "unhealthy"
            logger.error(f"Health check error: {name}: {e}")

        result = {"status": status, "healthy": healthy, "description": description}
        self.checks[name] = result
        return result

    def all_healthy(self) -> bool:
        return all(c["healthy"] for c in self.checks.values())

    def to_dict(self, detailed: bool = False) -> dict:
        base = {
            "status": "healthy" if self.all_healthy() else "degraded",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if detailed:
            base["checks"] = self.checks
        return base


def check_database() -> bool:
    db.session.execute(db.text("SELECT 1"))
    return True


def check_redis() -> bool:
    if cache.available:
        cache.get("health", "ping")
        return True
    return False


def check_queue() -> bool:
    """Check RQ queue health by verifying Redis is available."""
    return check_redis()


def check_stripe() -> bool:
    """Check Stripe API connectivity (lightweight)."""
    import stripe
    from flask import current_app
    if not current_app.config.get("STRIPE_SECRET_KEY"):
        return False
    try:
        stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
        stripe.Balance.retrieve()
        return True
    except Exception:
        return False


def check_email_service() -> bool:
    """Check if email service is configured."""
    from flask import current_app
    return bool(current_app.config.get("SENDGRID_API_KEY") or
                current_app.config.get("MAIL_SUPPRESS_SEND"))


# ─── Initialize Observability ──────────────────────────────────────────────────

def init_observability(app: Flask) -> None:
    """Initialize all observability components."""
    setup_logging(app)
    CorrelationMiddleware(app)
    MetricsMiddleware(app)
    logger.info(
        "Observability initialized",
        extra={"structured_data": {"correlation_enabled": True,
                                    "metrics_enabled": True,
                                    "log_format": app.config.get("LOG_FORMAT", "json")}},
    )
