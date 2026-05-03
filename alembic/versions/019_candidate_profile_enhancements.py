"""Candidate profile enhancements: AI summary + candidate notes

Revision ID: 019
Revises: 018
Create Date: 2026-05-03

Changes:
  - Add ai_professional_summary to candidates table
  - Create candidate_notes table

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()

    # -- Add ai_professional_summary to candidates table --
    insp = _inspector()
    cols = _column_names(insp, "candidates")
    if "ai_professional_summary" not in cols:
        op.add_column(
            "candidates",
            sa.Column("ai_professional_summary", sa.Text(), nullable=True),
        )

    # -- Create candidate_notes table --
    if not _table_exists(insp, "candidate_notes"):
        op.create_table(
            "candidate_notes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    # Drop candidate_notes table
    op.drop_table("candidate_notes")

    # Remove ai_professional_summary from candidates
    op.drop_column("candidates", "ai_professional_summary")
