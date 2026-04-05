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
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
import json

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enhance subscription_plans table ─────────────────────────────────────────
    
    # Add new columns to subscription_plans
    with op.batch_alter_table("subscription_plans") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("price_monthly", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("price_yearly", sa.Integer(), nullable=True, server_default="0"))
        batch_op.add_column(sa.Column("currency", sa.String(3), nullable=True, server_default="USD"))
        batch_op.add_column(sa.Column("features", sa.Text(), nullable=True, server_default="[]"))
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now))
    
    # Create index on is_active and sort_order
    op.create_index("ix_subscription_plans_is_active_sort", "subscription_plans", ["is_active", "sort_order"])
    
    # ── Add usage tracking columns to tenants ───────────────────────────────────
    
    with op.batch_alter_table("tenants") as batch_op:
        # Link to plan (already exists but ensure proper FK)
        # Add usage tracking
        batch_op.add_column(sa.Column("subscription_status", sa.String(20), nullable=False, server_default="active"))
        batch_op.add_column(sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("analyses_count_this_month", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("storage_used_bytes", sa.BigInteger(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("usage_reset_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("stripe_customer_id", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("stripe_subscription_id", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("subscription_updated_at", sa.DateTime(timezone=True), nullable=True))
    
    op.create_index("ix_tenants_subscription_status", "tenants", ["subscription_status"])
    op.create_index("ix_tenants_stripe_customer", "tenants", ["stripe_customer_id"], unique=False)
    
    # ── Create usage_logs table ─────────────────────────────────────────────────
    
    op.create_table(
        "usage_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),  # 'resume_analysis', 'batch_analysis', etc.
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("details", sa.Text(), nullable=True),  # JSON with context
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_logs_tenant_action", "usage_logs", ["tenant_id", "action"])
    op.create_index("ix_usage_logs_tenant_created", "usage_logs", ["tenant_id", "created_at"])
    op.create_index("ix_usage_logs_created_at", "usage_logs", ["created_at"])
    
    # ── Seed initial subscription plans ─────────────────────────────────────────
    
    plans_table = table(
        'subscription_plans',
        column('id', sa.Integer),
        column('name', sa.String),
        column('display_name', sa.String),
        column('description', sa.String),
        column('limits', sa.Text),
        column('price_monthly', sa.Integer),
        column('price_yearly', sa.Integer),
        column('currency', sa.String),
        column('features', sa.Text),
        column('is_active', sa.Boolean),
        column('sort_order', sa.Integer),
    )
    
    plans = [
        {
            'name': 'free',
            'display_name': 'Free',
            'description': 'For individuals trying out ARIA. Limited analyses and features.',
            'limits': json.dumps({
                'analyses_per_month': 20,
                'batch_size': 5,
                'team_members': 1,
                'storage_gb': 1,
                'api_access': False,
                'custom_weights': False,
                'priority_support': False,
            }),
            'price_monthly': 0,
            'price_yearly': 0,
            'currency': 'USD',
            'features': json.dumps([
                '20 resume analyses per month',
                'Batch up to 5 resumes',
                'Single user access',
                'Basic resume parsing',
                'Email support',
            ]),
            'is_active': True,
            'sort_order': 1,
        },
        {
            'name': 'pro',
            'display_name': 'Pro',
            'description': 'For growing teams and recruiters who need more power and collaboration.',
            'limits': json.dumps({
                'analyses_per_month': 500,
                'batch_size': 50,
                'team_members': 5,
                'storage_gb': 10,
                'api_access': True,
                'custom_weights': True,
                'priority_support': True,
            }),
            'price_monthly': 49,
            'price_yearly': 470,  # ~20% discount
            'currency': 'USD',
            'features': json.dumps([
                '500 analyses per month',
                'Batch up to 50 resumes',
                'Up to 5 team members',
                'Advanced AI scoring & matching',
                'Custom scoring weights',
                'API access',
                'Priority email support',
                'Detailed analytics',
                'Export to CSV/Excel',
            ]),
            'is_active': True,
            'sort_order': 2,
        },
        {
            'name': 'enterprise',
            'display_name': 'Enterprise',
            'description': 'For large organizations with high volume and custom requirements.',
            'limits': json.dumps({
                'analyses_per_month': -1,  # unlimited
                'batch_size': 100,
                'team_members': 25,
                'storage_gb': 100,
                'api_access': True,
                'custom_weights': True,
                'priority_support': True,
                'dedicated_support': True,
                'custom_integrations': True,
                'sso': True,
            }),
            'price_monthly': 199,
            'price_yearly': 1910,  # ~20% discount
            'currency': 'USD',
            'features': json.dumps([
                'Unlimited analyses',
                'Batch up to 100 resumes',
                'Up to 25 team members',
                'Everything in Pro',
                'SSO & advanced security',
                'Dedicated account manager',
                'Custom AI model training',
                'SLA guarantee',
                'On-premise deployment option',
            ]),
            'is_active': True,
            'sort_order': 3,
        },
    ]
    
    op.bulk_insert(plans_table, plans)
    
    # ── Link existing tenants to Pro plan by default ───────────────────────────
    
    # Get the Pro plan ID
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT id FROM subscription_plans WHERE name = 'pro'"))
    pro_plan_id = result.scalar()
    
    if pro_plan_id:
        # Update all existing tenants to use Pro plan
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
            {'plan_id': pro_plan_id}
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
