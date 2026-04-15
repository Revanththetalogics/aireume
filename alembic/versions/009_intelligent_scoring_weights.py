"""Intelligent Scoring Weights System

Revision ID: 009
Revises: 008
Create Date: 2026-04-16

Adds support for intelligent, role-adaptive scoring weights with version management.

This migration introduces:
- Version management fields (is_active, version_number) for ScreeningResult
- Role detection and weight metadata (role_category, weight_reasoning)
- Backward compatible - all fields nullable with sensible defaults
- Existing records automatically set to is_active=True, version_number=1
"""

from alembic import op
import sqlalchemy as sa


# Alembic revision identifiers
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add intelligent scoring weights support to ScreeningResult table.
    
    All new columns are nullable to maintain backward compatibility.
    Existing records will have defaults applied via SQL UPDATE.
    """
    
    # Add version management columns
    op.add_column(
        'screening_results',
        sa.Column('is_active', sa.Boolean, nullable=True, server_default='true')
    )
    op.add_column(
        'screening_results',
        sa.Column('version_number', sa.Integer, nullable=True, server_default='1')
    )
    
    # Add role detection and weight metadata columns
    op.add_column(
        'screening_results',
        sa.Column('role_category', sa.String(50), nullable=True)
    )
    op.add_column(
        'screening_results',
        sa.Column('weight_reasoning', sa.Text, nullable=True)
    )
    op.add_column(
        'screening_results',
        sa.Column('suggested_weights_json', sa.Text, nullable=True)
    )
    
    # Create index on is_active for efficient querying of current versions
    op.create_index(
        'ix_screening_results_is_active',
        'screening_results',
        ['is_active', 'candidate_id'],
        unique=False
    )
    
    # Create index on version_number for version history queries
    op.create_index(
        'ix_screening_results_version',
        'screening_results',
        ['candidate_id', 'version_number'],
        unique=False
    )


def downgrade():
    """
    Remove intelligent scoring weights support.
    
    Safe to run - only removes new columns, doesn't affect existing data.
    """
    
    # Drop indexes first
    op.drop_index('ix_screening_results_version', table_name='screening_results')
    op.drop_index('ix_screening_results_is_active', table_name='screening_results')
    
    # Drop columns
    op.drop_column('screening_results', 'suggested_weights_json')
    op.drop_column('screening_results', 'weight_reasoning')
    op.drop_column('screening_results', 'role_category')
    op.drop_column('screening_results', 'version_number')
    op.drop_column('screening_results', 'is_active')
