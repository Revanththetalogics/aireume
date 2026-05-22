"""Add sso_configs table for SAML/OIDC SSO integration"""

from alembic import op
import sqlalchemy as sa


revision = "032_sso_config"
down_revision = "031_onboarding_flag"
branch_labels = None
depends_on = None


def upgrade():
    insp = sa.inspect(op.get_bind())
    if "sso_configs" not in insp.get_table_names():
        op.create_table(
            'sso_configs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id', ondelete='CASCADE'), unique=True, nullable=False, index=True),
            sa.Column('provider_type', sa.String(20), nullable=False, server_default='saml2'),
            sa.Column('idp_entity_id', sa.String(500), nullable=False),
            sa.Column('idp_sso_url', sa.String(500), nullable=False),
            sa.Column('idp_slo_url', sa.String(500), nullable=True),
            sa.Column('idp_certificate', sa.Text(), nullable=False),
            sa.Column('sp_entity_id', sa.String(500), nullable=True),
            sa.Column('sp_acs_url', sa.String(500), nullable=True),
            sa.Column('enforce_sso', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('auto_provision', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('default_role', sa.String(50), nullable=False, server_default='viewer'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        )


def downgrade():
    op.drop_table('sso_configs')
