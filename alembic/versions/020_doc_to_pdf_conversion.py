"""DOC to PDF conversion support

Revision ID: 020
Revises: 019
Create Date: 2026-05-03

Changes:
  - Add resume_converted_pdf_data to candidates table (stores PDF conversion of .doc files)

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()
    cols = _column_names(insp, "candidates")

    if "resume_converted_pdf_data" not in cols:
        op.add_column(
            "candidates",
            sa.Column("resume_converted_pdf_data", sa.LargeBinary, nullable=True),
        )


def downgrade() -> None:
    insp = _inspector()
    cols = _column_names(insp, "candidates")

    if "resume_converted_pdf_data" in cols:
        op.drop_column("candidates", "resume_converted_pdf_data")
