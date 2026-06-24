"""Add AI Recruiter tables: recruiter_interview_sessions, recruiter_interview_questions, recruiter_scorecards, recruiter_auto_trigger_configs"""

revision = "045_ai_recruiter"
down_revision = "044_voice_screening"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def upgrade():
    insp = inspect(op.get_bind())
    existing = {t for t in insp.get_table_names()}

    # ── Recruiter Interview Sessions ─────────────────────────────────────────
    if 'recruiter_interview_sessions' not in existing:
        op.create_table(
            'recruiter_interview_sessions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('jd_id', sa.Integer(), sa.ForeignKey('role_templates.id', ondelete='CASCADE'), nullable=False),
            sa.Column('screening_result_id', sa.Integer(), sa.ForeignKey('screening_results.id', ondelete='SET NULL'), nullable=True),
            sa.Column('voice_session_id', sa.Integer(), sa.ForeignKey('voice_screening_sessions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('trigger_type', sa.String(20), nullable=False, server_default='manual'),
            sa.Column('status', sa.String(30), nullable=False, server_default='pending_strategy'),
            sa.Column('interview_strategy_json', sa.Text(), nullable=True),
            sa.Column('interview_config_json', sa.Text(), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_recruiter_sessions_tenant_status', 'recruiter_interview_sessions', ['tenant_id', 'status'])
        op.create_index('ix_recruiter_sessions_tenant_candidate', 'recruiter_interview_sessions', ['tenant_id', 'candidate_id'])
        op.create_index('ix_recruiter_sessions_candidate_jd', 'recruiter_interview_sessions', ['candidate_id', 'jd_id'])

    # ── Recruiter Interview Questions ────────────────────────────────────────
    if 'recruiter_interview_questions' not in existing:
        op.create_table(
            'recruiter_interview_questions',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('session_id', sa.String(36), sa.ForeignKey('recruiter_interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('sequence_number', sa.Integer(), nullable=False),
            sa.Column('category', sa.String(30), nullable=False),
            sa.Column('question_text', sa.Text(), nullable=False),
            sa.Column('question_context', sa.Text(), nullable=True),
            sa.Column('candidate_response', sa.Text(), nullable=True),
            sa.Column('response_duration_seconds', sa.Float(), nullable=True),
            sa.Column('evaluation_json', sa.Text(), nullable=True),
            sa.Column('is_follow_up', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('parent_question_id', sa.String(36), sa.ForeignKey('recruiter_interview_questions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_recruiter_questions_session_seq', 'recruiter_interview_questions', ['session_id', 'sequence_number'])

    # ── Recruiter Scorecards ─────────────────────────────────────────────────
    if 'recruiter_scorecards' not in existing:
        op.create_table(
            'recruiter_scorecards',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('session_id', sa.String(36), sa.ForeignKey('recruiter_interview_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('technical_score', sa.Integer(), nullable=True),
            sa.Column('technical_evidence', sa.Text(), nullable=True),
            sa.Column('behavioral_score', sa.Integer(), nullable=True),
            sa.Column('behavioral_evidence', sa.Text(), nullable=True),
            sa.Column('communication_score', sa.Integer(), nullable=True),
            sa.Column('communication_evidence', sa.Text(), nullable=True),
            sa.Column('cultural_fit_score', sa.Integer(), nullable=True),
            sa.Column('cultural_fit_evidence', sa.Text(), nullable=True),
            sa.Column('motivation_score', sa.Integer(), nullable=True),
            sa.Column('motivation_evidence', sa.Text(), nullable=True),
            sa.Column('risk_signals_validated', sa.Text(), nullable=True),
            sa.Column('gaps_explained', sa.Text(), nullable=True),
            sa.Column('original_fit_score', sa.Integer(), nullable=True),
            sa.Column('adjusted_fit_score', sa.Integer(), nullable=True),
            sa.Column('adjustment_reasoning', sa.Text(), nullable=True),
            sa.Column('overall_score', sa.Integer(), nullable=True),
            sa.Column('confidence_level', sa.String(10), nullable=True),
            sa.Column('recommendation', sa.String(20), nullable=True),
            sa.Column('recommendation_reasoning', sa.Text(), nullable=True),
            sa.Column('executive_summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_recruiter_scorecards_tenant_candidate', 'recruiter_scorecards', ['tenant_id', 'candidate_id'])

    # ── Recruiter Auto Trigger Configs ───────────────────────────────────────
    if 'recruiter_auto_trigger_configs' not in existing:
        op.create_table(
            'recruiter_auto_trigger_configs',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True, index=True),
            sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('trigger_pipeline_stage', sa.String(20), nullable=False, server_default='in_review'),
            sa.Column('min_fit_score_threshold', sa.Integer(), nullable=False, server_default='40'),
            sa.Column('max_fit_score_threshold', sa.Integer(), nullable=False, server_default='85'),
            sa.Column('auto_schedule_delay_minutes', sa.Integer(), nullable=False, server_default='60'),
            sa.Column('interview_duration_target', sa.Integer(), nullable=False, server_default='15'),
            sa.Column('focus_areas', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )


def downgrade():
    op.drop_index('ix_recruiter_scorecards_tenant_candidate', table_name='recruiter_scorecards')
    op.drop_table('recruiter_scorecards')

    op.drop_index('ix_recruiter_questions_session_seq', table_name='recruiter_interview_questions')
    op.drop_table('recruiter_interview_questions')

    op.drop_index('ix_recruiter_sessions_candidate_jd', table_name='recruiter_interview_sessions')
    op.drop_index('ix_recruiter_sessions_tenant_candidate', table_name='recruiter_interview_sessions')
    op.drop_index('ix_recruiter_sessions_tenant_status', table_name='recruiter_interview_sessions')
    op.drop_table('recruiter_interview_sessions')

    op.drop_table('recruiter_auto_trigger_configs')
