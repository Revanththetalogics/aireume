"""Add interview_kit_error column for kit fallback diagnostics."""

from alembic import op
import sqlalchemy as sa

revision = "057_interview_kit_error"
down_revision = "056_requisitions_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("screening_results")}
    if "interview_kit_error" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("interview_kit_error", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("screening_results")}
    if "interview_kit_error" in cols:
        op.drop_column("screening_results", "interview_kit_error")
