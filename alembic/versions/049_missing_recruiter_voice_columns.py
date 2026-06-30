"""Add missing columns to recruiter and voice tables.

Revision ID: 049_missing_recruiter_voice_columns
Revises: 048_candidate_storage_keys
Create Date: 2026-07-01

Changes:
  - recruiter_interview_sessions: add consent_status (String 20, default 'pending')
  - recruiter_auto_trigger_configs: add auto_status_update_enabled (Boolean, default false)
  - recruiter_auto_trigger_configs: add auto_status_mapping_json (Text, nullable)
  - recruiter_auto_trigger_configs: add require_consent (Boolean, default true)
  - recruiter_auto_trigger_configs: add evaluator_model_json (Text, nullable)
  - voice_screening_sessions: add consent_status (String 20, nullable)
  - voice_transcript_entries: add question_id (String 36, nullable)

These columns were added to the SQLAlchemy models but never had
corresponding Alembic migrations, causing 500 errors on any query that
loads these models (e.g. GET /api/interviews/sessions, POST /api/voice/schedule).

Idempotent: safe when columns already exist.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "049_missing_recruiter_voice_columns"
down_revision = "048_candidate_storage_keys"
branch_labels = None
depends_on = None


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade():
    insp = inspect(op.get_bind())

    # ── recruiter_interview_sessions.consent_status ──────────────────────────
    if "recruiter_interview_sessions" in insp.get_table_names():
        cols = _column_names(insp, "recruiter_interview_sessions")
        if "consent_status" not in cols:
            op.add_column(
                "recruiter_interview_sessions",
                sa.Column(
                    "consent_status",
                    sa.String(20),
                    nullable=False,
                    server_default="pending",
                ),
            )

    # ── recruiter_auto_trigger_configs (4 missing columns) ───────────────────
    if "recruiter_auto_trigger_configs" in insp.get_table_names():
        cols = _column_names(insp, "recruiter_auto_trigger_configs")

        if "auto_status_update_enabled" not in cols:
            op.add_column(
                "recruiter_auto_trigger_configs",
                sa.Column(
                    "auto_status_update_enabled",
                    sa.Boolean,
                    nullable=False,
                    server_default=sa.text("false"),
                ),
            )

        if "auto_status_mapping_json" not in cols:
            op.add_column(
                "recruiter_auto_trigger_configs",
                sa.Column("auto_status_mapping_json", sa.Text, nullable=True),
            )

        if "require_consent" not in cols:
            op.add_column(
                "recruiter_auto_trigger_configs",
                sa.Column(
                    "require_consent",
                    sa.Boolean,
                    nullable=False,
                    server_default=sa.text("true"),
                ),
            )

        if "evaluator_model_json" not in cols:
            op.add_column(
                "recruiter_auto_trigger_configs",
                sa.Column("evaluator_model_json", sa.Text, nullable=True),
            )

    # ── voice_screening_sessions.consent_status ──────────────────────────────
    if "voice_screening_sessions" in insp.get_table_names():
        cols = _column_names(insp, "voice_screening_sessions")
        if "consent_status" not in cols:
            op.add_column(
                "voice_screening_sessions",
                sa.Column("consent_status", sa.String(20), nullable=True),
            )

    # ── voice_transcript_entries.question_id ─────────────────────────────────
    if "voice_transcript_entries" in insp.get_table_names():
        cols = _column_names(insp, "voice_transcript_entries")
        if "question_id" not in cols:
            op.add_column(
                "voice_transcript_entries",
                sa.Column("question_id", sa.String(36), nullable=True),
            )


def downgrade():
    op.drop_column("voice_transcript_entries", "question_id")
    op.drop_column("voice_screening_sessions", "consent_status")
    op.drop_column("recruiter_auto_trigger_configs", "evaluator_model_json")
    op.drop_column("recruiter_auto_trigger_configs", "require_consent")
    op.drop_column("recruiter_auto_trigger_configs", "auto_status_mapping_json")
    op.drop_column("recruiter_auto_trigger_configs", "auto_status_update_enabled")
    op.drop_column("recruiter_interview_sessions", "consent_status")
