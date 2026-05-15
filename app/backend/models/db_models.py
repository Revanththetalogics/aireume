from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text, Boolean, LargeBinary,
    ForeignKey, Float, func, BigInteger, UniqueConstraint, Index
)
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from app.backend.db.database import Base


# ─── Multi-tenancy ────────────────────────────────────────────────────────────

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(50), unique=True, nullable=False)   # free / pro / enterprise
    display_name = Column(String(100), nullable=True)                # Human-readable name
    description  = Column(Text, nullable=True)                        # Plan description
    limits       = Column(Text, nullable=False, default="{}")      # JSON: analyses_per_month, batch_size, etc.
    price_monthly = Column(Integer, nullable=False, default=0)       # Monthly price in cents
    price_yearly = Column(Integer, nullable=False, default=0)        # Yearly price in cents
    currency     = Column(String(3), nullable=False, default="USD")  # ISO currency code
    features     = Column(Text, nullable=False, default="[]")      # JSON array of feature strings
    is_active    = Column(Boolean, nullable=False, default=True)     # Whether plan is available
    sort_order   = Column(Integer, nullable=False, default=0)        # Display order
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    tenants = relationship("Tenant", back_populates="plan")
    plan_features = relationship("PlanFeature", back_populates="plan", cascade="all, delete-orphan")


class Tenant(Base):
    __tablename__ = "tenants"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False)
    slug       = Column(String(100), unique=True, nullable=False)
    plan_id    = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Subscription & Usage Tracking ─────────────────────────────────────────
    subscription_status     = Column(String(20), nullable=False, default="active")  # active/trialing/cancelled/past_due
    current_period_start    = Column(DateTime(timezone=True), nullable=True)
    current_period_end      = Column(DateTime(timezone=True), nullable=True)
    analyses_count_this_month = Column(Integer, nullable=False, default=0)
    storage_used_bytes      = Column(BigInteger, nullable=False, default=0)
    usage_reset_at          = Column(DateTime(timezone=True), nullable=True)  # Last monthly reset

    # Stripe integration (for future payment integration)
    stripe_customer_id      = Column(String(255), nullable=True)
    stripe_subscription_id  = Column(String(255), nullable=True)
    subscription_updated_at = Column(DateTime(timezone=True), nullable=True)
    suspended_at    = Column(DateTime(timezone=True), nullable=True)
    suspended_reason = Column(Text, nullable=True)
    metadata_json   = Column(Text, nullable=False, default="{}")
    
    # Tenant-level default scoring weights (JSON string)
    scoring_weights = Column(Text, nullable=True)  # JSON: custom weights for this tenant

    plan         = relationship("SubscriptionPlan", back_populates="tenants")
    users        = relationship("User", back_populates="tenant")
    candidates   = relationship("Candidate", back_populates="tenant")
    templates    = relationship("RoleTemplate", back_populates="tenant")
    results      = relationship("ScreeningResult", back_populates="tenant")
    team_members = relationship("TeamMember", back_populates="tenant")
    usage_logs   = relationship("UsageLog", back_populates="tenant")
    email_config = relationship("TenantEmailConfig", backref="tenant", uselist=False)


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(50), nullable=False, default="recruiter")  # admin / recruiter / viewer
    is_active       = Column(Boolean, default=True)
    is_platform_admin = Column(Boolean, nullable=False, default=False)
    platform_role   = Column(String(50), nullable=True)  # super_admin | billing_admin | support | security_admin | readonly
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    tenant       = relationship("Tenant", back_populates="users")
    team_member  = relationship("TeamMember", back_populates="user", uselist=False)
    comments     = relationship("Comment", back_populates="author")
    usage_logs   = relationship("UsageLog", back_populates="user")

    @property
    def is_platform_admin_compat(self) -> bool:
        """Backward compatibility: any non-null platform_role counts as platform admin."""
        return self.is_platform_admin or (self.platform_role is not None)


class UsageLog(Base):
    """Detailed usage tracking for subscription billing and analytics."""
    __tablename__ = "usage_logs"

    id         = Column(Integer, primary_key=True, index=True)
    tenant_id  = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action     = Column(String(50), nullable=False)  # resume_analysis, batch_analysis, etc.
    quantity   = Column(Integer, nullable=False, default=1)
    details    = Column(Text, nullable=True)  # JSON with context
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    tenant = relationship("Tenant", back_populates="usage_logs")
    user   = relationship("User", back_populates="usage_logs")


# ─── Candidate & results ──────────────────────────────────────────────────────

class Candidate(Base):
    __tablename__ = "candidates"

    id         = Column(Integer, primary_key=True, index=True)
    tenant_id  = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name       = Column(String(255), nullable=True)
    email      = Column(String(255), nullable=True, index=True)
    phone      = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Enriched profile (stored once, re-used for every JD re-analysis) ──────
    resume_file_hash   = Column(String(64),  nullable=True, index=True)  # MD5(file bytes)
    resume_filename    = Column(String(255), nullable=True)              # Original filename
    resume_file_data   = Column(LargeBinary, nullable=True)              # Original file bytes (BYTEA)
    resume_converted_pdf_data = Column(LargeBinary, nullable=True)       # PDF conversion of .doc for browser viewing
    raw_resume_text    = Column(Text,        nullable=True)
    parsed_skills      = Column(Text,        nullable=True)   # JSON array
    parsed_education   = Column(Text,        nullable=True)   # JSON array
    parsed_work_exp    = Column(Text,        nullable=True)   # JSON array
    gap_analysis_json  = Column(Text,        nullable=True)   # JSON object
    current_role       = Column(String(255), nullable=True)
    current_company    = Column(String(255), nullable=True)
    total_years_exp    = Column(Float,       nullable=True)
    profile_quality    = Column(String(20),  nullable=True)   # high | medium | low
    profile_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Full parse_resume() output as JSON (contact_info, raw_text, skills, …) — audit / re-analyze
    parser_snapshot_json = Column(Text, nullable=True)

    # AI-generated professional summary for the candidate profile
    ai_professional_summary = Column(Text, nullable=True)

    tenant               = relationship("Tenant", back_populates="candidates")
    results              = relationship("ScreeningResult", back_populates="candidate")
    transcript_analyses  = relationship("TranscriptAnalysis", back_populates="candidate")


class CandidateNote(Base):
    __tablename__ = "candidate_notes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate = relationship("Candidate", backref="notes")
    user = relationship("User")
    tenant = relationship("Tenant")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id                 = Column(Integer, primary_key=True, index=True)
    tenant_id          = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    candidate_id       = Column(Integer, ForeignKey("candidates.id"), nullable=True, index=True)
    role_template_id   = Column(Integer, ForeignKey("role_templates.id"), nullable=True)
    resume_text        = Column(Text, nullable=False)
    jd_text            = Column(Text, nullable=False)
    parsed_data        = Column(Text, nullable=False)   # JSON string
    analysis_result    = Column(Text, nullable=False)   # JSON string
    narrative_json     = Column(Text, nullable=True)    # LLM narrative (generated asynchronously)
    narrative_status   = Column(String(20), default="pending")  # pending | processing | ready | failed
    narrative_error    = Column(Text, nullable=True)            # error details when failed (null when successful)
    status             = Column(String(50), default="pending")  # pending/shortlisted/rejected/in-review/hired
    is_active          = Column(Boolean, default=True)          # active version for candidate analysis
    version_number     = Column(Integer, default=1)             # version tracking for re-analysis
    role_category      = Column(String(50), nullable=True)      # technical, sales, hr, marketing, operations, leadership
    weight_reasoning   = Column(Text, nullable=True)            # JSON: reasoning for suggested weights
    suggested_weights_json = Column(Text, nullable=True)        # JSON: suggested scoring weights
    timestamp          = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # ── Deterministic scoring fields ─────────────────────────────────────────
    deterministic_score = Column(Integer, nullable=True)        # Hard-capped deterministic score
    domain_match_score  = Column(Float, nullable=True)           # Domain match confidence
    core_skill_score    = Column(Float, nullable=True)           # Core skill match ratio
    eligibility_status  = Column(Boolean, nullable=True)         # Whether candidate passed eligibility gates
    eligibility_reason  = Column(String(100), nullable=True)     # Rejection reason if ineligible
    status_updated_at   = Column(DateTime(timezone=True), nullable=True)  # When status was last changed

    tenant        = relationship("Tenant", back_populates="results")
    candidate     = relationship("Candidate", back_populates="results")
    role_template = relationship("RoleTemplate", back_populates="results")
    comments      = relationship("Comment", back_populates="result")
    evaluations = relationship("InterviewEvaluation", back_populates="result", cascade="all, delete-orphan")
    overall_assessment = relationship("OverallAssessment", back_populates="result", cascade="all, delete-orphan", uselist=True)
    training_examples = relationship("TrainingExample", back_populates="result")


# ─── Role templates ───────────────────────────────────────────────────────────

class RoleTemplate(Base):
    __tablename__ = "role_templates"

    id              = Column(Integer, primary_key=True, index=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name            = Column(String(200), nullable=False)
    jd_text         = Column(Text, nullable=False)
    scoring_weights = Column(Text, nullable=True)   # JSON: {skills,experience,stability,education}
    tags            = Column(String(500), nullable=True)
    required_skills_override = Column(Text, nullable=True)  # JSON: ["skill1", "skill2"] or [{"skill": "...", "proficiency": "..."}]
    nice_to_have_skills_override = Column(Text, nullable=True)  # Same format
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    tenant               = relationship("Tenant", back_populates="templates")
    results              = relationship("ScreeningResult", back_populates="role_template")
    transcript_analyses  = relationship("TranscriptAnalysis", back_populates="role_template")


class SkillClassificationTemplate(Base):
    """Saved skill classification templates scoped per tenant for reuse across JDs."""
    __tablename__ = "skill_classification_templates"

    id                  = Column(Integer, primary_key=True, index=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    name                = Column(String(255), nullable=False)
    role_template_id    = Column(Integer, ForeignKey("role_templates.id"), nullable=True)
    required_skills     = Column(Text, nullable=False, default="[]")       # JSON array
    nice_to_have_skills = Column(Text, nullable=False, default="[]")       # JSON array
    created_by          = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tenant          = relationship("Tenant")
    role_template   = relationship("RoleTemplate")
    created_by_user = relationship("User")


# ─── Team collaboration ───────────────────────────────────────────────────────

class TeamMember(Base):
    __tablename__ = "team_members"

    id        = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    role      = Column(String(50), nullable=False, default="recruiter")

    tenant = relationship("Tenant", back_populates="team_members")
    user   = relationship("User", back_populates="team_member")


class Comment(Base):
    __tablename__ = "comments"

    id        = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("screening_results.id"), nullable=False)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    text      = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    result = relationship("ScreeningResult", back_populates="comments")
    author = relationship("User", back_populates="comments")


class InterviewEvaluation(Base):
    """Per-question recruiter evaluation (note + rating)."""
    __tablename__ = "interview_evaluations"

    id                = Column(Integer, primary_key=True, index=True)
    result_id         = Column(Integer, ForeignKey("screening_results.id"), nullable=False, index=True)
    user_id           = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_category = Column(String(30), nullable=False)
    question_index    = Column(Integer, nullable=False)
    rating            = Column(String(10), nullable=True)
    notes             = Column(Text, nullable=True)
    created_at        = Column(DateTime(timezone=True), server_default=func.now())
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    result = relationship("ScreeningResult", back_populates="evaluations")
    evaluator = relationship("User")

    __table_args__ = (
        UniqueConstraint('result_id', 'user_id', 'question_category', 'question_index',
                         name='uq_eval_per_question'),
    )

class OverallAssessment(Base):
    """Recruiter's overall assessment for HM scorecard."""
    __tablename__ = "overall_assessments"

    id                       = Column(Integer, primary_key=True, index=True)
    result_id                = Column(Integer, ForeignKey("screening_results.id"), nullable=False, index=True)
    user_id                  = Column(Integer, ForeignKey("users.id"), nullable=False)
    overall_assessment       = Column(Text, nullable=True)
    recruiter_recommendation = Column(String(10), nullable=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now())
    updated_at               = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    result = relationship("ScreeningResult", back_populates="overall_assessment")
    evaluator = relationship("User")

    __table_args__ = (
        UniqueConstraint('result_id', 'user_id', name='uq_overall_per_user'),
    )


# ─── Transcript analysis ──────────────────────────────────────────────────────

class TranscriptAnalysis(Base):
    __tablename__ = "transcript_analyses"

    id               = Column(Integer, primary_key=True, index=True)
    tenant_id        = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    candidate_id     = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    role_template_id = Column(Integer, ForeignKey("role_templates.id"), nullable=True)
    transcript_text  = Column(Text, nullable=False)
    source_platform  = Column(String(50), nullable=True)   # zoom / teams / manual
    analysis_result  = Column(Text, nullable=False)         # JSON
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    candidate     = relationship("Candidate", back_populates="transcript_analyses")
    role_template = relationship("RoleTemplate", back_populates="transcript_analyses")


# ─── Custom AI training ───────────────────────────────────────────────────────

class TrainingExample(Base):
    __tablename__ = "training_examples"

    id                  = Column(Integer, primary_key=True, index=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    screening_result_id = Column(Integer, ForeignKey("screening_results.id"), nullable=False)
    outcome             = Column(String(50), nullable=False)   # hired / rejected
    feedback            = Column(Text, nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())

    result = relationship("ScreeningResult", back_populates="training_examples")


# ─── Hybrid pipeline caches & skills registry ─────────────────────────────────

class JdCache(Base):
    """Shared JD parse cache across all workers. Keyed by MD5 of first 2000 chars."""
    __tablename__ = "jd_cache"

    hash        = Column(String(64), primary_key=True)
    result_json = Column(Text,       nullable=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class Skill(Base):
    """Dynamic skills registry — seed from hardcoded list, grow via discovery."""
    __tablename__ = "skills"

    id         = Column(Integer,     primary_key=True, index=True)
    name       = Column(String(200), unique=True, nullable=False)
    aliases    = Column(Text,        nullable=True)   # comma-separated alias list
    domain     = Column(String(50),  nullable=True)   # backend|frontend|data_science|...
    status     = Column(String(20),  nullable=False, default="active")  # active|pending|rejected
    source     = Column(String(20),  nullable=False, default="seed")    # seed|discovered|manual
    frequency  = Column(Integer,     nullable=False, default=0)         # times seen in JDs/resumes
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── Token revocation ─────────────────────────────────────────────────────────

class RevokedToken(Base):
    """Tracks revoked JWT tokens to prevent reuse after logout."""
    __tablename__ = "revoked_tokens"

    id          = Column(Integer, primary_key=True, index=True)
    jti         = Column(String(64), unique=True, index=True, nullable=False)  # JWT ID (UUID)
    revoked_at  = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at  = Column(DateTime(timezone=True), nullable=False)  # When token would have expired


class AuditLog(Base):
    """Platform admin audit trail."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_email = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class FeatureFlag(Base):
    """Global feature flags for the platform."""
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    enabled_globally = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    overrides = relationship("TenantFeatureOverride", back_populates="feature_flag")
    plan_features = relationship("PlanFeature", back_populates="feature_flag", cascade="all, delete-orphan")

class TenantFeatureOverride(Base):
    """Per-tenant feature flag overrides."""
    __tablename__ = "tenant_feature_overrides"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    feature_flag_id = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    enabled = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    feature_flag = relationship("FeatureFlag", back_populates="overrides")

    __table_args__ = (UniqueConstraint('tenant_id', 'feature_flag_id', name='uq_tenant_feature'),)

class RateLimitConfig(Base):
    """Per-tenant rate limiting configuration."""
    __tablename__ = "rate_limit_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    requests_per_minute = Column(Integer, nullable=False, default=60)
    llm_concurrent_max = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Webhook(Base):
    """Tenant webhook configuration for event notifications."""
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    secret = Column(String(255), nullable=False)
    events = Column(Text, nullable=False, default="[]")  # JSON array of event names
    is_active = Column(Boolean, nullable=False, default=True)
    failure_count = Column(Integer, nullable=False, default=0)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    deliveries = relationship("WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan")


class WebhookDelivery(Base):
    """Record of a webhook delivery attempt."""
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    event = Column(String(100), nullable=False)
    payload = Column(Text, nullable=True)  # JSON
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    attempt = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    webhook = relationship("Webhook", back_populates="deliveries")


class PlatformConfig(Base):
    """Platform-level key-value configuration for billing provider settings."""
    __tablename__ = "platform_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(255), unique=True, nullable=False, index=True)
    config_value = Column(Text, nullable=False)
    description = Column(String(500), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class TenantEmailConfig(Base):
    """Per-tenant SMTP email configuration for outbound notifications."""
    __tablename__ = "tenant_email_configs"

    id              = Column(Integer, primary_key=True, index=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), unique=True, nullable=False)
    smtp_host       = Column(String(255), nullable=False)
    smtp_port       = Column(Integer, default=587)
    smtp_user       = Column(String(255), nullable=True)
    smtp_password   = Column(String(500), nullable=True)          # Fernet-encrypted
    smtp_from       = Column(String(255), nullable=False)
    from_name       = Column(String(255), nullable=True)
    reply_to        = Column(String(255), nullable=True)
    encryption_type = Column(String(10), default="tls")           # tls, ssl, none
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    configured_by   = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_test_at    = Column(DateTime(timezone=True), nullable=True)
    last_test_success = Column(Boolean, nullable=True)


class ImpersonationSession(Base):
    """Tracks active admin impersonation sessions for support/debugging."""
    __tablename__ = "impersonation_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    admin_user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_user_id  = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash      = Column(String(64), unique=True, nullable=False, index=True)
    expires_at      = Column(DateTime(timezone=True), nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at      = Column(DateTime(timezone=True), nullable=True)
    ip_address      = Column(String(45), nullable=True)

    admin_user  = relationship("User", foreign_keys=[admin_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])


class SecurityEvent(Base):
    """Security monitoring events: logins, failures, suspicious activity."""
    __tablename__ = "security_events"

    id          = Column(Integer, primary_key=True, index=True)
    tenant_id   = Column(Integer, ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_type  = Column(String(50), nullable=False)
    ip_address  = Column(String(45), nullable=True)
    user_agent  = Column(String(500), nullable=True)
    details     = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")
    user   = relationship("User")


class PlanFeature(Base):
    """Maps subscription plans to feature flag entitlements."""
    __tablename__ = "plan_features"

    id               = Column(Integer, primary_key=True, index=True)
    plan_id          = Column(Integer, ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False)
    feature_flag_id  = Column(Integer, ForeignKey("feature_flags.id", ondelete="CASCADE"), nullable=False)
    enabled          = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    plan         = relationship("SubscriptionPlan", back_populates="plan_features")
    feature_flag = relationship("FeatureFlag", back_populates="plan_features")

    __table_args__ = (UniqueConstraint("plan_id", "feature_flag_id", name="uq_plan_feature"),)


class ErasureLog(Base):
    """Audit trail for GDPR data erasure requests."""
    __tablename__ = "erasure_logs"

    id               = Column(Integer, primary_key=True, index=True)
    tenant_id        = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    actor_user_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status           = Column(String(20), nullable=False, default="requested")
    started_at       = Column(DateTime(timezone=True), nullable=True)
    completed_at     = Column(DateTime(timezone=True), nullable=True)
    records_affected = Column(Integer, nullable=False, default=0)
    details          = Column(Text, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")
    actor  = relationship("User")


# ─── Historical learning system ────────────────────────────────────────────────

class HiringOutcome(Base):
    """Tracks hiring decisions for historical learning and model calibration."""
    __tablename__ = "hiring_outcomes"

    id                   = Column(Integer, primary_key=True, index=True)
    tenant_id            = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    screening_result_id  = Column(Integer, ForeignKey("screening_results.id"), unique=True, nullable=False)
    candidate_id         = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    role_template_id     = Column(Integer, ForeignKey("role_templates.id"), nullable=True, index=True)
    decision             = Column(String(20), nullable=False)          # hired|rejected|withdrawn|no_decision
    decision_stage       = Column(String(50), nullable=True)           # screening|phone_screen|interview|offer|onboarded
    decision_date        = Column(DateTime, nullable=True)
    decision_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)
    feedback_rating      = Column(Integer, nullable=True)              # 1-5
    feedback_notes       = Column(Text, nullable=True)
    source               = Column(String(20), server_default="manual") # manual|ats_webhook
    metadata_json        = Column(Text, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())
    updated_at           = Column(DateTime(timezone=True), onupdate=func.now())

    tenant            = relationship("Tenant")
    screening_result  = relationship("ScreeningResult")
    candidate         = relationship("Candidate")
    role_template     = relationship("RoleTemplate")
    decision_by_user  = relationship("User")

    __table_args__ = (
        Index("ix_hiring_outcomes_tenant_template", "tenant_id", "role_template_id"),
        Index("ix_hiring_outcomes_tenant_decision_date", "tenant_id", "decision", "created_at"),
    )


class TeamSkillProfile(Base):
    """Team-level skill profile for gap analysis and benchmarking."""
    __tablename__ = "team_skill_profiles"

    id                  = Column(Integer, primary_key=True, index=True)
    tenant_id           = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    team_name           = Column(String(200), nullable=False)
    skills_json         = Column(Text, nullable=True)                  # JSON array
    job_functions       = Column(Text, nullable=True)                  # JSON array
    member_count        = Column(Integer, nullable=True)
    created_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    tenant          = relationship("Tenant")
    created_by_user = relationship("User")


class SkillTrendSnapshot(Base):
    """Periodic snapshot of skill demand/supply trends for analytics."""
    __tablename__ = "skill_trend_snapshots"

    id                   = Column(Integer, primary_key=True, index=True)
    tenant_id            = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    role_category        = Column(String(50), nullable=True)
    skill_name           = Column(String(200), nullable=False)
    period_date          = Column(Date, nullable=False)
    jd_mention_count     = Column(Integer, default=0)
    resume_present_count = Column(Integer, default=0)
    hired_with_skill     = Column(Integer, default=0)
    total_hired          = Column(Integer, default=0)
    trend_direction      = Column(String(10), nullable=True)           # rising|falling|stable
    growth_pct           = Column(Float, nullable=True)
    created_at           = Column(DateTime(timezone=True), server_default=func.now())

    tenant = relationship("Tenant")

    __table_args__ = (
        Index("ix_skill_trends_tenant_category_date", "tenant_id", "role_category", "period_date"),
        Index("ix_skill_trends_tenant_skill_date", "tenant_id", "skill_name", "period_date"),
    )


class OutcomeSkillPattern(Base):
    """Statistical correlation between skills and hiring outcomes."""
    __tablename__ = "outcome_skill_patterns"

    id                      = Column(Integer, primary_key=True, index=True)
    tenant_id               = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    role_template_id        = Column(Integer, ForeignKey("role_templates.id"), nullable=True, index=True)
    role_category           = Column(String(50), nullable=True)
    skill_name              = Column(String(200), nullable=False)
    correlation_score       = Column(Float, nullable=True)
    present_in_hired_pct    = Column(Float, nullable=True)
    present_in_rejected_pct = Column(Float, nullable=True)
    sample_size             = Column(Integer, nullable=True)
    last_computed_at        = Column(DateTime, nullable=True)
    created_at              = Column(DateTime(timezone=True), server_default=func.now())

    tenant        = relationship("Tenant")
    role_template = relationship("RoleTemplate")

    __table_args__ = (
        Index("ix_outcome_patterns_tenant_template", "tenant_id", "role_template_id"),
    )

