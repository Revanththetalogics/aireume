"""Add adaptive depth escalation config for voice screening."""
# Migration 047: Adaptive Depth Escalation

revision = "047_adaptive_depth_escalation"
down_revision = "046_unified_interview"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'voice_tenant_configs' in inspector.get_table_names():
        columns = [c['name'] for c in inspector.get_columns('voice_tenant_configs')]

        if 'auto_escalation_enabled' not in columns:
            op.add_column(
                'voice_tenant_configs',
                sa.Column('auto_escalation_enabled', sa.Boolean, nullable=False, server_default='false'),
            )

        if 'auto_escalation_threshold' not in columns:
            op.add_column(
                'voice_tenant_configs',
                sa.Column('auto_escalation_threshold', sa.Integer, nullable=False, server_default='70'),
            )


def downgrade():
    op.drop_column('voice_tenant_configs', 'auto_escalation_threshold')
    op.drop_column('voice_tenant_configs', 'auto_escalation_enabled')
