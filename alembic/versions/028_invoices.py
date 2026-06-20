"""Add invoices table for payment receipt tracking"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "028_invoices"
down_revision = "027_billing_events"
branch_labels = None
depends_on = None


def upgrade():
    insp = inspect(op.get_bind())
    if 'invoices' in {t for t in insp.get_table_names()}:
        return
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('tenant_id', sa.Integer, sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('invoice_number', sa.String(50), unique=True, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='paid'),
        sa.Column('amount', sa.Integer, nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='usd'),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('line_items', sa.JSON, nullable=True),
        sa.Column('payment_provider', sa.String(20), nullable=True),
        sa.Column('provider_invoice_id', sa.String(255), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_invoices_tenant_issued', 'invoices', ['tenant_id', 'issued_at'])


def downgrade():
    op.drop_index('ix_invoices_tenant_issued', table_name='invoices')
    op.drop_table('invoices')
