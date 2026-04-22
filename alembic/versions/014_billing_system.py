"""Billing system: platform_configs table for payment provider settings

Revision ID: 014
Revises: 013
Create Date: 2026-04-22

Changes:
  - Create platform_configs table for storing billing provider configuration

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _index_names(insp, table: str) -> set:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    insp = _inspector()

    # ── Create platform_configs table ──────────────────────────────────────────
    if not _table_exists(insp, "platform_configs"):
        op.create_table(
            "platform_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("config_key", sa.String(255), unique=True, nullable=False),
            sa.Column("config_value", sa.Text(), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_platform_configs_id", "platform_configs", ["id"])
        op.create_index("ix_platform_configs_config_key", "platform_configs", ["config_key"])
    else:
        insp = _inspector()
        idx = _index_names(insp, "platform_configs")
        if "ix_platform_configs_id" not in idx:
            op.create_index("ix_platform_configs_id", "platform_configs", ["id"])
        if "ix_platform_configs_config_key" not in idx:
            op.create_index("ix_platform_configs_config_key", "platform_configs", ["config_key"])


def downgrade() -> None:
    insp = _inspector()
    if _table_exists(insp, "platform_configs"):
        idx = _index_names(insp, "platform_configs")
        if "ix_platform_configs_config_key" in idx:
            op.drop_index("ix_platform_configs_config_key", "platform_configs")
        if "ix_platform_configs_id" in idx:
            op.drop_index("ix_platform_configs_id", "platform_configs")
        op.drop_table("platform_configs")
