"""Enterprise platform admin: granular roles, impersonation, security events, plan features, erasure

Revision ID: 021
Revises: 020
Create Date: 2026-05-06

Changes:
  - Add platform_role to users (NULL | super_admin | billing_admin | support | security_admin | readonly)
  - Backfill platform_role from is_platform_admin
  - Create impersonation_sessions table
  - Create security_events table
  - Create plan_features table
  - Create erasure_logs table

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
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

    # ── 1. Add platform_role to users ──────────────────────────────────────────
    user_cols = _column_names(insp, "users")
    if "platform_role" not in user_cols:
        op.add_column(
            "users",
            sa.Column(
                "platform_role",
                sa.String(50),
                nullable=True,
            ),
        )

    # Backfill existing platform admins (only if is_platform_admin column exists)
    user_cols_check = _column_names(insp, "users")
    if "is_platform_admin" in user_cols_check:
        op.execute("""
            UPDATE users
            SET platform_role = 'super_admin'
            WHERE is_platform_admin = true AND platform_role IS NULL
        """)

    # ── 2. Create impersonation_sessions ───────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "impersonation_sessions"):
        op.create_table(
            "impersonation_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), unique=True, nullable=False, index=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
        )
        op.create_index("ix_impersonation_sessions_admin", "impersonation_sessions", ["admin_user_id"])
        op.create_index("ix_impersonation_sessions_target", "impersonation_sessions", ["target_user_id"])
        op.create_index("ix_impersonation_sessions_expires", "impersonation_sessions", ["expires_at"])

    # ── 3. Create security_events ──────────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "security_events"):
        op.create_table(
            "security_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
        op.create_index("ix_security_events_created_at", "security_events", ["created_at"])
        op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
        op.create_index("ix_security_events_tenant_id", "security_events", ["tenant_id"])

    # ── 4. Create plan_features ────────────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "plan_features"):
        op.create_table(
            "plan_features",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False),
            sa.Column("feature_flag_id", sa.Integer(), sa.ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_plan_features_plan_id", "plan_features", ["plan_id"])
        op.create_index("ix_plan_features_feature_flag_id", "plan_features", ["feature_flag_id"])
        op.create_unique_constraint("uq_plan_feature", "plan_features", ["plan_id", "feature_flag_id"])

    # ── 5. Create erasure_logs ─────────────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "erasure_logs"):
        op.create_table(
            "erasure_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="requested"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("records_affected", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_erasure_logs_tenant_id", "erasure_logs", ["tenant_id"])
        op.create_index("ix_erasure_logs_status", "erasure_logs", ["status"])

    # ── 6. Add scoring_weights to tenants ──────────────────────────────────────
    insp = _inspector()
    tenant_cols = _column_names(insp, "tenants")
    if "scoring_weights" not in tenant_cols:
        op.add_column(
            "tenants",
            sa.Column("scoring_weights", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    # Drop erasure_logs
    op.drop_index("ix_erasure_logs_status", "erasure_logs")
    op.drop_index("ix_erasure_logs_tenant_id", "erasure_logs")
    op.drop_table("erasure_logs")

    # Drop plan_features
    op.drop_constraint("uq_plan_feature", "plan_features", type_="unique")
    op.drop_index("ix_plan_features_feature_flag_id", "plan_features")
    op.drop_index("ix_plan_features_plan_id", "plan_features")
    op.drop_table("plan_features")

    # Drop security_events
    op.drop_index("ix_security_events_tenant_id", "security_events")
    op.drop_index("ix_security_events_user_id", "security_events")
    op.drop_index("ix_security_events_created_at", "security_events")
    op.drop_index("ix_security_events_event_type", "security_events")
    op.drop_table("security_events")

    # Drop impersonation_sessions
    op.drop_index("ix_impersonation_sessions_expires", "impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_target", "impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_admin", "impersonation_sessions")
    op.drop_table("impersonation_sessions")

    # Remove platform_role from users
    op.drop_column("users", "platform_role")

    # Remove scoring_weights from tenants
    insp = _inspector()
    tenant_cols = _column_names(insp, "tenants")
    if "scoring_weights" in tenant_cols:
        op.drop_column("tenants", "scoring_weights")
