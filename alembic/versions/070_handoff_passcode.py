"""Optional passcode hash on public handoff share links.

Revision ID: 070_handoff_passcode
Revises: 069_mfa_audit_hash
"""
from alembic import op
import sqlalchemy as sa

revision = "070_handoff_passcode"
down_revision = "069_mfa_audit_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "handoff_share_links" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("handoff_share_links")}
    if "passcode_hash" not in cols:
        op.add_column(
            "handoff_share_links",
            sa.Column("passcode_hash", sa.String(64), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "handoff_share_links" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("handoff_share_links")}
    if "passcode_hash" in cols:
        op.drop_column("handoff_share_links", "passcode_hash")
