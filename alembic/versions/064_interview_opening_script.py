"""Add tenant custom interview opening script fields."""

from alembic import op
import sqlalchemy as sa

revision = "064_interview_opening_script"
down_revision = "063_candidate_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("voice_tenant_configs")}

    if "interview_opening_script" not in cols:
        op.add_column(
            "voice_tenant_configs",
            sa.Column("interview_opening_script", sa.Text(), nullable=True),
        )
    if "use_custom_interview_opening" not in cols:
        op.add_column(
            "voice_tenant_configs",
            sa.Column(
                "use_custom_interview_opening",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "company_about_blurb" not in cols:
        op.add_column(
            "voice_tenant_configs",
            sa.Column("company_about_blurb", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("voice_tenant_configs")}

    if "company_about_blurb" in cols:
        op.drop_column("voice_tenant_configs", "company_about_blurb")
    if "use_custom_interview_opening" in cols:
        op.drop_column("voice_tenant_configs", "use_custom_interview_opening")
    if "interview_opening_script" in cols:
        op.drop_column("voice_tenant_configs", "interview_opening_script")
