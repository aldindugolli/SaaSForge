"""PostgreSQL-specific database features: JSONB, FTS, materialized views, query optimization."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

from app.core.extensions import db
from app.core.models import (
    ApiRequestLog,
    AuditLog,
    Invoice,
    Organization,
    PaymentEvent,
    Subscription,
    User,
)

logger = logging.getLogger(__name__)

# ─── JSONB Column Helper ───────────────────────────────────────────────────────

def jsonb_column(default: Any = None):
    """Return a JSONB column definition for PostgreSQL, fallback to JSON for SQLite."""
    try:
        import sqlalchemy
        if sqlalchemy.__version__ >= "2.0":
            return db.Column(JSONB, nullable=True, default=default)
    except Exception:
        pass
    return db.Column(db.JSON, nullable=True, default=default)


# ─── GIN Index Management ──────────────────────────────────────────────────────

GIN_INDEXES = {
    "idx_audit_log_metadata": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_metadata
        ON audit_logs USING GIN (metadata)
    """,
    "idx_payment_event_data": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_event_data
        ON payment_events USING GIN (data)
    """,
    "idx_feature_flag_metadata": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_feature_flag_metadata
        ON feature_flags USING GIN (metadata)
    """,
}


def create_gin_indexes():
    """Create GIN indexes on JSONB columns for PostgreSQL."""
    from flask import current_app
    if "postgresql" not in current_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        logger.info("Skipping GIN indexes: not using PostgreSQL")
        return

    for name, ddl in GIN_INDEXES.items():
        try:
            db.session.execute(text(ddl))
            logger.info(f"Created GIN index: {name}")
        except Exception as e:
            logger.warning(f"Failed to create GIN index {name}: {e}")
    db.session.commit()


# ─── Expression Indexes ────────────────────────────────────────────────────────

EXPRESSION_INDEXES = {
    "idx_users_email_lower": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email_lower
        ON users (LOWER(email))
    """,
    "idx_organizations_name_lower": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_organizations_name_lower
        ON organizations (LOWER(name))
    """,
    "idx_audit_logs_actor_action": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_actor_action
        ON audit_logs (actor_id, action, created_at DESC)
    """,
    "idx_api_request_logs_composite": """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_api_request_logs_composite
        ON api_request_logs (api_key_id, created_at DESC)
    """,
}


def create_expression_indexes():
    """Create expression and composite indexes for PostgreSQL."""
    from flask import current_app
    if "postgresql" not in current_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        logger.info("Skipping expression indexes: not using PostgreSQL")
        return

    for name, ddl in EXPRESSION_INDEXES.items():
        try:
            db.session.execute(text(ddl))
            logger.info(f"Created expression index: {name}")
        except Exception as e:
            logger.warning(f"Failed to create expression index {name}: {e}")
    db.session.commit()


# ─── Full-Text Search Support ──────────────────────────────────────────────────

def create_fts_trigger(table: str, column: str, vector_column: str, weight: str = "D"):
    """Create a tsvector column and trigger for full-text search."""
    return f"""
    -- Add tsvector column if not exists
    ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {vector_column} TSVECTOR;

    -- Create trigger function
    CREATE OR REPLACE FUNCTION {table}_tsvector_update()
    RETURNS trigger AS $$
    BEGIN
        NEW.{vector_column} := to_tsvector('english', COALESCE(NEW.{column}, ''));
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    -- Drop existing trigger if any
    DROP TRIGGER IF EXISTS trg_{table}_tsvector ON {table};

    -- Create trigger
    CREATE TRIGGER trg_{table}_tsvector
    BEFORE INSERT OR UPDATE ON {table}
    FOR EACH ROW EXECUTE FUNCTION {table}_tsvector_update();

    -- Create GIN index on tsvector
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{table}_fts
    ON {table} USING GIN ({vector_column});

    -- Backfill existing data
    UPDATE {table} SET {vector_column} = to_tsvector('english', COALESCE({column}, ''));
    """


FTS_CONFIGS = {
    "users": {
        "columns": [
            ("name", "A"),
            ("email", "B"),
            ("company", "C"),
            ("bio", "D"),
        ],
        "vector_column": "search_vector",
    },
    "organizations": {
        "columns": [
            ("name", "A"),
            ("description", "B"),
        ],
        "vector_column": "search_vector",
    },
    "audit_logs": {
        "columns": [
            ("action", "A"),
        ],
        "vector_column": "search_vector",
    },
    "notifications": {
        "columns": [
            ("title", "A"),
            ("message", "B"),
        ],
        "vector_column": "search_vector",
    },
}


def create_full_text_search():
    """Set up full-text search for PostgreSQL."""
    from flask import current_app
    if "postgresql" not in current_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        logger.info("Skipping FTS: not using PostgreSQL")
        return

    for table, config in FTS_CONFIGS.items():
        vector_col = config["vector_column"]
        # Build combined tsvector from weighted columns
        columns_sql = " || ' ' || ".join(
            f"setweight(to_tsvector('english', COALESCE({col}, '')), '{weight}')"
            for col, weight in config["columns"]
        )

        try:
            db.session.execute(text(f"""
                ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {vector_col} TSVECTOR;
            """))
            db.session.execute(text(f"""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_{table}_fts
                ON {table} USING GIN ({vector_col});
            """))
            db.session.execute(text(f"""
                UPDATE {table}
                SET {vector_col} = {columns_sql};
            """))
            logger.info(f"Created FTS on {table}.{vector_col}")
        except Exception as e:
            logger.warning(f"Failed to create FTS on {table}: {e}")

    db.session.commit()


def search_table(table_name: str, query: str, vector_column: str = "search_vector",
                 limit: int = 20, offset: int = 0) -> list:
    """Full-text search against a table with tsvector column."""
    sql = text(f"""
        SELECT *, ts_rank({vector_column}, plainto_tsquery('english', :query)) AS rank
        FROM {table_name}
        WHERE {vector_column} @@ plainto_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit OFFSET :offset
    """)
    result = db.session.execute(sql, {"query": query, "limit": limit, "offset": offset})
    return [dict(row._mapping) for row in result]


# ─── Materialized Views ────────────────────────────────────────────────────────

MATERIALIZED_VIEWS = {
    "mv_dashboard_stats": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_stats AS
        SELECT
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM users WHERE last_login_at >= NOW() - INTERVAL '30 days') AS active_users,
            (SELECT COUNT(*) FROM organizations) AS total_organizations,
            (SELECT COUNT(*) FROM subscriptions WHERE status IN ('active', 'trialing')) AS total_subscriptions,
            (SELECT COALESCE(SUM(amount_paid), 0) FROM invoices WHERE status = 'paid') AS total_revenue,
            (SELECT COUNT(*) FROM subscriptions WHERE plan = 'pro' AND status IN ('active', 'trialing')) * 29 +
            (SELECT COUNT(*) FROM subscriptions WHERE plan = 'business' AND status IN ('active', 'trialing')) * 99 AS mrr,
            (SELECT COUNT(*) FROM subscriptions WHERE status = 'canceled' AND canceled_at >= NOW() - INTERVAL '30 days') AS canceled_30d,
            (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '30 days') AS new_users_30d,
            (SELECT COUNT(*) FROM users WHERE created_at < NOW() - INTERVAL '30 days') AS users_before_30d
        WITH DATA
    """,
    "mv_revenue_by_month": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_revenue_by_month AS
        SELECT
            DATE_TRUNC('month', paid_at) AS month,
            COUNT(*) AS invoice_count,
            SUM(amount_paid) AS revenue_cents,
            COUNT(DISTINCT organization_id) AS paying_orgs
        FROM invoices
        WHERE status = 'paid'
        GROUP BY DATE_TRUNC('month', paid_at)
        ORDER BY month DESC
        WITH DATA
    """,
    "mv_api_usage_stats": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_api_usage_stats AS
        SELECT
            endpoint,
            method,
            COUNT(*) AS request_count,
            AVG(response_time_ms)::INTEGER AS avg_response_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)::INTEGER AS p95_response_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms)::INTEGER AS p99_response_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::FLOAT / COUNT(*)::FLOAT * 100 AS error_rate_pct,
            COUNT(DISTINCT api_key_id) AS unique_keys,
            MAX(created_at) AS last_request_at
        FROM api_request_logs
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY endpoint, method
        ORDER BY request_count DESC
        WITH DATA
    """,
    "mv_subscription_metrics": """
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_subscription_metrics AS
        SELECT
            plan,
            status,
            COUNT(*) AS subscriber_count,
            AVG(EXTRACT(EPOCH FROM (COALESCE(current_period_end, NOW()) - created_at))) / 86400 AS avg_age_days
        FROM subscriptions
        GROUP BY plan, status
        ORDER BY plan, status
        WITH DATA
    """,
}


def create_materialized_views():
    """Create all materialized views for PostgreSQL."""
    from flask import current_app
    if "postgresql" not in current_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        logger.info("Skipping materialized views: not using PostgreSQL")
        return

    for name, ddl in MATERIALIZED_VIEWS.items():
        try:
            db.session.execute(text(ddl))
            db.session.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS uq_{name} ON {name} ((true))"))
            logger.info(f"Created materialized view: {name}")
        except Exception as e:
            logger.warning(f"Failed to create materialized view {name}: {e}")
    db.session.commit()


def refresh_materialized_view(name: str, concurrently: bool = True):
    """Refresh a specific materialized view."""
    concurrently_sql = "CONCURRENTLY" if concurrently else ""
    try:
        db.session.execute(text(f"REFRESH MATERIALIZED VIEW {concurrently_sql} {name}"))
        db.session.commit()
        logger.info(f"Refreshed materialized view: {name}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to refresh materialized view {name}: {e}")


def refresh_all_materialized_views(concurrently: bool = True):
    """Refresh all materialized views."""
    for name in MATERIALIZED_VIEWS:
        refresh_materialized_view(name, concurrently)


# ─── Query Optimization ────────────────────────────────────────────────────────

def optimize_queries():
    """Run ANALYZE to update query planner statistics."""
    from flask import current_app
    if "postgresql" not in current_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        return
    try:
        db.session.execute(text("ANALYZE"))
        db.session.commit()
        logger.info("Database analyzed for query optimization")
    except Exception as e:
        logger.warning(f"Failed to analyze database: {e}")


def eager_load_organization(org_id: str) -> Organization | None:
    """Load organization with all related data in a single query."""
    return (
        Organization.query
        .options(
            db.joinedload(Organization.memberships)
            .joinedload(Membership.user),
            db.joinedload(Organization.subscriptions),
            db.joinedload(Organization.owner),
        )
        .filter(Organization.id == org_id)
        .first()
    )


def eager_load_user(user_id: str) -> User | None:
    """Load user with memberships and orgs in optimized queries."""
    return (
        User.query
        .options(
            db.joinedload(User.memberships)
            .joinedload(Membership.organization),
        )
        .filter(User.id == user_id)
        .first()
    )


# ─── Database Initialization ───────────────────────────────────────────────────

def init_database_extensions():
    """Run all database optimization steps."""
    create_gin_indexes()
    create_expression_indexes()
    create_full_text_search()
    create_materialized_views()
    optimize_queries()
    logger.info("Database optimization complete")
