"""Add admin notifications table"""

revision = "042_admin_notifications"
down_revision = "041_email_verification"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'admin_notifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False, server_default='info'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_admin_notifications_is_read', 'admin_notifications', ['is_read'])
    op.create_index('ix_admin_notifications_created_at', 'admin_notifications', ['created_at'])


def downgrade():
    op.drop_index('ix_admin_notifications_created_at', table_name='admin_notifications')
    op.drop_index('ix_admin_notifications_is_read', table_name='admin_notifications')
    op.drop_table('admin_notifications')
