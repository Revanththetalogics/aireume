"""Scope email uniqueness to tenant"""

revision = "039_tenant_scoped_email"
down_revision = "038_tenant_soft_delete"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()

    # Find and drop any existing unique constraint on the email column alone
    result = conn.execute(sa.text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = 'users'::regclass AND contype = 'u' "
        "AND pg_get_constraintdef(oid) LIKE '%(email)%' "
        "AND pg_get_constraintdef(oid) NOT LIKE '%tenant_id%'"
    )).fetchone()

    if result:
        op.execute(f"ALTER TABLE users DROP CONSTRAINT IF EXISTS {result[0]}")

    # Drop any standalone unique index on email
    op.execute("DROP INDEX IF EXISTS ix_users_email")

    # Create composite unique constraint if it doesn't already exist
    composite_result = conn.execute(sa.text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid = 'users'::regclass AND contype = 'u' "
        "AND conname = 'uq_users_tenant_email'"
    )).fetchone()

    if not composite_result:
        op.create_unique_constraint(
            "uq_users_tenant_email",
            "users",
            ["tenant_id", "email"],
        )


def downgrade():
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.create_unique_constraint("uq_users_email", "users", ["email"])
