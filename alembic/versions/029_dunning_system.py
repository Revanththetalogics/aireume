"""Add dunning_records table for failed payment retry tracking"""

from alembic import op
import sqlalchemy as sa


revision = "029_dunning_system"
down_revision = "028_invoices"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'dunning_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default='4'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.String(500), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Seed default dunning configuration into platform_configs
    op.execute("""
        INSERT INTO platform_configs (config_key, config_value, description)
        VALUES (
            'billing.dunning',
            '{"retry_schedule_days": [1, 3, 7, 14], "max_retries": 4, "suspend_after_max_retries": true, "notify_on_each_retry": true}',
            'Dunning configuration for failed payment retries'
        )
        ON CONFLICT (config_key) DO NOTHING
    """)


def downgrade():
    op.execute("DELETE FROM platform_configs WHERE config_key = 'billing.dunning'")
    op.drop_table('dunning_records')
