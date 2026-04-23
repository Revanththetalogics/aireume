"""Webhooks, webhook deliveries, and default feature flag seeding

Revision ID: 013
Revises: 012
Create Date: 2026-04-22

Changes:
  - Create webhooks table
  - Create webhook_deliveries table
  - Seed default feature flags into feature_flags table

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _index_names(insp, table: str) -> set:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    insp = _inspector()

    # ── Create webhooks table ──────────────────────────────────────────────────
    if not _table_exists(insp, "webhooks"):
        op.create_table(
            "webhooks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("secret", sa.String(255), nullable=False),
            sa.Column("events", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )
        op.create_index("ix_webhooks_id", "webhooks", ["id"])
        op.create_index("ix_webhooks_tenant_id", "webhooks", ["tenant_id"])
    else:
        insp = _inspector()
        idx = _index_names(insp, "webhooks")
        if "ix_webhooks_id" not in idx:
            op.create_index("ix_webhooks_id", "webhooks", ["id"])
        if "ix_webhooks_tenant_id" not in idx:
            op.create_index("ix_webhooks_tenant_id", "webhooks", ["tenant_id"])

    # ── Create webhook_deliveries table ────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False),
            sa.Column("event", sa.String(100), nullable=False),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.Text(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_webhook_deliveries_id", "webhook_deliveries", ["id"])
        op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])
    else:
        insp = _inspector()
        idx = _index_names(insp, "webhook_deliveries")
        if "ix_webhook_deliveries_id" not in idx:
            op.create_index("ix_webhook_deliveries_id", "webhook_deliveries", ["id"])
        if "ix_webhook_deliveries_webhook_id" not in idx:
            op.create_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries", ["webhook_id"])

    # ── Seed default feature flags (idempotent) ───────────────────────────────
    conn = op.get_bind()
    flags = [
        ("video_analysis", "Video Analysis"),
        ("batch_analysis", "Batch Analysis"),
        ("custom_weights", "Custom Scoring Weights"),
        ("api_access", "API Access"),
        ("export_excel", "Excel Export"),
        ("transcript_analysis", "Transcript Analysis"),
        ("email_generation", "Email Generation"),
    ]
    for key, display in flags:
        existing = conn.execute(
            text("SELECT id FROM feature_flags WHERE key = :key"),
            {"key": key},
        ).fetchone()
        if not existing:
            conn.execute(
                text(
                    "INSERT INTO feature_flags (key, display_name, enabled_globally) "
                    "VALUES (:key, :display, true)"
                ),
                {"key": key, "display": display},
            )


def downgrade() -> None:
    # Drop webhook_deliveries (depends on webhooks)
    insp = _inspector()
    if _table_exists(insp, "webhook_deliveries"):
        idx = _index_names(insp, "webhook_deliveries")
        if "ix_webhook_deliveries_webhook_id" in idx:
            op.drop_index("ix_webhook_deliveries_webhook_id", "webhook_deliveries")
        if "ix_webhook_deliveries_id" in idx:
            op.drop_index("ix_webhook_deliveries_id", "webhook_deliveries")
        op.drop_table("webhook_deliveries")

    # Drop webhooks
    insp = _inspector()
    if _table_exists(insp, "webhooks"):
        idx = _index_names(insp, "webhooks")
        if "ix_webhooks_tenant_id" in idx:
            op.drop_index("ix_webhooks_tenant_id", "webhooks")
        if "ix_webhooks_id" in idx:
            op.drop_index("ix_webhooks_id", "webhooks")
        op.drop_table("webhooks")

    # Remove seeded feature flags
    conn = op.get_bind()
    flag_keys = [
        "video_analysis", "batch_analysis", "custom_weights",
        "api_access", "export_excel", "transcript_analysis", "email_generation",
    ]
    for key in flag_keys:
        conn.execute(text("DELETE FROM feature_flags WHERE key = :key"), {"key": key})
