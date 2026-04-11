"""Add narrative_status and narrative_error columns to screening_results

Revision ID: 007
Revises: 006
Create Date: 2026-04-11

Changes:
  - screening_results: add narrative_status column (String(20), default='pending')
  - screening_results: add narrative_error column (Text, nullable=True)
  - Backfill existing rows: set narrative_status='ready' where narrative_json IS NOT NULL

Idempotent: safe when columns already exist.
"""
from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()
    cols = _column_names(insp, "screening_results")

    # Add narrative_status column if missing
    if "narrative_status" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("narrative_status", sa.String(20), nullable=True, server_default="pending")
        )

    # Add narrative_error column if missing
    if "narrative_error" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("narrative_error", sa.Text, nullable=True)
        )

    # Backfill existing data: rows with narrative_json should be 'ready'
    # Only run backfill if narrative_json column exists (it may not on local SQLite
    # where intermediate migrations were stamped rather than applied)
    cols = _column_names(_inspector(), "screening_results")
    if "narrative_json" in cols:
        op.execute(
            "UPDATE screening_results SET narrative_status = 'ready' WHERE narrative_json IS NOT NULL AND narrative_status IS NULL"
        )


def downgrade() -> None:
    # Drop columns using batch_alter_table for SQLite compatibility
    with op.batch_alter_table("screening_results") as batch_op:
        batch_op.drop_column("narrative_error")
        batch_op.drop_column("narrative_status")
