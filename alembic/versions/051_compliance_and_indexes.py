"""Compliance tables (consent, AI decision log, breach, retention, idempotency)
+ performance indexes + score range constraint.
"""

revision = "051_compliance_and_indexes"
down_revision = "050_screening_cache"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def _has_table(insp, name):
    return name in set(insp.get_table_names())


def _has_index(insp, table, index_name):
    try:
        return index_name in {ix["name"] for ix in insp.get_indexes(table)}
    except Exception:
        return False


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    is_pg = bind.dialect.name == "postgresql"

    if not _has_table(insp, "candidate_consents"):
        op.create_table(
            "candidate_consents",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("consent_type", sa.String(50), nullable=False),
            sa.Column("consented", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("consent_version", sa.String(20), nullable=False, server_default="1.0"),
            sa.Column("consent_ip", sa.String(64), nullable=True),
            sa.Column("withdrawal_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("candidate_id", "consent_type", name="uq_candidate_consent_type"),
        )
        op.create_index("ix_candidate_consent_tenant", "candidate_consents", ["tenant_id", "candidate_id"])

    if not _has_table(insp, "ai_decision_logs"):
        op.create_table(
            "ai_decision_logs",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
            sa.Column("screening_result_id", sa.Integer(), sa.ForeignKey("screening_results.id", ondelete="SET NULL"), nullable=True),
            sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True),
            sa.Column("model_name", sa.String(100), nullable=True),
            sa.Column("model_version", sa.String(50), nullable=True),
            sa.Column("prompt_template_version", sa.String(20), nullable=True),
            sa.Column("prompt_hash", sa.String(64), nullable=True),
            sa.Column("raw_llm_output", sa.Text(), nullable=True),
            sa.Column("guardrails_triggered", sa.JSON(), nullable=True),
            sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("deterministic_score", sa.Float(), nullable=True),
            sa.Column("llm_score", sa.Float(), nullable=True),
            sa.Column("final_score", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_ai_decision_tenant_created", "ai_decision_logs", ["tenant_id", "created_at"])

    if not _has_table(insp, "idempotency_keys"):
        op.create_table(
            "idempotency_keys",
            sa.Column("key", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.Integer(), nullable=False),
            sa.Column("endpoint", sa.String(200), nullable=False),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_idempotency_tenant", "idempotency_keys", ["tenant_id"])
        op.create_index("ix_idempotency_expires", "idempotency_keys", ["expires_at"])

    if not _has_table(insp, "breach_logs"):
        op.create_table(
            "breach_logs",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
            sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("breach_type", sa.String(100), nullable=False),
            sa.Column("affected_records_count", sa.Integer(), nullable=True),
            sa.Column("affected_data_categories", sa.JSON(), nullable=True),
            sa.Column("reported_to_authority_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notified_subjects_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("remediation_steps", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _has_table(insp, "data_retention_policies"):
        op.create_table(
            "data_retention_policies",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("candidate_retention_days", sa.Integer(), nullable=False, server_default="730"),
            sa.Column("screening_result_retention_days", sa.Integer(), nullable=False, server_default="1095"),
            sa.Column("voice_transcript_retention_days", sa.Integer(), nullable=False, server_default="365"),
            sa.Column("ai_decision_log_retention_days", sa.Integer(), nullable=False, server_default="2555"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # ── Billing webhook idempotency: event_id on billing_events ───────────────
    if _has_table(insp, "billing_events"):
        becols = {c["name"] for c in insp.get_columns("billing_events")}
        if "event_id" not in becols:
            op.add_column("billing_events", sa.Column("event_id", sa.String(255), nullable=True))
            op.create_index("ix_billing_events_event_id", "billing_events", ["event_id"])
            op.create_unique_constraint(
                "uq_billing_event_provider_event_id", "billing_events", ["provider", "event_id"]
            )

    # ── Performance indexes on hot query paths ────────────────────────────────
    if _has_table(insp, "candidates"):
        cols = {c["name"] for c in insp.get_columns("candidates")}
        if {"tenant_id", "status"}.issubset(cols) and not _has_index(insp, "candidates", "ix_candidate_tenant_status"):
            op.create_index("ix_candidate_tenant_status", "candidates", ["tenant_id", "status"])
        # GIN index on skills JSONB (PostgreSQL only)
        if is_pg and "skills" in cols and not _has_index(insp, "candidates", "ix_candidate_skills_gin"):
            op.execute("CREATE INDEX IF NOT EXISTS ix_candidate_skills_gin ON candidates USING gin (skills)")

    if _has_table(insp, "screening_results"):
        srcols = {c["name"] for c in insp.get_columns("screening_results")}
        if {"tenant_id", "created_at"}.issubset(srcols) and not _has_index(insp, "screening_results", "ix_screening_result_tenant_created"):
            op.create_index("ix_screening_result_tenant_created", "screening_results", ["tenant_id", "created_at"])

        # Score range check constraint (PostgreSQL). Named so it is idempotent.
        if is_pg:
            for col in ("fit_score", "score"):
                if col in srcols:
                    op.execute(
                        f"ALTER TABLE screening_results DROP CONSTRAINT IF EXISTS chk_{col}_range"
                    )
                    op.execute(
                        f"ALTER TABLE screening_results ADD CONSTRAINT chk_{col}_range "
                        f"CHECK ({col} IS NULL OR ({col} >= 0 AND {col} <= 100))"
                    )
                    break


def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    if is_pg:
        op.execute("ALTER TABLE screening_results DROP CONSTRAINT IF EXISTS chk_fit_score_range")
        op.execute("ALTER TABLE screening_results DROP CONSTRAINT IF EXISTS chk_score_range")
        op.execute("DROP INDEX IF EXISTS ix_candidate_skills_gin")
    for ix, tbl in [
        ("ix_screening_result_tenant_created", "screening_results"),
        ("ix_candidate_tenant_status", "candidates"),
    ]:
        try:
            op.drop_index(ix, table_name=tbl)
        except Exception:
            pass
    try:
        op.drop_constraint("uq_billing_event_provider_event_id", "billing_events", type_="unique")
        op.drop_index("ix_billing_events_event_id", table_name="billing_events")
        op.drop_column("billing_events", "event_id")
    except Exception:
        pass
    for tbl in ["data_retention_policies", "breach_logs", "idempotency_keys", "ai_decision_logs", "candidate_consents"]:
        try:
            op.drop_table(tbl)
        except Exception:
            pass
