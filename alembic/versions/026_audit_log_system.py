"""Field-level audit log system for candidate/report change tracking"""

from alembic import op
import sqlalchemy as sa


revision = "026_audit_log_system"
down_revision = "025_template_skill_overrides"
branch_labels = None
depends_on = None


def upgrade():
    insp = sa.inspect(op.get_bind())
    if "field_audit_logs" not in insp.get_table_names():
        op.create_table(
            'field_audit_logs',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
            sa.Column('entity_type', sa.String(50), nullable=False),  # 'candidate', 'screening_result'
            sa.Column('entity_id', sa.Integer, nullable=False, index=True),
            sa.Column('field_name', sa.String(100), nullable=False),
            sa.Column('old_value', sa.Text, nullable=True),
            sa.Column('new_value', sa.Text, nullable=True),
            sa.Column('changed_by', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
            sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('change_reason', sa.String(500), nullable=True),
        )
    # Ensure index exists
    idx_names = {i["name"] for i in insp.get_indexes("field_audit_logs")}
    if "ix_field_audit_entity" not in idx_names:
        op.create_index('ix_field_audit_entity', 'field_audit_logs', ['entity_type', 'entity_id'])


def downgrade():
    op.drop_index('ix_field_audit_entity', table_name='field_audit_logs')
    op.drop_table('field_audit_logs')
