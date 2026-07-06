"""Create dead_letter_jobs table

Revision ID: 052_dead_letter_jobs
Revises: 051_compliance_and_indexes
Create Date: 2026-07-07

The DeadLetterJob model (app.backend.models.db_models) was never backed by a
migration — it only ever existed via the legacy Base.metadata.create_all() path.
Production applies the schema purely through `alembic upgrade heads`, so on any
database built from migrations the table is missing, breaking the dead-letter
queue. It has a foreign key to `analysis_jobs` (created by revision 008), so it
is created here, after that dependency exists.

Idempotent: skips creation if the table already exists (e.g. legacy create_all).
"""
from alembic import op
import sqlalchemy as sa

revision = "052_dead_letter_jobs"
down_revision = "051_compliance_and_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "dead_letter_jobs" in insp.get_table_names():
        return

    from app.backend.db.database import Base
    import app.backend.models.db_models  # noqa: F401 — registers all models

    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[Base.metadata.tables["dead_letter_jobs"]],
    )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "dead_letter_jobs" in insp.get_table_names():
        op.drop_table("dead_letter_jobs")
