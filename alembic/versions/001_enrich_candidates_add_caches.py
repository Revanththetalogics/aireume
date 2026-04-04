"""enrich candidates profile, add jd_cache and skills tables

Revision ID: 001
Revises:
Create Date: 2026-04-04

Changes:
  - candidates: add 11 profile columns (resume_file_hash, raw_resume_text,
    parsed_skills, parsed_education, parsed_work_exp, gap_analysis_json,
    current_role, current_company, total_years_exp, profile_quality,
    profile_updated_at)
  - new table: jd_cache
  - new table: skills
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── candidates: add profile columns ───────────────────────────────────────
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.add_column(sa.Column("resume_file_hash",   sa.String(64),              nullable=True))
        batch_op.add_column(sa.Column("raw_resume_text",    sa.Text(),                  nullable=True))
        batch_op.add_column(sa.Column("parsed_skills",      sa.Text(),                  nullable=True))
        batch_op.add_column(sa.Column("parsed_education",   sa.Text(),                  nullable=True))
        batch_op.add_column(sa.Column("parsed_work_exp",    sa.Text(),                  nullable=True))
        batch_op.add_column(sa.Column("gap_analysis_json",  sa.Text(),                  nullable=True))
        batch_op.add_column(sa.Column("current_role",       sa.String(255),             nullable=True))
        batch_op.add_column(sa.Column("current_company",    sa.String(255),             nullable=True))
        batch_op.add_column(sa.Column("total_years_exp",    sa.Float(),                 nullable=True))
        batch_op.add_column(sa.Column("profile_quality",    sa.String(20),              nullable=True))
        batch_op.add_column(sa.Column("profile_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_candidates_resume_file_hash", ["resume_file_hash"])

    # ── jd_cache table ─────────────────────────────────────────────────────────
    op.create_table(
        "jd_cache",
        sa.Column("hash",        sa.String(64),              primary_key=True),
        sa.Column("result_json", sa.Text(),                  nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── skills table ───────────────────────────────────────────────────────────
    op.create_table(
        "skills",
        sa.Column("id",         sa.Integer(),               primary_key=True, autoincrement=True),
        sa.Column("name",       sa.String(200),             nullable=False, unique=True),
        sa.Column("aliases",    sa.Text(),                  nullable=True),
        sa.Column("domain",     sa.String(50),              nullable=True),
        sa.Column("status",     sa.String(20),              nullable=False, server_default="active"),
        sa.Column("source",     sa.String(20),              nullable=False, server_default="seed"),
        sa.Column("frequency",  sa.Integer(),               nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_skills_id",   "skills", ["id"])
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)


def downgrade() -> None:
    op.drop_table("skills")
    op.drop_table("jd_cache")
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.drop_index("ix_candidates_resume_file_hash")
        batch_op.drop_column("profile_updated_at")
        batch_op.drop_column("profile_quality")
        batch_op.drop_column("total_years_exp")
        batch_op.drop_column("current_company")
        batch_op.drop_column("current_role")
        batch_op.drop_column("gap_analysis_json")
        batch_op.drop_column("parsed_work_exp")
        batch_op.drop_column("parsed_education")
        batch_op.drop_column("parsed_skills")
        batch_op.drop_column("raw_resume_text")
        batch_op.drop_column("resume_file_hash")
