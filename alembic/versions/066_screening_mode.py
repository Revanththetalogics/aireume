"""Add screening_mode to tenant requisition settings."""

from alembic import op
import sqlalchemy as sa

revision = "066_screening_mode"
down_revision = "065_user_prefs_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("tenant_requisition_settings")}
    if "screening_mode" not in cols:
        op.add_column(
            "tenant_requisition_settings",
            sa.Column(
                "screening_mode",
                sa.String(30),
                nullable=False,
                server_default="requisition_required",
            ),
        )


def downgrade() -> None:
    op.drop_column("tenant_requisition_settings", "screening_mode")
