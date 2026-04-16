"""Add jd_text to ScreeningResult for RAG learning

Revision ID: 010_add_jd_text
Revises: 009_intelligent_scoring_weights
Create Date: 2026-04-16 21:47:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_add_jd_text'
down_revision = '009_intelligent_scoring_weights'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add jd_text column to screening_results table for similarity matching.
    Add index on role_category for faster calibration queries.
    """
    # Add jd_text column (nullable for backward compatibility)
    op.add_column('screening_results', 
        sa.Column('jd_text', sa.Text(), nullable=True))
    
    # Add index on role_category for calibration queries
    op.create_index(
        'ix_screening_results_role_category', 
        'screening_results', 
        ['role_category']
    )
    
    # Add composite index for calibration queries (tenant_id + role_category + is_active)
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
