"""MFA columns and tamper-evident audit hash chain.

Revision ID: 069_mfa_audit_hash
Revises: 068_legacy_jd_migrated_flag
"""
from alembic import op
import sqlalchemy as sa

revision = "069_mfa_audit_hash"
down_revision = "068_legacy_jd_migrated_flag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "mfa_secret" not in cols:
            op.add_column("users", sa.Column("mfa_secret", sa.String(64), nullable=True))
        if "mfa_enabled" not in cols:
            op.add_column(
                "users",
                sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            )

    if "audit_logs" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("audit_logs")}
        if "entry_hash" not in cols:
            op.add_column("audit_logs", sa.Column("entry_hash", sa.String(64), nullable=True))
        if "prev_hash" not in cols:
            op.add_column("audit_logs", sa.Column("prev_hash", sa.String(64), nullable=True))
        if "impersonated_by" not in cols:
            op.add_column("audit_logs", sa.Column("impersonated_by", sa.Integer(), nullable=True))

        dialect = bind.dialect.name
        if dialect == "postgresql":
            op.execute(
                """
                CREATE OR REPLACE FUNCTION aria_deny_audit_mutation()
                RETURNS trigger AS $$
                BEGIN
                  RAISE EXCEPTION 'audit_logs are append-only';
                END;
                $$ LANGUAGE plpgsql;
                """
            )
            op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs")
            op.execute(
                """
                CREATE TRIGGER audit_logs_no_update
                BEFORE UPDATE OR DELETE ON audit_logs
                FOR EACH ROW EXECUTE FUNCTION aria_deny_audit_mutation();
                """
            )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS aria_deny_audit_mutation()")
    insp = sa.inspect(bind)
    if "audit_logs" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("audit_logs")}
        for col in ("impersonated_by", "prev_hash", "entry_hash"):
            if col in cols:
                op.drop_column("audit_logs", col)
    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "mfa_enabled" in cols:
            op.drop_column("users", "mfa_enabled")
        if "mfa_secret" in cols:
            op.drop_column("users", "mfa_secret")
