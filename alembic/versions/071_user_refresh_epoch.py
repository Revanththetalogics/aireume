"""Add refresh_epoch so reused refresh tokens kill the token family.

Revision ID: 071_user_refresh_epoch
Revises: 070_handoff_passcode
"""
from alembic import op
import sqlalchemy as sa

revision = "071_user_refresh_epoch"
down_revision = "070_handoff_passcode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "refresh_epoch" not in cols:
        op.add_column(
            "users",
            sa.Column("refresh_epoch", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "refresh_epoch" in cols:
        op.drop_column("users", "refresh_epoch")
