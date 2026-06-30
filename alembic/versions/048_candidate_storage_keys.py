"""Add resume_file_key and resume_pdf_key to candidates table

Revision ID: 048_candidate_storage_keys
Revises: 047_adaptive_depth_escalation
Create Date: 2026-06-01

Changes:
  - candidates: add resume_file_key (String 500) for S3/MinIO object key
  - candidates: add resume_pdf_key (String 500) for S3/MinIO PDF object key

These columns were added to the SQLAlchemy model but never had a
corresponding Alembic migration, causing 500 errors on any query that
loads Candidate objects (e.g. GET /api/candidates, GET /api/dashboard/activity).

Idempotent: safe when columns already exist.
"""
from alembic import op
import sqlalchemy as sa


revision = "048_candidate_storage_keys"
down_revision = "047_adaptive_depth_escalation"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade():
    insp = _inspector()
    cols = _column_names(insp, "candidates")

    if "resume_file_key" not in cols:
        op.add_column(
            "candidates",
            sa.Column("resume_file_key", sa.String(500), nullable=True),
        )

    if "resume_pdf_key" not in cols:
        op.add_column(
            "candidates",
            sa.Column("resume_pdf_key", sa.String(500), nullable=True),
        )


def downgrade():
    op.drop_column("candidates", "resume_pdf_key")
    op.drop_column("candidates", "resume_file_key")
