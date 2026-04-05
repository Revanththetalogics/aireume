"""Add parser_snapshot_json to candidates for full parse output storage

Revision ID: 002
Revises: 001
Create Date: 2026-04-05

Stores complete JSON from parse_resume (contact_info including linkedin, etc.)
so re-analysis and audits do not depend on re-parsing patterns alone.

Idempotent: skips if column already exists.
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("candidates")}
    if "parser_snapshot_json" not in cols:
        op.add_column(
            "candidates",
            sa.Column("parser_snapshot_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_column("parser_snapshot_json")
