"""Interview kit enhancement - evaluations and assessments

Revision ID: 017
Revises: 016
Create Date: 2026-04-29
"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table already exists (idempotent guard)."""
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    # Interview evaluations table - per-question recruiter notes and ratings
    if not _table_exists("interview_evaluations"):
        op.create_table(
            "interview_evaluations",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("result_id", sa.Integer(), sa.ForeignKey("screening_results.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("question_category", sa.String(30), nullable=False),
            sa.Column("question_index", sa.Integer(), nullable=False),
            sa.Column("rating", sa.String(10), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("result_id", "user_id", "question_category", "question_index",
                               name="uq_eval_per_question"),
        )

    # Overall assessments table - recruiter's overall recommendation for HM
    if not _table_exists("overall_assessments"):
        op.create_table(
            "overall_assessments",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("result_id", sa.Integer(), sa.ForeignKey("screening_results.id"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("overall_assessment", sa.Text(), nullable=True),
            sa.Column("recruiter_recommendation", sa.String(10), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("result_id", "user_id", name="uq_overall_per_user"),
        )


def downgrade() -> None:
    if _table_exists("overall_assessments"):
        op.drop_table("overall_assessments")
    if _table_exists("interview_evaluations"):
        op.drop_table("interview_evaluations")
