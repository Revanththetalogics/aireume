"""One-time legacy JD→requisition migration flag on tenant settings.

Prevents migrate_legacy_data from resurrecting deleted requisitions from
leftover RoleTemplate rows on every list/dashboard request.
"""

from alembic import op
import sqlalchemy as sa

revision = "068_legacy_jd_migrated_flag"
down_revision = "067_icp_hiring_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "tenant_requisition_settings" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tenant_requisition_settings")}
    if "legacy_jd_migrated" not in cols:
        op.add_column(
            "tenant_requisition_settings",
            sa.Column(
                "legacy_jd_migrated",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # Existing tenants have already had auto-migrate on list/dashboard. Mark them
    # done so leftover RoleTemplates cannot resurrect deleted requisitions after
    # this deploy. New tenants still start with false and migrate once.
    op.execute("UPDATE tenant_requisition_settings SET legacy_jd_migrated = TRUE")
    op.execute(
        """
        INSERT INTO tenant_requisition_settings (tenant_id, legacy_jd_migrated)
        SELECT t.id, TRUE
        FROM tenants t
        WHERE NOT EXISTS (
            SELECT 1 FROM tenant_requisition_settings s WHERE s.tenant_id = t.id
        )
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "tenant_requisition_settings" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tenant_requisition_settings")}
    if "legacy_jd_migrated" in cols:
        op.drop_column("tenant_requisition_settings", "legacy_jd_migrated")
