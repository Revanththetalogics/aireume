"""Add hiring manager request fields on requisitions (recruiter request → admin approve)."""

from alembic import op
import sqlalchemy as sa

revision = "058_requisition_hm_requests"
down_revision = "057_interview_kit_error"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("requisitions")}
    if "hm_request_email" not in cols:
        op.add_column("requisitions", sa.Column("hm_request_email", sa.String(255), nullable=True))
    if "hm_request_status" not in cols:
        op.add_column("requisitions", sa.Column("hm_request_status", sa.String(30), nullable=True))
    if "hm_requested_by" not in cols:
        op.add_column(
            "requisitions",
            sa.Column("hm_requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
    if "hm_requested_at" not in cols:
        op.add_column("requisitions", sa.Column("hm_requested_at", sa.DateTime(timezone=True), nullable=True))
    if "hm_request_notes" not in cols:
        op.add_column("requisitions", sa.Column("hm_request_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("requisitions")}
    for col in ("hm_request_notes", "hm_requested_at", "hm_requested_by", "hm_request_status", "hm_request_email"):
        if col in cols:
            op.drop_column("requisitions", col)
