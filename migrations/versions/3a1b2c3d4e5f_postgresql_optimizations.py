"""Migration to add PostgreSQL-specific optimizations:
- JSONB columns for audit_logs, payment_events, feature_flags
- GIN indexes on JSONB columns
- Expression indexes for case-insensitive search
- FTS tsvector columns
- Materialized views for analytics
"""

revision = "3a1b2c3d4e5f"
down_revision = "29131e9dc678"
branch_labels = None
depends_on = None

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

import app.core.extensions  # noqa: F401


def upgrade():
    conn = op.get_bind()
    is_postgres = "postgresql" in str(conn.engine.url)

    if not is_postgres:
        # SQLite — skip PostgreSQL-specific operations, just alter columns
        with op.batch_alter_table("audit_logs") as batch_op:
            batch_op.alter_column("metadata", type_=sa.JSON, existing_type=sa.JSON)
        with op.batch_alter_table("payment_events") as batch_op:
            batch_op.alter_column("data", type_=sa.JSON, existing_type=sa.JSON)
        return

    # ─── JSONB Columns ─────────────────────────────────────────────────────
    op.alter_column("audit_logs", "metadata",
                    type_=JSONB, existing_type=sa.JSON,
                    postgresql_using="metadata::jsonb")
    op.alter_column("payment_events", "data",
                    type_=JSONB, existing_type=sa.JSON,
                    postgresql_using="data::jsonb")

    # Add metadata column to feature_flags if missing
    try:
        op.add_column("feature_flags", sa.Column("metadata", JSONB, nullable=True))
    except Exception:
        pass

    # ─── GIN Indexes ───────────────────────────────────────────────────────
    op.create_index("idx_audit_logs_metadata_gin", "audit_logs", ["metadata"],
                    postgresql_using="gin")
    op.create_index("idx_payment_events_data_gin", "payment_events", ["data"],
                    postgresql_using="gin")
    op.create_index("idx_feature_flags_metadata_gin", "feature_flags", ["metadata"],
                    postgresql_using="gin")

    # ─── Expression Indexes ─────────────────────────────────────────────────
    op.create_index("idx_users_email_lower", "users",
                    [sa.text("LOWER(email)")],
                    postgresql_using="btree")
    op.create_index("idx_organizations_name_lower", "organizations",
                    [sa.text("LOWER(name)")],
                    postgresql_using="btree")
    op.create_index("idx_audit_logs_actor_action", "audit_logs",
                    ["actor_id", "action", sa.text("created_at DESC")],
                    postgresql_using="btree")
    op.create_index("idx_api_request_logs_composite", "api_request_logs",
                    ["api_key_id", sa.text("created_at DESC")],
                    postgresql_using="btree")

    # ─── Full-Text Search Support ───────────────────────────────────────────
    for table, config in _fts_configs().items():
        vector_col = config["vector_column"]
        op.add_column(table, sa.Column(vector_col, TSVECTOR, nullable=True))

        # Build combined tsvector expression
        columns_expr = " || ' ' || ".join(
            f"setweight(to_tsvector('english', COALESCE(NEW.{col}, '')), '{weight}')"
            for col, weight in config["columns"]
        )

        # Create trigger function
        op.execute(f"""
            CREATE OR REPLACE FUNCTION {table}_fts_update()
            RETURNS trigger AS $$
            BEGIN
                NEW.{vector_col} := {columns_expr};
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)

        # Create trigger
        op.execute(f"""
            DROP TRIGGER IF EXISTS trg_{table}_fts ON {table};
            CREATE TRIGGER trg_{table}_fts
            BEFORE INSERT OR UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION {table}_fts_update();
        """)

        # Backfill existing data
        op.execute(f"""
            UPDATE {table}
            SET {vector_col} = {columns_expr};
        """)

        # GIN index on tsvector
        op.create_index(f"idx_{table}_fts_gin", table, [vector_col],
                        postgresql_using="gin")

    # ─── Materialized Views ─────────────────────────────────────────────────
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_stats AS
        SELECT
            (SELECT COUNT(*) FROM users) AS total_users,
            (SELECT COUNT(*) FROM users WHERE last_login_at >= NOW() - INTERVAL '30 days') AS active_users,
            (SELECT COUNT(*) FROM organizations) AS total_organizations,
            (SELECT COUNT(*) FROM subscriptions WHERE status IN ('active', 'trialing')) AS total_subscriptions,
            (SELECT COALESCE(SUM(amount_paid), 0) FROM invoices WHERE status = 'paid') AS total_revenue,
            (SELECT COUNT(*) FROM subscriptions WHERE plan = 'pro' AND status IN ('active', 'trialing')) * 29 +
            (SELECT COUNT(*) FROM subscriptions WHERE plan = 'business' AND status IN ('active', 'trialing')) * 99 AS mrr
        WITH DATA
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_dashboard_stats ON mv_dashboard_stats ((true))")

    op.execute("""
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
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_revenue_by_month ON mv_revenue_by_month (month)")

    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_api_usage_stats AS
        SELECT
            endpoint,
            method,
            COUNT(*) AS request_count,
            AVG(response_time_ms)::INTEGER AS avg_response_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms)::INTEGER AS p95_response_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms)::INTEGER AS p99_response_ms,
            SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END)::FLOAT / NULLIF(COUNT(*), 0)::FLOAT * 100 AS error_rate_pct,
            COUNT(DISTINCT api_key_id) AS unique_keys
        FROM api_request_logs
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY endpoint, method
        ORDER BY request_count DESC
        WITH DATA
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_api_usage_stats ON mv_api_usage_stats (endpoint, method)")


def downgrade():
    conn = op.get_bind()
    is_postgres = "postgresql" in str(conn.engine.url)

    if is_postgres:
        # Drop materialized views
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_dashboard_stats")
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_revenue_by_month")
        op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_api_usage_stats")

        # Drop FTS triggers and columns
        for table in ["users", "organizations", "audit_logs", "notifications"]:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_fts ON {table}")
            op.execute(f"DROP FUNCTION IF EXISTS {table}_fts_update()")
            op.drop_index(f"idx_{table}_fts_gin", table_name=table)
            op.drop_column(table, "search_vector")

        # Drop indexes
        op.drop_index("idx_api_request_logs_composite", table_name="api_request_logs")
        op.drop_index("idx_audit_logs_actor_action", table_name="audit_logs")
        op.drop_index("idx_organizations_name_lower", table_name="organizations")
        op.drop_index("idx_users_email_lower", table_name="users")
        op.drop_index("idx_feature_flags_metadata_gin", table_name="feature_flags")
        op.drop_index("idx_payment_events_data_gin", table_name="payment_events")
        op.drop_index("idx_audit_logs_metadata_gin", table_name="audit_logs")

        # Revert JSONB to JSON
        op.alter_column("audit_logs", "metadata", type_=sa.JSON, existing_type=JSONB)
        op.alter_column("payment_events", "data", type_=sa.JSON, existing_type=JSONB)

    else:
        with op.batch_alter_table("payment_events") as batch_op:
            batch_op.alter_column("data", type_=sa.JSON, existing_type=sa.JSON)
        with op.batch_alter_table("audit_logs") as batch_op:
            batch_op.alter_column("metadata", type_=sa.JSON, existing_type=sa.JSON)


def _fts_configs():
    return {
        "users": {
            "columns": [("name", "A"), ("email", "B"), ("company", "C"), ("bio", "D")],
            "vector_column": "search_vector",
        },
        "organizations": {
            "columns": [("name", "A"), ("description", "B")],
            "vector_column": "search_vector",
        },
        "audit_logs": {
            "columns": [("action", "A")],
            "vector_column": "search_vector",
        },
        "notifications": {
            "columns": [("title", "A"), ("message", "B")],
            "vector_column": "search_vector",
        },
    }
