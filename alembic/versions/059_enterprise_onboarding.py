"""Enterprise onboarding: tenant contact_email, user getting_started_progress."""

from alembic import op
import sqlalchemy as sa

revision = "059_enterprise_onboarding"
down_revision = "058_requisition_hm_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tenant_cols = {c["name"] for c in insp.get_columns("tenants")}
    if "contact_email" not in tenant_cols:
        op.add_column("tenants", sa.Column("contact_email", sa.String(255), nullable=True))

    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "getting_started_progress" not in user_cols:
        op.add_column(
            "users",
            sa.Column("getting_started_progress", sa.Text(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tenant_cols = {c["name"] for c in insp.get_columns("tenants")}
    if "contact_email" in tenant_cols:
        op.drop_column("tenants", "contact_email")

    user_cols = {c["name"] for c in insp.get_columns("users")}
    if "getting_started_progress" in user_cols:
        op.drop_column("users", "getting_started_progress")
