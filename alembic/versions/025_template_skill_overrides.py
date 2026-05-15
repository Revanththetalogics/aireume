"""Add skill override columns to role_templates"""

from alembic import op
import sqlalchemy as sa


revision = "025_template_skill_overrides"
down_revision = "024_audit_fixes"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("role_templates") as batch_op:
        batch_op.add_column(sa.Column("required_skills_override", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("nice_to_have_skills_override", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("role_templates") as batch_op:
        batch_op.drop_column("nice_to_have_skills_override")
        batch_op.drop_column("required_skills_override")
