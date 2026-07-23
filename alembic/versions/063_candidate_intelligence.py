"""Add candidate_intelligence_json to screening_results."""

from alembic import op
import sqlalchemy as sa

revision = "063_candidate_intelligence"
down_revision = "062_analytics_views_reports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("screening_results")}

    if "candidate_intelligence_json" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("candidate_intelligence_json", sa.Text(), nullable=True),
        )
    if "candidate_intelligence_status" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("candidate_intelligence_status", sa.String(32), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("screening_results")}
    if "candidate_intelligence_status" in cols:
        op.drop_column("screening_results", "candidate_intelligence_status")
    if "candidate_intelligence_json" in cols:
        op.drop_column("screening_results", "candidate_intelligence_json")
