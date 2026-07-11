"""Requisitions system — intake, calibration, HM portal, replaces projects.

Revision ID: 056_requisitions_system
Revises: 055_enterprise_rbac_phase2
Create Date: 2026-07-11
"""
from alembic import op
import sqlalchemy as sa

revision = "056_requisitions_system"
down_revision = "055_enterprise_rbac_phase2"
branch_labels = None
depends_on = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _table_exists(name: str) -> bool:
    bind = op.get_bind()
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    if not _table_exists("requisitions"):
        op.create_table(
            "requisitions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("jd_text", sa.Text(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("client_name", sa.String(200), nullable=True),
            sa.Column("headcount", sa.Integer(), nullable=True),
            sa.Column("location", sa.String(200), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("intake_status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("intake_json", sa.Text(), nullable=True),
            sa.Column("search_brief_json", sa.Text(), nullable=True),
            sa.Column("calibrated_criteria_json", sa.Text(), nullable=True),
            sa.Column("current_criteria_version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("scoring_weights", sa.Text(), nullable=True),
            sa.Column("tags", sa.String(500), nullable=True),
            sa.Column("required_skills_override", sa.Text(), nullable=True),
            sa.Column("nice_to_have_skills_override", sa.Text(), nullable=True),
            sa.Column("must_ask_questions_json", sa.Text(), nullable=True),
            sa.Column("primary_hiring_manager_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("legacy_role_template_id", sa.Integer(), sa.ForeignKey("role_templates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("legacy_project_id", sa.Integer(), nullable=True),
            sa.Column("external_ats_id", sa.String(100), nullable=True),
            sa.Column("ats_provider", sa.String(30), nullable=True),
            sa.Column("hm_approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("hm_approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("calibrated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_requisitions_tenant_id", "requisitions", ["tenant_id"])
        op.create_index("ix_requisitions_tenant_status", "requisitions", ["tenant_id", "status"])
        op.create_index("ix_requisitions_primary_hm", "requisitions", ["primary_hiring_manager_id"])

    if not _table_exists("requisition_criteria_versions"):
        op.create_table(
            "requisition_criteria_versions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("criteria_json", sa.Text(), nullable=False),
            sa.Column("source", sa.String(30), nullable=False, server_default="calibration"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("requisition_id", "version", name="uq_req_criteria_version"),
        )
        op.create_index("ix_req_criteria_requisition_id", "requisition_criteria_versions", ["requisition_id"])

    if not _table_exists("requisition_hiring_managers"):
        op.create_table(
            "requisition_hiring_managers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("requisition_id", "user_id", name="uq_req_hm_user"),
        )

    if not _table_exists("requisition_candidates"):
        op.create_table(
            "requisition_candidates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("screening_result_id", sa.Integer(), sa.ForeignKey("screening_results.id", ondelete="SET NULL"), nullable=True),
            sa.Column("pipeline_status", sa.String(50), nullable=False, server_default="pending"),
            sa.Column("submission_status", sa.String(30), nullable=False, server_default="none"),
            sa.Column("hm_outcome", sa.String(30), nullable=True),
            sa.Column("outcome_reason_code", sa.String(50), nullable=True),
            sa.Column("outcome_notes", sa.Text(), nullable=True),
            sa.Column("submission_json", sa.Text(), nullable=True),
            sa.Column("parse_confidence_json", sa.Text(), nullable=True),
            sa.Column("added_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("outcome_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("requisition_id", "candidate_id", name="uq_requisition_candidate"),
        )
        op.create_index("ix_req_candidates_requisition_status", "requisition_candidates", ["requisition_id", "pipeline_status"])

    if not _table_exists("tenant_requisition_settings"):
        op.create_table(
            "tenant_requisition_settings",
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("intake_gate_mode", sa.String(20), nullable=False, server_default="warn"),
            sa.Column("hm_pipeline_permission", sa.String(30), nullable=False, server_default="view_only"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    cols = _existing_columns("screening_results")
    if "requisition_id" not in cols:
        op.add_column(
            "screening_results",
            sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("requisitions.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("ix_screening_results_requisition_id", "screening_results", ["requisition_id"])

    if _table_exists("handoff_share_links"):
        cols = _existing_columns("handoff_share_links")
        if "requisition_id" not in cols:
            op.add_column(
                "handoff_share_links",
                sa.Column("requisition_id", sa.Integer(), sa.ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=True),
            )
        op.alter_column("handoff_share_links", "role_template_id", nullable=True)


def downgrade() -> None:
    if _table_exists("handoff_share_links") and "requisition_id" in _existing_columns("handoff_share_links"):
        op.drop_column("handoff_share_links", "requisition_id")
    if _table_exists("screening_results") and "requisition_id" in _existing_columns("screening_results"):
        op.drop_index("ix_screening_results_requisition_id", table_name="screening_results")
        op.drop_column("screening_results", "requisition_id")
    for table in (
        "tenant_requisition_settings",
        "requisition_candidates",
        "requisition_hiring_managers",
        "requisition_criteria_versions",
        "requisitions",
    ):
        if _table_exists(table):
            op.drop_table(table)
