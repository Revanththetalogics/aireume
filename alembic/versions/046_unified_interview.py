"""Add interview_depth to voice_screening_sessions for unified interview tracking"""

revision = "046a1b2c3d4e"
down_revision = "045_ai_recruiter"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Guard: table must exist
    if 'voice_screening_sessions' not in inspector.get_table_names():
        return

    columns = [c['name'] for c in inspector.get_columns('voice_screening_sessions')]

    if 'interview_depth' not in columns:
        op.add_column(
            'voice_screening_sessions',
            sa.Column('interview_depth', sa.String(10), server_default='quick', nullable=False),
        )

        # Backfill: sessions linked from recruiter_interview_sessions are 'deep'
        if 'recruiter_interview_sessions' in inspector.get_table_names():
            bind.execute(text("""
                UPDATE voice_screening_sessions
                SET interview_depth = 'deep'
                WHERE id IN (
                    SELECT voice_session_id FROM recruiter_interview_sessions
                    WHERE voice_session_id IS NOT NULL
                )
            """))

    # Add index if not exists
    indexes = [idx['name'] for idx in inspector.get_indexes('voice_screening_sessions')]
    if 'ix_vss_interview_depth' not in indexes:
        op.create_index('ix_vss_interview_depth', 'voice_screening_sessions', ['interview_depth'])


def downgrade():
    op.drop_index('ix_vss_interview_depth', table_name='voice_screening_sessions')
    op.drop_column('voice_screening_sessions', 'interview_depth')
