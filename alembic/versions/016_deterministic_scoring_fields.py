"""Add deterministic scoring fields to screening_results table

Revision ID: 016
Revises: 015_add_resume_file_storage
Create Date: 2026-04-27

Changes:
  - screening_results: add deterministic_score (Integer)
  - screening_results: add domain_match_score (Float)
  - screening_results: add core_skill_score (Float)
  - screening_results: add eligibility_status (Boolean)
  - screening_results: add eligibility_reason (String 100)

Idempotent: safe when columns already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()
    cols = _column_names(insp, "screening_results")

    if "deterministic_score" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("deterministic_score", sa.Integer, nullable=True),
        )

    if "domain_match_score" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("domain_match_score", sa.Float, nullable=True),
        )

    if "core_skill_score" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("core_skill_score", sa.Float, nullable=True),
        )

    if "eligibility_status" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("eligibility_status", sa.Boolean, nullable=True),
        )

    if "eligibility_reason" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("eligibility_reason", sa.String(100), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("screening_results", "eligibility_reason")
    op.drop_column("screening_results", "eligibility_status")
    op.drop_column("screening_results", "core_skill_score")
    op.drop_column("screening_results", "domain_match_score")
    op.drop_column("screening_results", "deterministic_score")
