"""Add jd_text to ScreeningResult for RAG learning

Revision ID: 010_add_jd_text
Revises: 009_intelligent_scoring_weights
Create Date: 2026-04-16 21:47:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '010_add_jd_text'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add jd_text column to screening_results table for similarity matching.
    Add index on role_category for faster calibration queries.
    
    Idempotent: Checks if column/indexes exist before creating them.
    This handles cases where migration was partially applied.
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('screening_results')]
    
    # Add jd_text column only if it doesn't exist
    if 'jd_text' not in existing_columns:
        op.add_column('screening_results', 
            sa.Column('jd_text', sa.Text(), nullable=True))
    
    # Get existing indexes
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('screening_results')]
    
    # Add index on role_category for calibration queries (if not exists)
    if 'ix_screening_results_role_category' not in existing_indexes:
        op.create_index(
            'ix_screening_results_role_category', 
            'screening_results', 
            ['role_category']
        )
    
    # Add composite index for calibration queries (if not exists)
    if 'ix_screening_results_calibration' not in existing_indexes:
        op.create_index(
            'ix_screening_results_calibration',
            'screening_results',
            ['tenant_id', 'role_category', 'is_active']
        )


def downgrade():
    """
    Remove jd_text column and indexes.
    """
    # Drop indexes
    op.drop_index('ix_screening_results_calibration', table_name='screening_results')
    op.drop_index('ix_screening_results_role_category', table_name='screening_results')
    
    # Drop column
    op.drop_column('screening_results', 'jd_text')
