"""Add lease-based locking and content_hash deduplication to analysis_jobs.

Revision ID: 036_queue_lease_locking
Revises: 035_recruiter_debrief
Create Date: 2026-05-28

Adds:
- leased_until: DateTime column for lease-based locking (prevents duplicate workers)
- content_hash: String(64) for fast tenant+candidate deduplication window check
"""

from alembic import op
import sqlalchemy as sa


revision = "036_queue_lease_locking"
down_revision = "036_fix_audit_tenant_id"
branch_labels = None
depends_on = None


def upgrade():
    # Add leased_until for lease-based job locking
    op.add_column(
        "analysis_jobs",
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True),
    )

    # Add content_hash for fast deduplication window checks
    op.add_column(
        "analysis_jobs",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )

    # Indexes for efficient stale-job recovery and dedup queries
    op.create_index(
        "ix_analysis_jobs_leased_until",
        "analysis_jobs",
        ["leased_until"],
    )
    op.create_index(
        "ix_analysis_jobs_content_hash",
        "analysis_jobs",
        ["content_hash"],
    )


def downgrade():
    op.drop_index("ix_analysis_jobs_content_hash", table_name="analysis_jobs")
    op.drop_index("ix_analysis_jobs_leased_until", table_name="analysis_jobs")
    op.drop_column("analysis_jobs", "content_hash")
    op.drop_column("analysis_jobs", "leased_until")
