"""Fix FieldAuditLog tenant_id type from String to Integer"""

revision = "036_fix_audit_tenant_id"
down_revision = "035_recruiter_debrief"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    conn = op.get_bind()

    # Check current column type before altering
    result = conn.execute(sa.text(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'field_audit_logs' AND column_name = 'tenant_id'"
    )).fetchone()

    if result and result[0] != "integer":
        op.execute(
            "ALTER TABLE field_audit_logs ALTER COLUMN tenant_id TYPE INTEGER USING tenant_id::INTEGER"
        )

    # Add foreign key if it doesn't already exist
    fk_result = conn.execute(sa.text(
        "SELECT constraint_name FROM information_schema.table_constraints "
        "WHERE table_schema = 'public' AND table_name = 'field_audit_logs' "
        "AND constraint_name = 'fk_field_audit_logs_tenant_id'"
    )).fetchone()

    if not fk_result:
        op.create_foreign_key(
            "fk_field_audit_logs_tenant_id",
            "field_audit_logs",
            "tenants",
            ["tenant_id"],
            ["id"],
        )


def downgrade():
    op.drop_constraint("fk_field_audit_logs_tenant_id", "field_audit_logs", type_="foreignkey")
    op.alter_column("field_audit_logs", "tenant_id", type_=sa.String(100))
