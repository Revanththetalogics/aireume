"""ICP hiring workflow — assignment, HM requests, routing policy.

Idempotent: migration 001 materializes `requisitions` from current model metadata,
so these columns may already exist on a fresh `alembic upgrade heads`.
"""

from alembic import op
import sqlalchemy as sa

revision = "067_icp_hiring_workflow"
down_revision = "066_screening_mode"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(table: str) -> set[str]:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if table not in insp.get_table_names():
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade():
    cols = _columns("requisitions")
    if "assigned_recruiter_id" not in cols:
        op.add_column(
            "requisitions",
            sa.Column(
                "assigned_recruiter_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "opened_on_behalf_of_hm_id" not in cols:
        op.add_column(
            "requisitions",
            sa.Column(
                "opened_on_behalf_of_hm_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    if "routing_policy_json" not in cols:
        op.add_column("requisitions", sa.Column("routing_policy_json", sa.Text(), nullable=True))

    if "ix_requisitions_assigned_recruiter" not in _indexes("requisitions"):
        op.create_index(
            "ix_requisitions_assigned_recruiter",
            "requisitions",
            ["assigned_recruiter_id"],
        )

    if not _table_exists("requisition_open_requests"):
        op.create_table(
            "requisition_open_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "tenant_id",
                sa.Integer(),
                sa.ForeignKey("tenants.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "requested_by",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("jd_text", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("location", sa.String(200), nullable=True),
            sa.Column("headcount", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column(
                "assigned_recruiter_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "requisition_id",
                sa.Integer(),
                sa.ForeignKey("requisitions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "assigned_by",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade():
    if _table_exists("requisition_open_requests"):
        op.drop_table("requisition_open_requests")
    if "ix_requisitions_assigned_recruiter" in _indexes("requisitions"):
        op.drop_index("ix_requisitions_assigned_recruiter", "requisitions")
    cols = _columns("requisitions")
    for col in ("routing_policy_json", "opened_on_behalf_of_hm_id", "assigned_recruiter_id"):
        if col in cols:
            op.drop_column("requisitions", col)
