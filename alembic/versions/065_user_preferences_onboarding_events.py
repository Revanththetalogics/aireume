"""User preferences JSON and onboarding funnel events."""

from alembic import op
import sqlalchemy as sa

revision = "065_user_prefs_events"
down_revision = "064_interview_opening_script"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "preferences_json" not in user_cols:
        op.add_column(
            "users",
            sa.Column("preferences_json", sa.Text(), nullable=False, server_default="{}"),
        )

    if not insp.has_table("onboarding_funnel_events"):
        op.create_table(
            "onboarding_funnel_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("event_name", sa.String(100), nullable=False),
            sa.Column("properties_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_onboarding_funnel_events_tenant_id", "onboarding_funnel_events", ["tenant_id"])
        op.create_index("ix_onboarding_funnel_events_event_name", "onboarding_funnel_events", ["event_name"])
        op.create_index("ix_onboarding_funnel_events_created_at", "onboarding_funnel_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("onboarding_funnel_events")
    op.drop_column("users", "preferences_json")
