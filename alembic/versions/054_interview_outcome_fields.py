"""Add interview outcome fields to screening_results.

Revision ID: 054_interview_outcome
Revises: 053_background_enrichment_status
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = "054_interview_outcome"
down_revision = "053_background_enrichment_status"
branch_labels = None
depends_on = None

_NEW_COLUMNS = (
    ("call_fit_score", sa.Integer()),
    ("call_source", sa.String(20)),
    ("consolidated_recommendation", sa.String(50)),
    ("consolidated_reasoning", sa.Text()),
    ("call_completed_at", sa.DateTime(timezone=True)),
)


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    existing = _existing_columns("screening_results")
    for name, col_type in _NEW_COLUMNS:
        if name not in existing:
            op.add_column("screening_results", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    existing = _existing_columns("screening_results")
    for name, _ in reversed(_NEW_COLUMNS):
        if name in existing:
            op.drop_column("screening_results", name)
