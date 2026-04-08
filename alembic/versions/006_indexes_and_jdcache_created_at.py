"""add indexes to screening_results and created_at to jd_cache

Revision ID: 006
Revises: 004
Create Date: 2026-04-08

Changes:
  - screening_results: add index on candidate_id
  - screening_results: add index on timestamp
  - jd_cache: add created_at column (if missing)

Idempotent: safe when indexes/columns already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _index_names(insp, table: str) -> set:
    return {i["name"] for i in insp.get_indexes(table)}


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()

    # ── screening_results: add indexes ────────────────────────────────────────
    idx = _index_names(insp, "screening_results")

    if "ix_screening_results_candidate_id" not in idx:
        op.create_index(
            "ix_screening_results_candidate_id",
            "screening_results",
            ["candidate_id"]
        )

    if "ix_screening_results_timestamp" not in idx:
        op.create_index(
            "ix_screening_results_timestamp",
            "screening_results",
            ["timestamp"]
        )

    # ── jd_cache: add created_at column if missing ────────────────────────────
    insp = _inspector()
    jd_cols = _column_names(insp, "jd_cache")
    if "created_at" not in jd_cols:
        op.add_column(
            "jd_cache",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now())
        )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_screening_results_timestamp", table_name="screening_results")
    op.drop_index("ix_screening_results_candidate_id", table_name="screening_results")

    # Drop created_at column from jd_cache
    with op.batch_alter_table("jd_cache") as batch_op:
        batch_op.drop_column("created_at")
