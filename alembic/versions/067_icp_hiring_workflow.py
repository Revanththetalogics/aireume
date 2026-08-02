"""ICP hiring workflow — assignment, HM requests, routing policy."""

from alembic import op
import sqlalchemy as sa

revision = "067_icp_hiring_workflow"
down_revision = "066_screening_mode"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "requisitions",
        sa.Column("assigned_recruiter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "requisitions",
        sa.Column("opened_on_behalf_of_hm_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column("requisitions", sa.Column("routing_policy_json", sa.Text(), nullable=True))
    op.create_index("ix_requisitions_assigned_recruiter", "requisitions", ["assigned_recruiter_id"])

    op.create_table(
        "requisition_open_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("jd_text", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("headcount", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("assigned_recruiter_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("requisitions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("requisition_open_requests")
    op.drop_index("ix_requisitions_assigned_recruiter", "requisitions")
    op.drop_column("requisitions", "routing_policy_json")
    op.drop_column("requisitions", "opened_on_behalf_of_hm_id")
    op.drop_column("requisitions", "assigned_recruiter_id")
