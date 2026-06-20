"""Add voice screening tables: voice_tenant_configs, voice_screening_sessions, voice_transcript_entries"""

revision = "044_voice_screening"
down_revision = "043_platform_settings"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def upgrade():
    insp = inspect(op.get_bind())
    existing = {t for t in insp.get_table_names()}

    # ── Voice Tenant Config ──────────────────────────────────────────────────
    if 'voice_tenant_configs' not in existing:
        op.create_table(
            'voice_tenant_configs',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('bot_name', sa.String(100), nullable=False, server_default='ARIA Assistant'),
            sa.Column('bot_voice_gender', sa.String(10), nullable=False, server_default='female'),
            sa.Column('bot_voice_sample_url', sa.Text(), nullable=True),
            sa.Column('outbound_phone_number', sa.String(20), nullable=True),
            sa.Column('caller_id_name', sa.String(100), nullable=True),
            sa.Column('business_hours_start', sa.String(5), nullable=False, server_default='09:00'),
            sa.Column('business_hours_end', sa.String(5), nullable=False, server_default='18:00'),
            sa.Column('allowed_days', sa.JSON(), nullable=False, server_default=sa.text("'[1,2,3,4,5]'")),
            sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
            sa.Column('consent_script', sa.Text(), nullable=True),
            sa.Column('greeting_style', sa.String(20), nullable=False, server_default='professional'),
            sa.Column('call_duration_min', sa.Integer(), nullable=False, server_default='5'),
            sa.Column('call_duration_max', sa.Integer(), nullable=False, server_default='7'),
            sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('retry_intervals', sa.JSON(), nullable=False, server_default=sa.text("'[24,48]'")),
            sa.Column('escalation_contact_id', sa.Integer(), sa.ForeignKey('team_members.id', ondelete='SET NULL'), nullable=True),
            sa.Column('assessment_detail_level', sa.String(10), nullable=False, server_default='full'),
            sa.Column('auto_update_status', sa.Boolean(), nullable=False, server_default=sa.text('true')),
            sa.Column('follow_up_aggressiveness', sa.String(10), nullable=False, server_default='medium'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )
        op.create_index('ix_voice_tenant_configs_tenant_id', 'voice_tenant_configs', ['tenant_id'])

    # ── Voice Screening Sessions ─────────────────────────────────────────────
    if 'voice_screening_sessions' not in existing:
        op.create_table(
            'voice_screening_sessions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
            sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
            sa.Column('jd_id', sa.Integer(), sa.ForeignKey('role_templates.id', ondelete='SET NULL'), nullable=True),
            sa.Column('phone_number', sa.String(20), nullable=False),
            sa.Column('direction', sa.String(10), nullable=False, server_default='outbound'),
            sa.Column('callback_of_id', sa.Integer(), sa.ForeignKey('voice_screening_sessions.id', ondelete='SET NULL'), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
            sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('transcript_json', sa.Text(), nullable=True),
            sa.Column('assessment_json', sa.Text(), nullable=True),
            sa.Column('duration_seconds', sa.Integer(), nullable=True),
            sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('consent_recorded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('call_sid', sa.String(100), nullable=True),
            sa.Column('error_log', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )
        op.create_index('ix_voice_screening_sessions_tenant_id', 'voice_screening_sessions', ['tenant_id'])
        op.create_index('ix_voice_screening_sessions_candidate_id', 'voice_screening_sessions', ['candidate_id'])
        op.create_index('ix_voice_screening_sessions_status', 'voice_screening_sessions', ['status'])
        op.create_index('ix_voice_sessions_tenant_candidate', 'voice_screening_sessions', ['tenant_id', 'candidate_id'])
        op.create_index('ix_voice_sessions_phone_status', 'voice_screening_sessions', ['phone_number', 'status'])

    # ── Voice Transcript Entries ─────────────────────────────────────────────
    if 'voice_transcript_entries' not in existing:
        op.create_table(
            'voice_transcript_entries',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('session_id', sa.Integer(), sa.ForeignKey('voice_screening_sessions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('speaker', sa.String(10), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
            sa.Column('audio_url', sa.Text(), nullable=True),
        )
        op.create_index('ix_voice_transcript_entries_session_id', 'voice_transcript_entries', ['session_id'])
        op.create_index('ix_voice_transcript_session_ts', 'voice_transcript_entries', ['session_id', 'timestamp'])


def downgrade():
    op.drop_index('ix_voice_transcript_session_ts', table_name='voice_transcript_entries')
    op.drop_index('ix_voice_transcript_entries_session_id', table_name='voice_transcript_entries')
    op.drop_table('voice_transcript_entries')

    op.drop_index('ix_voice_sessions_phone_status', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_sessions_tenant_candidate', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_screening_sessions_status', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_screening_sessions_candidate_id', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_screening_sessions_tenant_id', table_name='voice_screening_sessions')
    op.drop_table('voice_screening_sessions')

    op.drop_index('ix_voice_tenant_configs_tenant_id', table_name='voice_tenant_configs')
    op.drop_table('voice_tenant_configs')
"""Add voice screening tables: voice_tenant_configs, voice_screening_sessions, voice_transcript_entries"""

revision = "044_voice_screening"
down_revision = "043_platform_settings"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ── Voice Tenant Config ──────────────────────────────────────────────────
    op.create_table(
        'voice_tenant_configs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('bot_name', sa.String(100), nullable=False, server_default='ARIA Assistant'),
        sa.Column('bot_voice_gender', sa.String(10), nullable=False, server_default='female'),
        sa.Column('bot_voice_sample_url', sa.Text(), nullable=True),
        sa.Column('outbound_phone_number', sa.String(20), nullable=True),
        sa.Column('caller_id_name', sa.String(100), nullable=True),
        sa.Column('business_hours_start', sa.String(5), nullable=False, server_default='09:00'),
        sa.Column('business_hours_end', sa.String(5), nullable=False, server_default='18:00'),
        sa.Column('allowed_days', sa.JSON(), nullable=False, server_default=sa.text("'[1,2,3,4,5]'")),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('consent_script', sa.Text(), nullable=True),
        sa.Column('greeting_style', sa.String(20), nullable=False, server_default='professional'),
        sa.Column('call_duration_min', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('call_duration_max', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('retry_intervals', sa.JSON(), nullable=False, server_default=sa.text("'[24,48]'")),
        sa.Column('escalation_contact_id', sa.Integer(), sa.ForeignKey('team_members.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assessment_detail_level', sa.String(10), nullable=False, server_default='full'),
        sa.Column('auto_update_status', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('follow_up_aggressiveness', sa.String(10), nullable=False, server_default='medium'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_voice_tenant_configs_tenant_id', 'voice_tenant_configs', ['tenant_id'])

    # ── Voice Screening Sessions ─────────────────────────────────────────────
    op.create_table(
        'voice_screening_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('jd_id', sa.Integer(), sa.ForeignKey('role_templates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('phone_number', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False, server_default='outbound'),
        sa.Column('callback_of_id', sa.Integer(), sa.ForeignKey('voice_screening_sessions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='scheduled'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('transcript_json', sa.Text(), nullable=True),
        sa.Column('assessment_json', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('consent_recorded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('call_sid', sa.String(100), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_voice_screening_sessions_tenant_id', 'voice_screening_sessions', ['tenant_id'])
    op.create_index('ix_voice_screening_sessions_candidate_id', 'voice_screening_sessions', ['candidate_id'])
    op.create_index('ix_voice_screening_sessions_status', 'voice_screening_sessions', ['status'])
    op.create_index('ix_voice_sessions_tenant_candidate', 'voice_screening_sessions', ['tenant_id', 'candidate_id'])
    op.create_index('ix_voice_sessions_phone_status', 'voice_screening_sessions', ['phone_number', 'status'])

    # ── Voice Transcript Entries ─────────────────────────────────────────────
    op.create_table(
        'voice_transcript_entries',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.Integer(), sa.ForeignKey('voice_screening_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('speaker', sa.String(10), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('audio_url', sa.Text(), nullable=True),
    )
    op.create_index('ix_voice_transcript_entries_session_id', 'voice_transcript_entries', ['session_id'])
    op.create_index('ix_voice_transcript_session_ts', 'voice_transcript_entries', ['session_id', 'timestamp'])


def downgrade():
    op.drop_index('ix_voice_transcript_session_ts', table_name='voice_transcript_entries')
    op.drop_index('ix_voice_transcript_entries_session_id', table_name='voice_transcript_entries')
    op.drop_table('voice_transcript_entries')

    op.drop_index('ix_voice_sessions_phone_status', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_sessions_tenant_candidate', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_screening_sessions_status', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_screening_sessions_candidate_id', table_name='voice_screening_sessions')
    op.drop_index('ix_voice_screening_sessions_tenant_id', table_name='voice_screening_sessions')
    op.drop_table('voice_screening_sessions')

    op.drop_index('ix_voice_tenant_configs_tenant_id', table_name='voice_tenant_configs')
    op.drop_table('voice_tenant_configs')
