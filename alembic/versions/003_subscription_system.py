"""Complete subscription system with usage tracking and plan management

Revision ID: 003
Revises: 002
Create Date: 2026-04-05

Changes:
  - Enhance subscription_plans with detailed fields (price, description, features)
  - Add usage tracking columns to tenants
  - Create usage_logs table for detailed tracking
  - Seed initial plans: Free, Pro, Enterprise
  - Link existing tenants to default Pro plan

Idempotent: safe when objects already exist (legacy create_all + first Alembic run).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import json

revision = "003"
down_revision = "002"
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
    connection = op.get_bind()

    # ── Enhance subscription_plans table ─────────────────────────────────────────
    sp_cols = _column_names(insp, "subscription_plans")
    additions = [
        ("display_name", sa.Column("display_name", sa.String(100), nullable=True)),
        ("description", sa.Column("description", sa.Text(), nullable=True)),
        ("price_monthly", sa.Column("price_monthly", sa.Integer(), nullable=True, server_default="0")),
        ("price_yearly", sa.Column("price_yearly", sa.Integer(), nullable=True, server_default="0")),
        ("currency", sa.Column("currency", sa.String(3), nullable=True, server_default="USD")),
        ("features", sa.Column("features", sa.Text(), nullable=True, server_default="[]")),
        ("is_active", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())),
        ("sort_order", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")),
        ("created_at", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now())),
        ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now)),
    ]
    for name, col in additions:
        if name not in sp_cols:
            op.add_column("subscription_plans", col)

    insp = _inspector()
    if "ix_subscription_plans_is_active_sort" not in _index_names(insp, "subscription_plans"):
        op.create_index("ix_subscription_plans_is_active_sort", "subscription_plans", ["is_active", "sort_order"])

    # ── Add usage tracking columns to tenants ───────────────────────────────────
    insp = _inspector()
    t_cols = _column_names(insp, "tenants")
    tenant_additions = [
        ("subscription_status", sa.Column("subscription_status", sa.String(20), nullable=False, server_default="active")),
        ("current_period_start", sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True)),
        ("current_period_end", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True)),
        ("analyses_count_this_month", sa.Column("analyses_count_this_month", sa.Integer(), nullable=False, server_default="0")),
        ("storage_used_bytes", sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False, server_default="0")),
        ("usage_reset_at", sa.Column("usage_reset_at", sa.DateTime(timezone=True), nullable=True)),
        ("stripe_customer_id", sa.Column("stripe_customer_id", sa.String(255), nullable=True)),
        ("stripe_subscription_id", sa.Column("stripe_subscription_id", sa.String(255), nullable=True)),
        ("subscription_updated_at", sa.Column("subscription_updated_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for name, col in tenant_additions:
        if name not in t_cols:
            op.add_column("tenants", col)

    insp = _inspector()
    if "ix_tenants_subscription_status" not in _index_names(insp, "tenants"):
        op.create_index("ix_tenants_subscription_status", "tenants", ["subscription_status"])
    if "ix_tenants_stripe_customer" not in _index_names(insp, "tenants"):
        op.create_index("ix_tenants_stripe_customer", "tenants", ["stripe_customer_id"], unique=False)

    # ── Create usage_logs table ─────────────────────────────────────────────────
    insp = _inspector()
    if not _table_exists(insp, "usage_logs"):
        op.create_table(
            "usage_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_usage_logs_tenant_action", "usage_logs", ["tenant_id", "action"])
        op.create_index("ix_usage_logs_tenant_created", "usage_logs", ["tenant_id", "created_at"])
        op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])
    else:
        insp = _inspector()
        idx = _index_names(insp, "usage_logs")
        if "ix_usage_logs_tenant_action" not in idx:
            op.create_index("ix_usage_logs_tenant_action", "usage_logs", ["tenant_id", "action"])
        if "ix_usage_logs_tenant_created" not in idx:
            op.create_index("ix_usage_logs_tenant_created", "usage_logs", ["tenant_id", "created_at"])
        if "ix_usage_logs_created_at" not in idx:
            op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])

    # ── Seed initial subscription plans (insert only missing names) ─────────────
    plans_table = table(
        "subscription_plans",
        column("id", sa.Integer),
        column("name", sa.String),
        column("display_name", sa.String),
        column("description", sa.String),
        column("limits", sa.Text),
        column("price_monthly", sa.Integer),
        column("price_yearly", sa.Integer),
        column("currency", sa.String),
        column("features", sa.Text),
        column("is_active", sa.Boolean),
        column("sort_order", sa.Integer),
    )

    plans = [
        {
            "name": "free",
            "display_name": "Free",
            "description": "For individuals trying out ARIA. Limited analyses and features.",
            "limits": json.dumps({
                "analyses_per_month": 20,
                "batch_size": 5,
                "team_members": 1,
                "storage_gb": 1,
                "api_access": False,
                "custom_weights": False,
                "priority_support": False,
            }),
            "price_monthly": 0,
            "price_yearly": 0,
            "currency": "USD",
            "features": json.dumps([
                "20 resume analyses per month",
                "Batch up to 5 resumes",
                "Single user access",
                "Basic resume parsing",
                "Email support",
            ]),
            "is_active": True,
            "sort_order": 1,
        },
        {
            "name": "pro",
            "display_name": "Pro",
            "description": "For growing teams and recruiters who need more power and collaboration.",
            "limits": json.dumps({
                "analyses_per_month": 500,
                "batch_size": 50,
                "team_members": 5,
                "storage_gb": 10,
                "api_access": True,
                "custom_weights": True,
                "priority_support": True,
            }),
            "price_monthly": 49,
            "price_yearly": 470,
            "currency": "USD",
            "features": json.dumps([
                "500 analyses per month",
                "Batch up to 50 resumes",
                "Up to 5 team members",
                "Advanced AI scoring & matching",
                "Custom scoring weights",
                "API access",
                "Priority email support",
                "Detailed analytics",
                "Export to CSV/Excel",
            ]),
            "is_active": True,
            "sort_order": 2,
        },
        {
            "name": "enterprise",
            "display_name": "Enterprise",
            "description": "For large organizations with high volume and custom requirements.",
            "limits": json.dumps({
                "analyses_per_month": -1,
                "batch_size": 100,
                "team_members": 25,
                "storage_gb": 100,
                "api_access": True,
                "custom_weights": True,
                "priority_support": True,
                "dedicated_support": True,
                "custom_integrations": True,
                "sso": True,
            }),
            "price_monthly": 199,
            "price_yearly": 1910,
            "currency": "USD",
            "features": json.dumps([
                "Unlimited analyses",
                "Batch up to 100 resumes",
                "Up to 25 team members",
                "Everything in Pro",
                "SSO & advanced security",
                "Dedicated account manager",
                "Custom AI model training",
                "SLA guarantee",
                "On-premise deployment option",
            ]),
            "is_active": True,
            "sort_order": 3,
        },
    ]

    for plan in plans:
        row = connection.execute(
            sa.text("SELECT 1 FROM subscription_plans WHERE name = :n"),
            {"n": plan["name"]},
        ).fetchone()
        if not row:
            op.bulk_insert(plans_table, [plan])

    # ── Link existing tenants to Pro plan by default ───────────────────────────
    result = connection.execute(sa.text("SELECT id FROM subscription_plans WHERE name = 'pro'"))
    pro_plan_id = result.scalar()

    if pro_plan_id:
        connection.execute(
            sa.text("""
                UPDATE tenants
                SET plan_id = :plan_id,
                    subscription_status = 'active',
                    current_period_start = NOW(),
                    current_period_end = NOW() + INTERVAL '1 year',
                    usage_reset_at = date_trunc('month', NOW())
                WHERE plan_id IS NULL
            """),
            {"plan_id": pro_plan_id},
        )


def downgrade() -> None:
    # Drop usage_logs
    op.drop_index("ix_usage_logs_created_at", "usage_logs")
    op.drop_index("ix_usage_logs_tenant_created", "usage_logs")
    op.drop_index("ix_usage_logs_tenant_action", "usage_logs")
    op.drop_table("usage_logs")

    # Remove tenant columns
    op.drop_index("ix_tenants_stripe_customer", "tenants")
    op.drop_index("ix_tenants_subscription_status", "tenants")

    with op.batch_alter_table("tenants") as batch_op:
        batch_op.drop_column("subscription_updated_at")
        batch_op.drop_column("stripe_subscription_id")
        batch_op.drop_column("stripe_customer_id")
        batch_op.drop_column("usage_reset_at")
        batch_op.drop_column("storage_used_bytes")
        batch_op.drop_column("analyses_count_this_month")
        batch_op.drop_column("current_period_end")
        batch_op.drop_column("current_period_start")
        batch_op.drop_column("subscription_status")

    # Remove subscription_plans columns
    op.drop_index("ix_subscription_plans_is_active_sort", "subscription_plans")

    with op.batch_alter_table("subscription_plans") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("sort_order")
        batch_op.drop_column("is_active")
        batch_op.drop_column("features")
        batch_op.drop_column("currency")
        batch_op.drop_column("price_yearly")
        batch_op.drop_column("price_monthly")
        batch_op.drop_column("description")
        batch_op.drop_column("display_name")
