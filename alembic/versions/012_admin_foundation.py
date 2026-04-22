"""Admin foundation: platform admin fields, audit logs, feature flags, rate limits

Revision ID: 012
Revises: 011
Create Date: 2026-04-21

Changes:
  - Add is_platform_admin to users
  - Add suspended_at, suspended_reason, metadata_json to tenants
  - Create audit_logs table
  - Create feature_flags table
  - Create tenant_feature_overrides table
  - Create rate_limit_configs table

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def _index_names(insp, table: str) -> set:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    insp = _inspector()

    # ── Add is_platform_admin to users ──────────────────────────────────────────
    user_cols = _column_names(insp, "users")
    if "is_platform_admin" not in user_cols:
        op.add_column(
            "users",
            sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    # ── Add admin columns to tenants ────────────────────────────────────────────
    insp = _inspector()
    tenant_cols = _column_names(insp, "tenants")
    tenant_additions = [
        ("suspended_at", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True)),
        ("suspended_reason", sa.Column("suspended_reason", sa.Text(), nullable=True)),
        ("metadata_json", sa.Column("metadata_json", sa.Text(), nullable=False, server_default='"{}"')),
    ]
    for name, col in tenant_additions:
        if name not in tenant_cols:
            op.add_column("tenants", col)

    # ── Create audit_logs table ─────────────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("actor_email", sa.String(255), nullable=False),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("resource_type", sa.String(50), nullable=False),
            sa.Column("resource_id", sa.Integer(), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    else:
        insp = _inspector()
        idx = _index_names(insp, "audit_logs")
        if "ix_audit_logs_action" not in idx:
            op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
        if "ix_audit_logs_created_at" not in idx:
            op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── Create feature_flags table ──────────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("key", sa.String(100), unique=True, nullable=False),
            sa.Column("display_name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("enabled_globally", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )
        op.create_index("ix_feature_flags_key", "feature_flags", ["key"])
    else:
        insp = _inspector()
        idx = _index_names(insp, "feature_flags")
        if "ix_feature_flags_key" not in idx:
            op.create_index("ix_feature_flags_key", "feature_flags", ["key"])

    # ── Create tenant_feature_overrides table ───────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "tenant_feature_overrides"):
        op.create_table(
            "tenant_feature_overrides",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("feature_flag_id", sa.Integer(), sa.ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "feature_flag_id", name="uq_tenant_feature"),
        )

    # ── Create rate_limit_configs table ─────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "rate_limit_configs"):
        op.create_table(
            "rate_limit_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False),
            sa.Column("requests_per_minute", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("llm_concurrent_max", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )


def downgrade() -> None:
    # Drop rate_limit_configs
    op.drop_table("rate_limit_configs")

    # Drop tenant_feature_overrides
    op.drop_table("tenant_feature_overrides")

    # Drop feature_flags
    op.drop_index("ix_feature_flags_key", "feature_flags")
    op.drop_table("feature_flags")

    # Drop audit_logs
    op.drop_index("ix_audit_logs_created_at", "audit_logs")
    op.drop_index("ix_audit_logs_action", "audit_logs")
    op.drop_table("audit_logs")

    # Remove tenant columns
    with op.batch_alter_table("tenants") as batch_op:
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("suspended_reason")
        batch_op.drop_column("suspended_at")

    # Remove user column
    op.drop_column("users", "is_platform_admin")
