"""narrative tracking enhancement

Revision ID: 011
Revises: 010_add_jd_text
Create Date: 2026-04-17 23:17:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010_add_jd_text'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add narrative_generated_at timestamp for tracking when LLM narrative completes.
    Backfill narrative_status for existing records.
    """
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('screening_results')]
    
    # Add narrative_generated_at if it doesn't exist
    if 'narrative_generated_at' not in existing_columns:
        op.add_column('screening_results', 
            sa.Column('narrative_generated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Backfill narrative_status for existing records
    # Records with narrative_json are 'ready', others are 'pending'
    op.execute("""
        UPDATE screening_results 
        SET narrative_status = 'ready' 
        WHERE narrative_json IS NOT NULL 
        AND narrative_json != '' 
        AND (narrative_status IS NULL OR narrative_status = 'pending')
    """)
    
    op.execute("""
        UPDATE screening_results 
        SET narrative_status = 'pending' 
        WHERE (narrative_json IS NULL OR narrative_json = '') 
        AND (narrative_status IS NULL OR narrative_status = '')
    """)


def downgrade():
    """Remove narrative_generated_at column."""
    op.drop_column('screening_results', 'narrative_generated_at')
