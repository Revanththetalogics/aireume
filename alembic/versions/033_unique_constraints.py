"""Add unique constraints for candidate and analysis deduplication"""

from alembic import op
import sqlalchemy as sa

revision = "033_unique_constraints"
down_revision = "032_sso_config"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # 1. Unique candidate per tenant by email (partial: only where email IS NOT NULL)
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_candidate_tenant_email'"
    )).fetchone()
    if not result:
        op.execute(
            "CREATE UNIQUE INDEX uq_candidate_tenant_email "
            "ON candidates (tenant_id, email) "
            "WHERE email IS NOT NULL"
        )

    # 2. Unique candidate per tenant by file hash (partial: only where resume_file_hash IS NOT NULL)
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_candidate_tenant_file_hash'"
    )).fetchone()
    if not result:
        op.execute(
            "CREATE UNIQUE INDEX uq_candidate_tenant_file_hash "
            "ON candidates (tenant_id, resume_file_hash) "
            "WHERE resume_file_hash IS NOT NULL"
        )

    # 3. Unique analysis per candidate per role template per tenant
    #    (partial: only where both candidate_id and role_template_id are set)
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_screening_tenant_candidate_role'"
    )).fetchone()
    if not result:
        op.execute(
            "CREATE UNIQUE INDEX uq_screening_tenant_candidate_role "
            "ON screening_results (tenant_id, candidate_id, role_template_id) "
            "WHERE candidate_id IS NOT NULL AND role_template_id IS NOT NULL"
        )


def downgrade():
    op.execute("DROP INDEX IF EXISTS uq_screening_tenant_candidate_role")
    op.execute("DROP INDEX IF EXISTS uq_candidate_tenant_file_hash")
    op.execute("DROP INDEX IF EXISTS uq_candidate_tenant_email")
