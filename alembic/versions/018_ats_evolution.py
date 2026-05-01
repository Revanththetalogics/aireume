"""ATS evolution: tenant email configs, screening status tracking

Revision ID: 018
Revises: 017
Create Date: 2026-05-01

Changes:
  - Create tenant_email_configs table
  - Add status_updated_at to screening_results

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _column_names(insp, table: str) -> set:
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    insp = _inspector()

    # ── Create tenant_email_configs table ──────────────────────────────────────
    if not _table_exists(insp, "tenant_email_configs"):
        op.create_table(
            "tenant_email_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), unique=True, nullable=False),
            sa.Column("smtp_host", sa.String(255), nullable=False),
            sa.Column("smtp_port", sa.Integer(), server_default="587"),
            sa.Column("smtp_user", sa.String(255), nullable=True),
            sa.Column("smtp_password", sa.String(500), nullable=True),
            sa.Column("smtp_from", sa.String(255), nullable=False),
            sa.Column("from_name", sa.String(255), nullable=True),
            sa.Column("reply_to", sa.String(255), nullable=True),
            sa.Column("encryption_type", sa.String(10), server_default="tls"),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("configured_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_test_success", sa.Boolean(), nullable=True),
        )

    # ── Add status_updated_at to screening_results ─────────────────────────────
    insp = _inspector()
    cols = _column_names(insp, "screening_results")
    if "status_updated_at" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("status_updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    # Remove status_updated_at from screening_results
    op.drop_column("screening_results", "status_updated_at")

    # Drop tenant_email_configs
    op.drop_table("tenant_email_configs")
