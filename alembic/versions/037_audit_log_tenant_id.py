"""Add tenant_id to audit_logs table"""

revision = "037_audit_log_tenant_id"
down_revision = "036_queue_lease_locking"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()

    # Check if column already exists
    cols = {r[0] for r in conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'audit_logs'"
    )).fetchall()}

    if "tenant_id" not in cols:
        op.add_column("audit_logs", sa.Column("tenant_id", sa.Integer(), nullable=True))

    # Add foreign key if it doesn't already exist
    fk_result = conn.execute(sa.text(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_schema = 'public' AND table_name = 'audit_logs' "
        "AND constraint_name = 'fk_audit_logs_tenant_id'"
    )).fetchone()

    if not fk_result:
        op.create_foreign_key(
            "fk_audit_logs_tenant_id",
            "audit_logs",
            "tenants",
            ["tenant_id"],
            ["id"],
        )

    # Add index if it doesn't already exist
    idx_result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_audit_logs_tenant_id'"
    )).fetchone()

    if not idx_result:
        op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])


def downgrade():
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_tenant_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "tenant_id")
