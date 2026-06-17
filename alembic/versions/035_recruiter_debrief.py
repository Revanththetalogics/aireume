"""Add recruiter debrief fields to overall_assessments."""

from alembic import op
import sqlalchemy as sa

revision = "035_recruiter_debrief"
down_revision = "034_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Idempotent: check if columns already exist before adding
    cols = {r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'overall_assessments'"
    )).fetchall()}

    if "debrief_json" not in cols:
        op.add_column("overall_assessments", sa.Column("debrief_json", sa.Text(), nullable=True))
    if "recruiter_score" not in cols:
        op.add_column("overall_assessments", sa.Column("recruiter_score", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("overall_assessments", "recruiter_score")
    op.drop_column("overall_assessments", "debrief_json")
