"""Add usage_alerts table for threshold notification tracking"""

from alembic import op
import sqlalchemy as sa


revision = "030_usage_alerts"
down_revision = "029_dunning_system"
branch_labels = None
depends_on = None


def upgrade():
    insp = sa.inspect(op.get_bind())
    if "usage_alerts" not in insp.get_table_names():
        op.create_table(
            'usage_alerts',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('alert_type', sa.String(50), nullable=False),
            sa.Column('threshold_percent', sa.Integer, nullable=False),
            sa.Column('metric_name', sa.String(50), nullable=False),
            sa.Column('current_value', sa.Integer, nullable=False),
            sa.Column('limit_value', sa.Integer, nullable=False),
            sa.Column('notified_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('period_key', sa.String(10), nullable=False),
            sa.UniqueConstraint('tenant_id', 'alert_type', 'period_key', name='uq_usage_alert_per_period'),
        )


def downgrade():
    op.drop_table('usage_alerts')
