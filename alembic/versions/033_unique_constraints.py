"""Add unique constraints for candidate and analysis deduplication"""

from alembic import op
import sqlalchemy as sa

revision = "033_unique_constraints"
down_revision = "032_sso_config"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # --- Step 1: Deduplicate candidates by email before creating unique index ---
    # Keep the row with the highest ID (most recent) for each (tenant_id, email) group
    conn.execute(sa.text("""
        DELETE FROM candidates
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM candidates
            WHERE email IS NOT NULL
            GROUP BY tenant_id, email
        )
        AND email IS NOT NULL
    """))

    # --- Step 2: Deduplicate candidates by file hash before creating unique index ---
    conn.execute(sa.text("""
        DELETE FROM candidates
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM candidates
            WHERE resume_file_hash IS NOT NULL
            GROUP BY tenant_id, resume_file_hash
        )
        AND resume_file_hash IS NOT NULL
    """))

    # --- Step 3: Deduplicate screening_results before creating unique index ---
    # Keep the row with the highest ID (most recent) for each (tenant_id, candidate_id, role_template_id) group
    conn.execute(sa.text("""
        DELETE FROM screening_results
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM screening_results
            WHERE candidate_id IS NOT NULL AND role_template_id IS NOT NULL
            GROUP BY tenant_id, candidate_id, role_template_id
        )
        AND candidate_id IS NOT NULL
        AND role_template_id IS NOT NULL
    """))

    # --- Step 4: Create unique indexes (idempotent — skip if already exist) ---

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
