"""Enterprise RBAC phase 2 — req ownership, HM share links, SSO group mapping.

Revision ID: 055_enterprise_rbac_phase2
Revises: 054_interview_outcome
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

revision = "055_enterprise_rbac_phase2"
down_revision = "054_interview_outcome"
branch_labels = None
depends_on = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table)}


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade() -> None:
    if "role_templates" in sa.inspect(op.get_bind()).get_table_names():
        cols = _existing_columns("role_templates")
        if "created_by" not in cols:
            op.add_column(
                "role_templates",
                sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            )

    if "sso_configs" in sa.inspect(op.get_bind()).get_table_names():
        cols = _existing_columns("sso_configs")
        if "groups_attribute" not in cols:
            op.add_column(
                "sso_configs",
                sa.Column("groups_attribute", sa.String(100), nullable=True, server_default="groups"),
            )

    if not _table_exists("sso_group_role_mappings"):
        op.create_table(
            "sso_group_role_mappings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("idp_group", sa.String(255), nullable=False),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("tenant_id", "idp_group", name="uq_sso_group_mapping"),
        )
        op.create_index("ix_sso_group_role_mappings_tenant_id", "sso_group_role_mappings", ["tenant_id"])

    if not _table_exists("handoff_share_links"):
        op.create_table(
            "handoff_share_links",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token", sa.String(64), nullable=False, unique=True, index=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role_template_id", sa.Integer(), sa.ForeignKey("role_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("label", sa.String(200), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_handoff_share_links_tenant_id", "handoff_share_links", ["tenant_id"])
        op.create_index("ix_handoff_share_links_role_template_id", "handoff_share_links", ["role_template_id"])


def downgrade() -> None:
    if _table_exists("handoff_share_links"):
        op.drop_table("handoff_share_links")
    if _table_exists("sso_group_role_mappings"):
        op.drop_table("sso_group_role_mappings")
    if "sso_configs" in sa.inspect(op.get_bind()).get_table_names():
        cols = _existing_columns("sso_configs")
        if "groups_attribute" in cols:
            op.drop_column("sso_configs", "groups_attribute")
    if "role_templates" in sa.inspect(op.get_bind()).get_table_names():
        cols = _existing_columns("role_templates")
        if "created_by" in cols:
            op.drop_column("role_templates", "created_by")
