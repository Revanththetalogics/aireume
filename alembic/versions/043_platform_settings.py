"""Add platform_settings table"""

revision = "043_platform_settings"
down_revision = "042_admin_notifications"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def upgrade():
    insp = inspect(op.get_bind())
    if 'platform_settings' in {t for t in insp.get_table_names()}:
        return
    op.create_table(
        'platform_settings',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('key', sa.String(100), unique=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_platform_settings_key', 'platform_settings', ['key'])


def downgrade():
    op.drop_index('ix_platform_settings_key', table_name='platform_settings')
    op.drop_table('platform_settings')
