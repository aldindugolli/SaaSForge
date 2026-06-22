"""API platform: scoped permissions, usage limits, rate enforcement, analytics."""

import time
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import wraps
from typing import Any

import stripe
from flask import current_app, g, jsonify, request
from flask_login import current_user
from sqlalchemy import func

from app.core.extensions import cache, db
from app.core.models import APIKey, ApiRequestLog
from app.services.base import ServiceError


# ─── Permission Scopes ─────────────────────────────────────────────────────────

class APIPermission(StrEnum):
    READ_USERS = "read:users"
    READ_ORGANIZATIONS = "read:organizations"
    WRITE_ORGANIZATIONS = "write:organizations"
    WRITE_MEMBERS = "write:members"
    READ_BILLING = "read:billing"
    WRITE_BILLING = "write:billing"
    ADMIN_ANALYTICS = "admin:analytics"
    ADMIN_USERS = "admin:users"
    WEBHOOKS_READ = "webhooks:read"
    WEBHOOKS_WRITE = "webhooks:write"
    AUDIT_READ = "audit:read"
    API_KEYS_WRITE = "api_keys:write"


# ─── Scoped Permission Checking ────────────────────────────────────────────────

SCOPE_PERMISSIONS: dict[str, list[str]] = {
    "read": [
        APIPermission.READ_USERS.value,
        APIPermission.READ_ORGANIZATIONS.value,
        APIPermission.READ_BILLING.value,
        APIPermission.WEBHOOKS_READ.value,
        APIPermission.AUDIT_READ.value,
    ],
    "write": [
        APIPermission.READ_USERS.value,
        APIPermission.READ_ORGANIZATIONS.value,
        APIPermission.WRITE_ORGANIZATIONS.value,
        APIPermission.WRITE_MEMBERS.value,
        APIPermission.WEBHOOKS_WRITE.value,
        APIPermission.API_KEYS_WRITE.value,
    ],
    "admin": [
        APIPermission.ADMIN_ANALYTICS.value,
        APIPermission.ADMIN_USERS.value,
    ],
    "full": [
        APIPermission.READ_USERS.value,
        APIPermission.READ_ORGANIZATIONS.value,
        APIPermission.WRITE_ORGANIZATIONS.value,
        APIPermission.WRITE_MEMBERS.value,
        APIPermission.READ_BILLING.value,
        APIPermission.WRITE_BILLING.value,
        APIPermission.WEBHOOKS_READ.value,
        APIPermission.WEBHOOKS_WRITE.value,
        APIPermission.AUDIT_READ.value,
        APIPermission.API_KEYS_WRITE.value,
        APIPermission.ADMIN_ANALYTICS.value,
    ],
}


def require_api_permission(permission: APIPermission):
    """Decorator to require a specific API permission scope."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key: APIKey | None = getattr(g, "api_key", None)
            if not api_key:
                return jsonify({"error": "API key required"}), 401

            perms = api_key.permissions or []
            if permission.value not in perms:
                return jsonify({
                    "error": "insufficient_permissions",
                    "message": f"Requires '{permission.value}' permission",
                    "required": permission.value,
                }), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


# ─── Usage Limits ──────────────────────────────────────────────────────────────

class UsageLimitService:
    """Per-plan API usage limits with Redis counters."""

    PLAN_LIMITS = {
        "free": {"requests_per_day": 1000, "rate_per_minute": 10},
        "pro": {"requests_per_day": 10000, "rate_per_minute": 60},
        "business": {"requests_per_day": 100000, "rate_per_minute": 300},
    }

    @staticmethod
    def get_limit(api_key: APIKey) -> dict:
        """Get usage limits for the API key's plan."""
        org = api_key.organization
        plan = org.subscription_tier if org else "free"
        return UsageLimitService.PLAN_LIMITS.get(plan, UsageLimitService.PLAN_LIMITS["free"])

    @staticmethod
    def check_daily_limit(api_key: APIKey) -> tuple[bool, int]:
        """Check if the API key has exceeded its daily request limit."""
        limits = UsageLimitService.get_limit(api_key)
        daily_limit = limits["requests_per_day"]

        # Count today's requests
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        used = ApiRequestLog.query.filter(
            ApiRequestLog.api_key_id == api_key.id,
            ApiRequestLog.created_at >= today_start,
        ).count()

        if used >= daily_limit:
            return False, used

        return True, used

    @staticmethod
    def get_usage_stats(api_key_id: str, days: int = 30) -> dict:
        """Get usage statistics for an API key."""
        start_date = datetime.now(UTC) - timedelta(days=days)

        total = ApiRequestLog.query.filter(
            ApiRequestLog.api_key_id == api_key_id,
            ApiRequestLog.created_at >= start_date,
        ).count()

        by_endpoint = (
            db.session.query(
                ApiRequestLog.endpoint,
                func.count(ApiRequestLog.id).label("count"),
                func.avg(ApiRequestLog.response_time_ms).label("avg_ms"),
            )
            .filter(
                ApiRequestLog.api_key_id == api_key_id,
                ApiRequestLog.created_at >= start_date,
            )
            .group_by(ApiRequestLog.endpoint)
            .order_by(func.count(ApiRequestLog.id).desc())
            .limit(20)
            .all()
        )

        by_day = (
            db.session.query(
                func.date(ApiRequestLog.created_at).label("date"),
                func.count(ApiRequestLog.id).label("count"),
            )
            .filter(
                ApiRequestLog.api_key_id == api_key_id,
                ApiRequestLog.created_at >= start_date,
            )
            .group_by(func.date(ApiRequestLog.created_at))
            .order_by(func.date(ApiRequestLog.created_at))
            .all()
        )

        return {
            "total_requests": total,
            "period_days": days,
            "by_endpoint": [
                {"endpoint": e.endpoint, "count": e.count, "avg_response_ms": int(e.avg_ms or 0)}
                for e in by_endpoint
            ],
            "by_day": [
                {"date": str(d.date), "count": d.count}
                for d in by_day
            ],
        }


# ─── Enhanced API Key Creation ─────────────────────────────────────────────────

def create_api_key(user_id: str, organization_id: str | None, name: str,
                   scope: str = "read", key_type: str = "test") -> tuple[APIKey, str]:
    """Create an API key with scoped permissions."""
    import secrets
    from werkzeug.security import generate_password_hash

    permissions = SCOPE_PERMISSIONS.get(scope, SCOPE_PERMISSIONS["read"])
    raw_key = f"sf_{secrets.token_hex(24)}"

    key_obj = APIKey(
        user_id=user_id,
        organization_id=organization_id,
        name=name,
        key_prefix=raw_key[:11],
        key_hash=generate_password_hash(raw_key),
        key_type=key_type,
        permissions=permissions,
    )
    db.session.add(key_obj)
    db.session.commit()
    return key_obj, raw_key


# ─── API Key Authentication Middleware ─────────────────────────────────────────

def api_auth_required(f):
    """Authenticate API requests via X-API-Key header with usage limits."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key_header = request.headers.get("X-API-Key")
        if not api_key_header:
            return jsonify({"error": "api_key_required", "message": "X-API-Key header is required"}), 401

        from werkzeug.security import check_password_hash

        key_obj = APIKey.query.filter_by(is_active=True).first()
        if not key_obj or not check_password_hash(key_obj.key_hash, api_key_header):
            return jsonify({"error": "invalid_api_key", "message": "Invalid API key"}), 401

        if key_obj.is_expired:
            return jsonify({"error": "api_key_expired", "message": "API key has expired"}), 401

        # Check daily usage limit
        within_limit, used = UsageLimitService.check_daily_limit(key_obj)
        if not within_limit:
            limits = UsageLimitService.get_limit(key_obj)
            return jsonify({
                "error": "rate_limit_exceeded",
                "message": f"Daily request limit ({limits['requests_per_day']}) exceeded",
                "limit": limits["requests_per_day"],
                "used": used,
            }), 429

        # Update usage tracking
        key_obj.usage_count = (key_obj.usage_count or 0) + 1
        key_obj.last_used_at = datetime.now(UTC)
        db.session.commit()

        g.api_key = key_obj
        g.api_user = key_obj.user
        g.api_start_time = time.time()

        return f(*args, **kwargs)
    return decorated


# ─── API Request Logging Middleware ────────────────────────────────────────────

def log_api_request(response):
    """Log API request details after response."""
    if not request.path.startswith("/api/v1/"):
        return response

    start_time = getattr(g, "api_start_time", None)
    duration = int((time.time() - start_time) * 1000) if start_time else None

    log = ApiRequestLog(
        user_id=getattr(g, "api_user", None) and g.api_user.id or None,
        organization_id=getattr(g, "api_key", None) and g.api_key.organization_id or None,
        api_key_id=getattr(g, "api_key", None) and g.api_key.id or None,
        method=request.method,
        endpoint=request.path,
        status_code=response.status_code,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent", "")[:500],
        response_time_ms=duration,
    )
    db.session.add(log)
    db.session.commit()
    return response


# ─── Enhanced API Error Responses ──────────────────────────────────────────────

def api_error_response(status_code: int, error: str, message: str,
                       details: dict | None = None) -> tuple:
    """Generate a consistent API error response."""
    response = {
        "error": error,
        "message": message,
    }
    if details:
        response["details"] = details

    # Add correlation ID if available
    from app.observability import get_correlation_id
    cid = get_correlation_id()
    if cid:
        response["correlation_id"] = cid

    return jsonify(response), status_code
