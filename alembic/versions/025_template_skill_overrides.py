"""Add skill override columns to role_templates"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "025_template_skill_overrides"
down_revision = "024_audit_fixes"
branch_labels = None
depends_on = None


def upgrade():
    insp = inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("role_templates")}
    with op.batch_alter_table("role_templates") as batch_op:
        if "required_skills_override" not in cols:
            batch_op.add_column(sa.Column("required_skills_override", sa.Text(), nullable=True))
        if "nice_to_have_skills_override" not in cols:
            batch_op.add_column(sa.Column("nice_to_have_skills_override", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("role_templates") as batch_op:
        batch_op.drop_column("nice_to_have_skills_override")
        batch_op.drop_column("required_skills_override")
