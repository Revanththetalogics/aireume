"""Add soft delete to tenants"""

revision = "038_tenant_soft_delete"
down_revision = "037_audit_log_tenant_id"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()

    # Check if column already exists
    cols = {r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'tenants'"
    )).fetchall()}

    if "deleted_at" not in cols:
        op.add_column(
            "tenants",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Add index if it doesn't already exist
    idx_result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_tenants_deleted_at'"
    )).fetchone()

    if not idx_result:
        op.create_index("ix_tenants_deleted_at", "tenants", ["deleted_at"])


def downgrade():
    op.drop_index("ix_tenants_deleted_at", table_name="tenants")
    op.drop_column("tenants", "deleted_at")
