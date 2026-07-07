"""Add interview kit and voice strategy background enrichment columns

Revision ID: 053_background_enrichment_status
Revises: 052_dead_letter_jobs
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "053_background_enrichment_status"
down_revision = "052_dead_letter_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("screening_results")}

    if "interview_kit_status" not in cols:
        op.add_column(
            "screening_results",
            sa.Column(
                "interview_kit_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
        )
    if "voice_strategy_json" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("voice_strategy_json", sa.Text(), nullable=True),
        )
    if "voice_strategy_status" not in cols:
        op.add_column(
            "screening_results",
            sa.Column(
                "voice_strategy_status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
        )
    if "voice_strategy_config_hash" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("voice_strategy_config_hash", sa.String(64), nullable=True),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("screening_results")}

    if "voice_strategy_config_hash" in cols:
        op.drop_column("screening_results", "voice_strategy_config_hash")
    if "voice_strategy_status" in cols:
        op.drop_column("screening_results", "voice_strategy_status")
    if "voice_strategy_json" in cols:
        op.drop_column("screening_results", "voice_strategy_json")
    if "interview_kit_status" in cols:
        op.drop_column("screening_results", "interview_kit_status")
