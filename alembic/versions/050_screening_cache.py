"""Add screening_cache table for batch scoring consistency"""

revision = "050_screening_cache"
down_revision = "049_missing_cols"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def upgrade():
    insp = inspect(op.get_bind())
    existing = {t for t in insp.get_table_names()}

    if 'screening_cache' not in existing:
        op.create_table(
            'screening_cache',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('cache_key', sa.String(128), nullable=False, unique=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True),
            sa.Column('result_json', sa.Text(), nullable=False),
            sa.Column('resume_hash', sa.String(32), nullable=False),
            sa.Column('jd_hash', sa.String(32), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_screening_cache_cache_key', 'screening_cache', ['cache_key'], unique=True)
        op.create_index('ix_screening_cache_tenant_id', 'screening_cache', ['tenant_id'])
        op.create_index('ix_screening_cache_resume_hash', 'screening_cache', ['resume_hash'])
        op.create_index('ix_screening_cache_jd_hash', 'screening_cache', ['jd_hash'])
        op.create_index('ix_screening_cache_tenant_created', 'screening_cache', ['tenant_id', 'created_at'])


def downgrade():
    op.drop_table('screening_cache')
