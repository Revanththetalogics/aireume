"""Skill classification template persistence

Revision ID: 023_skill_template_persistence
Revises: 022_historical_learning_system
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "023_skill_template_persistence"
down_revision = "022_historical_learning_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    table_names = insp.get_table_names()

    if "skill_classification_templates" not in table_names:
        op.create_table(
            "skill_classification_templates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("role_template_id", sa.Integer(), sa.ForeignKey("role_templates.id"), nullable=True),
            sa.Column("required_skills", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("nice_to_have_skills", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_skill_class_tmpl_tenant", "skill_classification_templates", ["tenant_id"])
        op.create_index("ix_skill_class_tmpl_name", "skill_classification_templates", ["tenant_id", "name"])
    else:
        # Table exists from SQL script — add missing columns if any
        cols = {c["name"] for c in insp.get_columns("skill_classification_templates")}
        if "updated_at" not in cols:
            op.add_column("skill_classification_templates", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True))
        idx = {i["name"] for i in insp.get_indexes("skill_classification_templates")}
        if "ix_skill_class_tmpl_tenant" not in idx:
            op.create_index("ix_skill_class_tmpl_tenant", "skill_classification_templates", ["tenant_id"])
        if "ix_skill_class_tmpl_name" not in idx:
            op.create_index("ix_skill_class_tmpl_name", "skill_classification_templates", ["tenant_id", "name"])


def downgrade() -> None:
    op.drop_table("skill_classification_templates")
