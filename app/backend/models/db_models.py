from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean,
    ForeignKey, Float, func
)
from sqlalchemy.orm import relationship
from app.backend.db.database import Base


# ─── Multi-tenancy ────────────────────────────────────────────────────────────

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id      = Column(Integer, primary_key=True, index=True)
    name    = Column(String(50), unique=True, nullable=False)   # free / pro / enterprise
    limits  = Column(Text, nullable=False, default="{}")        # JSON: analyses_per_month, batch_size, etc.

    tenants = relationship("Tenant", back_populates="plan")


class Tenant(Base):
    __tablename__ = "tenants"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False)
    slug       = Column(String(100), unique=True, nullable=False)
    plan_id    = Column(Integer, ForeignKey("subscription_plans.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    plan         = relationship("SubscriptionPlan", back_populates="tenants")
    users        = relationship("User", back_populates="tenant")
    candidates   = relationship("Candidate", back_populates="tenant")
    templates    = relationship("RoleTemplate", back_populates="tenant")
    results      = relationship("ScreeningResult", back_populates="tenant")
    team_members = relationship("TeamMember", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    email           = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(50), nullable=False, default="recruiter")  # admin / recruiter / viewer
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    tenant       = relationship("Tenant", back_populates="users")
    team_member  = relationship("TeamMember", back_populates="user", uselist=False)
    comments     = relationship("Comment", back_populates="author")


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

    tenant               = relationship("Tenant", back_populates="candidates")
    results              = relationship("ScreeningResult", back_populates="candidate")
    transcript_analyses  = relationship("TranscriptAnalysis", back_populates="candidate")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id                 = Column(Integer, primary_key=True, index=True)
    tenant_id          = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    candidate_id       = Column(Integer, ForeignKey("candidates.id"), nullable=True)
    role_template_id   = Column(Integer, ForeignKey("role_templates.id"), nullable=True)
    resume_text        = Column(Text, nullable=False)
    jd_text            = Column(Text, nullable=False)
    parsed_data        = Column(Text, nullable=False)   # JSON string
    analysis_result    = Column(Text, nullable=False)   # JSON string
    status             = Column(String(50), default="pending")  # pending/shortlisted/rejected/in-review/hired
    timestamp          = Column(DateTime(timezone=True), server_default=func.now())

    tenant        = relationship("Tenant", back_populates="results")
    candidate     = relationship("Candidate", back_populates="results")
    role_template = relationship("RoleTemplate", back_populates="results")
    comments      = relationship("Comment", back_populates="result")
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
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    tenant               = relationship("Tenant", back_populates="templates")
    results              = relationship("ScreeningResult", back_populates="role_template")
    transcript_analyses  = relationship("TranscriptAnalysis", back_populates="role_template")


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
