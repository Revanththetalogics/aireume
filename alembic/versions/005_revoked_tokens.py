"""Add revoked_tokens table for token revocation support

Revision ID: 005
Revises: 004
Create Date: 2026-04-08

Changes:
  - new table: revoked_tokens
    - id: primary key
    - jti: JWT ID (UUID) - unique, indexed
    - revoked_at: timestamp when token was revoked
    - expires_at: when the token would have expired naturally

This allows logout to revoke refresh tokens, preventing their reuse.
Expired tokens are cleaned up periodically by a background task.

Idempotent: safe when table already exists.
"""
from alembic import op
import sqlalchemy as sa


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(insp, name: str) -> bool:
    return name in insp.get_table_names()


def _index_names(insp, table: str) -> set:
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade() -> None:
    insp = _inspector()

    if not _table_exists(insp, "revoked_tokens"):
        op.create_table(
            "revoked_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("jti", sa.String(64), nullable=False, unique=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_revoked_tokens_id", "revoked_tokens", ["id"])
        op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"], unique=True)
    else:
        insp = _inspector()
        idx = _index_names(insp, "revoked_tokens")
        if "ix_revoked_tokens_id" not in idx:
            op.create_index("ix_revoked_tokens_id", "revoked_tokens", ["id"])
        if "ix_revoked_tokens_jti" not in idx:
            op.create_index("ix_revoked_tokens_jti", "revoked_tokens", ["jti"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_jti", "revoked_tokens")
    op.drop_index("ix_revoked_tokens_id", "revoked_tokens")
    op.drop_table("revoked_tokens")
