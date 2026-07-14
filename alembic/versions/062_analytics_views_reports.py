"""Analytics saved views, custom reports, and scheduled report delivery."""

from alembic import op
import sqlalchemy as sa

revision = "062_analytics_views_reports"
down_revision = "061_gtm_plan_tiers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    if "saved_analytics_views" not in tables:
        op.create_table(
            "saved_analytics_views",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("view_type", sa.String(20), nullable=False, server_default="explore"),
            sa.Column("slice", sa.String(30), nullable=True),
            sa.Column("filters", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        )
        op.create_index(
            "ix_saved_analytics_views_user_default",
            "saved_analytics_views",
            ["user_id", "is_default"],
        )

    if "saved_reports" not in tables:
        op.create_table(
            "saved_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("definition", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("shared_with_tenant", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("share_token", sa.String(64), nullable=True, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        )

    if "scheduled_reports" not in tables:
        op.create_table(
            "scheduled_reports",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("saved_report_id", sa.Integer(), sa.ForeignKey("saved_reports.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("schedule", sa.String(20), nullable=False),
            sa.Column("recipients", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("scheduled_reports")
    op.drop_table("saved_reports")
    op.drop_index("ix_saved_analytics_views_user_default", table_name="saved_analytics_views")
    op.drop_table("saved_analytics_views")
