"""Add webhook delivery tables (customer webhook endpoints, delivery log, event log)."""

revision = "4b2c3d4e5f6a"
down_revision = "3a1b2c3d4e5f"
branch_labels = None
depends_on = None

import sqlalchemy as sa
from alembic import op


def upgrade():
    # ─── Customer Webhook Endpoints ────────────────────────────────────────────
    op.create_table(
        "customer_webhook_endpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("secret", sa.String(128), nullable=False),
        sa.Column("events", sa.JSON, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("last_delivered_at", sa.DateTime, nullable=True),
        sa.Column("last_success_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_webhook_endpoints_org", "customer_webhook_endpoints", ["organization_id"])

    # ─── Webhook Delivery Log ──────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("endpoint_id", sa.String(36), sa.ForeignKey("customer_webhook_endpoints.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("attempt_count", sa.Integer, default=1, nullable=False),
        sa.Column("max_attempts", sa.Integer, default=5, nullable=False),
        sa.Column("next_retry_at", sa.DateTime, nullable=True),
        sa.Column("signature", sa.String(256), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_webhook_deliveries_status", "webhook_deliveries", ["status"])
    op.create_index("idx_webhook_deliveries_next_retry", "webhook_deliveries", ["next_retry_at"])

    # ─── Webhook Event Log (internal idempotent processing) ────────────────────
    op.create_table(
        "webhook_event_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("stripe_event_id", sa.String(255), unique=True, nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, default="pending"),
        sa.Column("attempt_count", sa.Integer, default=0, nullable=False),
        sa.Column("max_attempts", sa.Integer, default=3, nullable=False),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("processed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("idx_webhook_event_logs_stripe_event", "webhook_event_logs", ["stripe_event_id"])
    op.create_index("idx_webhook_event_logs_status", "webhook_event_logs", ["status"])


def downgrade():
    op.drop_table("webhook_event_logs")
    op.drop_table("webhook_deliveries")
    op.drop_table("customer_webhook_endpoints")
