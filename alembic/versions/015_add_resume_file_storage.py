"""Add resume file storage to candidates table

Revision ID: 015
Revises: 014_billing_system
Create Date: 2026-04-25

Changes:
  - candidates: add resume_filename (String 255) and resume_file_data (LargeBinary/BYTEA)

Idempotent: safe when columns already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()
    cand_cols = _column_names(insp, "candidates")

    if "resume_filename" not in cand_cols:
        op.add_column(
            "candidates",
            sa.Column("resume_filename", sa.String(255), nullable=True),
        )

    if "resume_file_data" not in cand_cols:
        op.add_column(
            "candidates",
            sa.Column("resume_file_data", sa.LargeBinary, nullable=True),
        )


def downgrade() -> None:
    op.drop_column("candidates", "resume_file_data")
    op.drop_column("candidates", "resume_filename")
