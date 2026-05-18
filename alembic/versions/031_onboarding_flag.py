"""Add onboarding_completed and onboarding_completed_at to tenants table"""

from alembic import op
import sqlalchemy as sa


revision = "031_onboarding_flag"
down_revision = "030_usage_alerts"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('tenants', sa.Column('onboarding_completed', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('tenants', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('tenants', 'onboarding_completed_at')
    op.drop_column('tenants', 'onboarding_completed')
