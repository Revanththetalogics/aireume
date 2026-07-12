"""Enterprise suite: OAuth identities, trials, CRM, white-label branding."""

from alembic import op
import sqlalchemy as sa

revision = "060_enterprise_suite"
down_revision = "059_enterprise_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    tenant_cols = {c["name"] for c in insp.get_columns("tenants")}
    additions = [
        ("trial_ends_at", sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True)),
        ("health_score", sa.Column("health_score", sa.Integer(), nullable=True)),
        ("churn_risk", sa.Column("churn_risk", sa.String(20), nullable=True)),
        ("custom_domain", sa.Column("custom_domain", sa.String(255), nullable=True)),
        ("brand_name", sa.Column("brand_name", sa.String(200), nullable=True)),
        ("brand_logo_url", sa.Column("brand_logo_url", sa.String(500), nullable=True)),
        ("brand_primary_color", sa.Column("brand_primary_color", sa.String(20), nullable=True)),
        ("brand_favicon_url", sa.Column("brand_favicon_url", sa.String(500), nullable=True)),
    ]
    for name, col in additions:
        if name not in tenant_cols:
            op.add_column("tenants", col)

    if "custom_domain" not in tenant_cols:
        op.create_index("ix_tenants_custom_domain", "tenants", ["custom_domain"], unique=True)

    tables = insp.get_table_names()
    if "user_oauth_identities" not in tables:
        op.create_table(
            "user_oauth_identities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("provider_user_id", sa.String(255), nullable=False),
            sa.Column("email_at_link", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        )

    if "tenant_account_notes" not in tables:
        op.create_table(
            "tenant_account_notes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("note_type", sa.String(30), nullable=False, server_default="general"),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if "tenant_nps_responses" not in tables:
        op.create_table(
            "tenant_nps_responses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()
    for t in ("tenant_nps_responses", "tenant_account_notes", "user_oauth_identities"):
        if t in tables:
            op.drop_table(t)
    tenant_cols = {c["name"] for c in insp.get_columns("tenants")}
    for col in ("brand_favicon_url", "brand_primary_color", "brand_logo_url", "brand_name",
                "custom_domain", "churn_risk", "health_score", "trial_ends_at"):
        if col in tenant_cols:
            if col == "custom_domain":
                op.drop_index("ix_tenants_custom_domain", table_name="tenants")
            op.drop_column("tenants", col)
