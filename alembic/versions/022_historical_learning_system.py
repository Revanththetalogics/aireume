"""Historical learning system: hiring outcomes, team skill profiles, skill trends, outcome patterns

Revision ID: 022
Revises: 021
Create Date: 2026-05-14

Changes:
  - Create hiring_outcomes table
  - Create team_skill_profiles table
  - Create skill_trend_snapshots table
  - Create outcome_skill_patterns table
  - Add composite indexes for analytics queries

Idempotent: safe when objects already exist.
"""
from alembic import op
import sqlalchemy as sa

revision = "022"
down_revision = "021"
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

    # ── 1. hiring_outcomes ─────────────────────────────────────────────────────
    if not _table_exists(insp, "hiring_outcomes"):
        op.create_table(
            "hiring_outcomes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("screening_result_id", sa.Integer(), sa.ForeignKey("screening_results.id"), unique=True, nullable=False),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False, index=True),
            sa.Column("role_template_id", sa.Integer(), sa.ForeignKey("role_templates.id"), nullable=True, index=True),
            sa.Column("decision", sa.String(20), nullable=False),
            sa.Column("decision_stage", sa.String(50), nullable=True),
            sa.Column("decision_date", sa.DateTime(), nullable=True),
            sa.Column("decision_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("feedback_rating", sa.Integer(), nullable=True),
            sa.Column("feedback_notes", sa.Text(), nullable=True),
            sa.Column("source", sa.String(20), server_default="manual"),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), onupdate=sa.func.now()),
        )

    # Composite indexes for hiring_outcomes
    if _table_exists(insp, "hiring_outcomes"):
        idx = _index_names(insp, "hiring_outcomes")
        if "ix_hiring_outcomes_tenant_template" not in idx:
            op.create_index("ix_hiring_outcomes_tenant_template", "hiring_outcomes", ["tenant_id", "role_template_id"])
        if "ix_hiring_outcomes_tenant_decision_date" not in idx:
            op.create_index("ix_hiring_outcomes_tenant_decision_date", "hiring_outcomes", ["tenant_id", "decision", "created_at"])

    # ── 2. team_skill_profiles ─────────────────────────────────────────────────
    if not _table_exists(insp, "team_skill_profiles"):
        op.create_table(
            "team_skill_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("team_name", sa.String(200), nullable=False),
            sa.Column("skills_json", sa.Text(), nullable=True),
            sa.Column("job_functions", sa.Text(), nullable=True),
            sa.Column("member_count", sa.Integer(), nullable=True),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), onupdate=sa.func.now()),
        )

    # ── 3. skill_trend_snapshots ───────────────────────────────────────────────
    if not _table_exists(insp, "skill_trend_snapshots"):
        op.create_table(
            "skill_trend_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("role_category", sa.String(50), nullable=True),
            sa.Column("skill_name", sa.String(200), nullable=False),
            sa.Column("period_date", sa.Date(), nullable=False),
            sa.Column("jd_mention_count", sa.Integer(), default=0),
            sa.Column("resume_present_count", sa.Integer(), default=0),
            sa.Column("hired_with_skill", sa.Integer(), default=0),
            sa.Column("total_hired", sa.Integer(), default=0),
            sa.Column("trend_direction", sa.String(10), nullable=True),
            sa.Column("growth_pct", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # Composite indexes for skill_trend_snapshots
    if _table_exists(insp, "skill_trend_snapshots"):
        idx = _index_names(insp, "skill_trend_snapshots")
        if "ix_skill_trends_tenant_category_date" not in idx:
            op.create_index("ix_skill_trends_tenant_category_date", "skill_trend_snapshots", ["tenant_id", "role_category", "period_date"])
        if "ix_skill_trends_tenant_skill_date" not in idx:
            op.create_index("ix_skill_trends_tenant_skill_date", "skill_trend_snapshots", ["tenant_id", "skill_name", "period_date"])

    # ── 4. outcome_skill_patterns ──────────────────────────────────────────────
    if not _table_exists(insp, "outcome_skill_patterns"):
        op.create_table(
            "outcome_skill_patterns",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
            sa.Column("role_template_id", sa.Integer(), sa.ForeignKey("role_templates.id"), nullable=True, index=True),
            sa.Column("role_category", sa.String(50), nullable=True),
            sa.Column("skill_name", sa.String(200), nullable=False),
            sa.Column("correlation_score", sa.Float(), nullable=True),
            sa.Column("present_in_hired_pct", sa.Float(), nullable=True),
            sa.Column("present_in_rejected_pct", sa.Float(), nullable=True),
            sa.Column("sample_size", sa.Integer(), nullable=True),
            sa.Column("last_computed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    # Composite index for outcome_skill_patterns
    if _table_exists(insp, "outcome_skill_patterns"):
        idx = _index_names(insp, "outcome_skill_patterns")
        if "ix_outcome_patterns_tenant_template" not in idx:
            op.create_index("ix_outcome_patterns_tenant_template", "outcome_skill_patterns", ["tenant_id", "role_template_id"])


def downgrade() -> None:
    # Drop in reverse order of creation

    # outcome_skill_patterns
    insp = _inspector()
    if _table_exists(insp, "outcome_skill_patterns"):
        idx = _index_names(insp, "outcome_skill_patterns")
        if "ix_outcome_patterns_tenant_template" in idx:
            op.drop_index("ix_outcome_patterns_tenant_template", "outcome_skill_patterns")
        op.drop_table("outcome_skill_patterns")

    # skill_trend_snapshots
    if _table_exists(insp, "skill_trend_snapshots"):
        idx = _index_names(insp, "skill_trend_snapshots")
        if "ix_skill_trends_tenant_skill_date" in idx:
            op.drop_index("ix_skill_trends_tenant_skill_date", "skill_trend_snapshots")
        if "ix_skill_trends_tenant_category_date" in idx:
            op.drop_index("ix_skill_trends_tenant_category_date", "skill_trend_snapshots")
        op.drop_table("skill_trend_snapshots")

    # team_skill_profiles
    if _table_exists(insp, "team_skill_profiles"):
        op.drop_table("team_skill_profiles")

    # hiring_outcomes
    if _table_exists(insp, "hiring_outcomes"):
        idx = _index_names(insp, "hiring_outcomes")
        if "ix_hiring_outcomes_tenant_decision_date" in idx:
            op.drop_index("ix_hiring_outcomes_tenant_decision_date", "hiring_outcomes")
        if "ix_hiring_outcomes_tenant_template" in idx:
            op.drop_index("ix_hiring_outcomes_tenant_template", "hiring_outcomes")
        op.drop_table("hiring_outcomes")
