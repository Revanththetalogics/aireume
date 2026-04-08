"""Add narrative_json column to screening_results for async LLM narrative

Revision ID: 004
Revises: 003
Create Date: 2026-04-07

Changes:
  - screening_results: add narrative_json TEXT column (nullable)
    Stores LLM-generated narrative separately from main analysis_result.
    This allows Python scoring results to be returned immediately while
    the LLM narrative is generated as a background task and polled later.

Idempotent: skips if column already exists.
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("screening_results")}
    if "narrative_json" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("narrative_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    with op.batch_alter_table("screening_results") as batch_op:
        batch_op.drop_column("narrative_json")
