"""Audit fixes: tenant_id non-nullable, datetime standardization, indexes"""

from alembic import op
import sqlalchemy as sa


revision = "024_audit_fixes"
down_revision = "023_skill_template_persistence"
branch_labels = None
depends_on = None


def upgrade():
    # First update any NULL tenant_ids to a default (1)
    op.execute("UPDATE screening_results SET tenant_id = 1 WHERE tenant_id IS NULL")

    # Make tenant_id non-nullable
    with op.batch_alter_table("screening_results") as batch_op:
        batch_op.alter_column("tenant_id", nullable=False, existing_type=sa.Integer())

    # Add composite index for common queries
    try:
        op.create_index(
            "ix_screening_results_tenant_created",
            "screening_results",
            ["tenant_id", "timestamp"],
        )
    except Exception:
        pass  # Index may already exist


def downgrade():
    try:
        op.drop_index("ix_screening_results_tenant_created", table_name="screening_results")
    except Exception:
        pass

    with op.batch_alter_table("screening_results") as batch_op:
        batch_op.alter_column("tenant_id", nullable=True, existing_type=sa.Integer())
