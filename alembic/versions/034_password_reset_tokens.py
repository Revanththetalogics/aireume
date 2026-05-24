"""Add password reset tokens table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "034_password_reset_tokens"
down_revision = "033_unique_constraints"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    if "password_reset_tokens" not in inspector.get_table_names():
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token", sa.String(255), unique=True, nullable=False, index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    op.drop_table("password_reset_tokens")
