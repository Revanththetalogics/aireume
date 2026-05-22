"""Add billing_events table for webhook audit logging"""

from alembic import op
import sqlalchemy as sa


revision = "027_billing_events"
down_revision = "026_audit_log_system"
branch_labels = None
depends_on = None


def upgrade():
    insp = sa.inspect(op.get_bind())
    if "billing_events" not in insp.get_table_names():
        op.create_table(
            'billing_events',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('provider', sa.String(20), nullable=False, index=True),
            sa.Column('event_type', sa.String(100), nullable=False, index=True),
            sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='SET NULL'), nullable=True, index=True),
            sa.Column('raw_payload', sa.Text, nullable=True),
            sa.Column('result', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('error_detail', sa.Text, nullable=True),
            sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade():
    op.drop_table('billing_events')
