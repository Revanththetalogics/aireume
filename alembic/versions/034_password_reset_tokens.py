"""Add password reset tokens table"""

from alembic import op
import sqlalchemy as sa

revision = "034_password_reset_tokens"
down_revision = "033_unique_constraints"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Idempotent: skip if table already exists
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'password_reset_tokens'"
    )).fetchone()
    if not result:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            # unique=True already creates a unique index; index=True is intentionally omitted to avoid duplicate index
            sa.Column("token", sa.String(255), unique=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    op.drop_table("password_reset_tokens")
