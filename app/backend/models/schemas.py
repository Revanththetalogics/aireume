from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# ─── Candidate deduplication & re-analysis ────────────────────────────────────

class DuplicateCandidateInfo(BaseModel):
    """Returned when an uploaded resume matches an existing candidate in the DB."""
    id:              int
    name:            Optional[str]  = None
    email:           Optional[str]  = None
    current_role:    Optional[str]  = None
    current_company: Optional[str]  = None
    total_years_exp: Optional[float] = None
    skills_snapshot: List[str]      = []
    result_count:    int            = 0
    last_analyzed:   Optional[str]  = None  # ISO format datetime string
    profile_quality: Optional[str]  = None


class AnalyzeJdRequest(BaseModel):
    """Body for POST /api/candidates/{id}/analyze-jd (no file upload needed)."""
    job_description: str
    scoring_weights: Optional[Dict[str, float]] = None


# ─── Core analysis ────────────────────────────────────────────────────────────

class EmploymentGap(BaseModel):
    start_date: str
    end_date: str
    duration_months: int
    severity: Optional[str] = None   # negligible | minor | moderate | critical


class RiskSignal(BaseModel):
    type: str
    description: str
    severity: Optional[str] = None   # low | medium | high


class ScoreBreakdown(BaseModel):
    # Backward-compat fields (always populated)
    skill_match:      Optional[int] = 0
    experience_match: Optional[int] = 0
    stability:        Optional[int] = 0   # mapped from timeline score
    education:        Optional[int] = 0
    # New LangGraph dimensions
    architecture:     Optional[int] = None
    domain_fit:       Optional[int] = None
    timeline:         Optional[int] = None
    risk_penalty:     Optional[int] = None


class InterviewQuestions(BaseModel):
    technical_questions:   List[str] = []
    behavioral_questions:  List[str] = []
    culture_fit_questions: List[str] = []

    @field_validator('technical_questions', 'behavioral_questions', 'culture_fit_questions', mode='before')
    @classmethod
    def coerce_to_str_list(cls, v):
        """Coerce LLM output that may return objects/non-strings into a clean list[str]."""
        if not isinstance(v, list):
            return []
        return [item if isinstance(item, str) else str(item) for item in v]


class ScoringWeights(BaseModel):
    # Updated defaults to match the new 7-dimension formula
    skills:       float = 0.30
    experience:   float = 0.20
    architecture: float = 0.15
    education:    float = 0.10
    timeline:     float = 0.10
    domain:       float = 0.10
    risk:         float = 0.15


class ExplainabilityDetail(BaseModel):
    skill_rationale:      Optional[str] = None
    experience_rationale: Optional[str] = None
    education_rationale:  Optional[str] = None
    timeline_rationale:   Optional[str] = None
    overall_rationale:    Optional[str] = None


class AnalysisResponse(BaseModel):
    model_config = {"extra": "ignore"}   # silently drop any LLM-produced extra keys

    # ── Core backward-compat fields ──
    fit_score:            Optional[int] = None  # null = "Pending" state
    job_role:             Optional[str] = None
    strengths:            List[str] = []
    weaknesses:           List[str] = []
    employment_gaps:      List[Any] = []
    education_analysis:   Optional[str] = None
    risk_signals:         List[Any] = []
    final_recommendation: str = "Pending"       # Shortlist | Consider | Reject | Pending
    score_breakdown:      Optional[ScoreBreakdown] = None
    matched_skills:       Optional[List[str]] = []
    missing_skills:       Optional[List[str]] = []
    risk_level:           Optional[str] = "Low"
    interview_questions:  Optional[InterviewQuestions] = None
    required_skills_count: Optional[int] = 0
    result_id:            Optional[int] = None
    candidate_id:         Optional[int] = None
    candidate_name:       Optional[str] = None
    work_experience:      Optional[List[Any]] = []
    contact_info:         Optional[Dict[str, Any]] = None
    # ── New hybrid pipeline fields ──
    jd_analysis:              Optional[Dict[str, Any]] = None
    candidate_profile:        Optional[Dict[str, Any]] = None
    skill_analysis:           Optional[Dict[str, Any]] = None
    edu_timeline_analysis:    Optional[Dict[str, Any]] = None
    explainability:           Optional[ExplainabilityDetail] = None
    recommendation_rationale: Optional[str] = None
    adjacent_skills:          Optional[List[str]] = []
    pipeline_errors:          Optional[List[str]] = []
    # ── Production hardening fields ──
    analysis_quality:   Optional[str] = None   # high | medium | low
    narrative_pending:  Optional[bool] = False  # True if LLM timed out, Python scores still valid
    duplicate_candidate: Optional[DuplicateCandidateInfo] = None


class BatchAnalysisResult(BaseModel):
    rank: int
    filename: str
    result: AnalysisResponse


class BatchAnalysisResponse(BaseModel):
    results: List[BatchAnalysisResult]
    total: int


# ─── Auth ─────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    company_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    tenant: Dict[str, Any]


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    tenant_id: int

    class Config:
        from_attributes = True


# ─── Screening results ────────────────────────────────────────────────────────

class ScreeningResultResponse(BaseModel):
    id: int
    timestamp: datetime
    analysis_result: dict
    status: Optional[str] = "pending"
    candidate_id: Optional[int] = None

    class Config:
        from_attributes = True


class StatusUpdate(BaseModel):
    status: str  # pending / shortlisted / rejected / in-review / hired


# ─── Candidates ───────────────────────────────────────────────────────────────

class CandidateNameUpdate(BaseModel):
    name: str


class CandidateOut(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    created_at: datetime
    result_count: Optional[int] = 0

    class Config:
        from_attributes = True


# ─── Templates ───────────────────────────────────────────────────────────────

class TemplateCreate(BaseModel):
    name: str
    jd_text: str
    scoring_weights: Optional[Dict[str, float]] = None
    tags: Optional[str] = None


class TemplateOut(BaseModel):
    id: int
    name: str
    jd_text: str
    scoring_weights: Optional[str] = None
    tags: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Email generation ─────────────────────────────────────────────────────────

class EmailGenRequest(BaseModel):
    candidate_id: int
    type: str   # shortlist / rejection / screening_call


class EmailGenResponse(BaseModel):
    subject: str
    body: str


# ─── JD URL extraction ────────────────────────────────────────────────────────

class JdUrlRequest(BaseModel):
    url: str


class JdUrlResponse(BaseModel):
    jd_text: str
    source_url: str


# ─── Team ─────────────────────────────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: str
    role: str = "recruiter"


class CommentCreate(BaseModel):
    text: str


class CommentOut(BaseModel):
    id: int
    text: str
    created_at: datetime
    author_email: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Compare ─────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    candidate_ids: List[int]


# ─── Training ────────────────────────────────────────────────────────────────

class LabelRequest(BaseModel):
    screening_result_id: int
    outcome: str    # hired / rejected
    feedback: Optional[str] = ""


class TrainingStatusResponse(BaseModel):
    labeled_count: int
    trained: bool
    model_name: Optional[str] = None
    last_trained: Optional[datetime] = None


# ─── Transcript analysis ──────────────────────────────────────────────────────

class JdAlignmentItem(BaseModel):
    requirement: str
    demonstrated: bool
    evidence: Optional[str] = None


class TranscriptAnalysisResult(BaseModel):
    fit_score: int
    technical_depth: int
    communication_quality: int
    jd_alignment: List[JdAlignmentItem]
    strengths: List[str]
    areas_for_improvement: List[str]
    bias_note: str
    recommendation: str   # proceed / hold / reject


class TranscriptAnalysisResponse(BaseModel):
    id: int
    candidate_id: Optional[int] = None
    candidate_name: Optional[str] = None
    role_template_id: Optional[int] = None
    role_template_name: Optional[str] = None
    source_platform: Optional[str] = None
    analysis_result: TranscriptAnalysisResult
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptAnalysisListItem(BaseModel):
    id: int
    candidate_id: Optional[int] = None
    candidate_name: Optional[str] = None
    role_template_id: Optional[int] = None
    role_template_name: Optional[str] = None
    source_platform: Optional[str] = None
    fit_score: Optional[int] = None
    recommendation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Subscription ───────────────────────────────────────────────────────────────

class PlanInfo(BaseModel):
    """Subscription plan information."""
    id: int
    name: str
    display_name: str
    description: str
    price_monthly: int
    price_yearly: int
    currency: str
    features: List[str]
    limits: Dict[str, Any]


class UsageStats(BaseModel):
    """Current usage statistics for a tenant."""
    analyses_used: int
    analyses_limit: int
    storage_used_mb: float
    storage_limit_gb: int
    team_members_count: int
    team_members_limit: int
    percent_used: float


class SubscriptionResponse(BaseModel):
    """Full subscription response for current tenant."""
    current_plan: PlanInfo
    status: str  # active, trialing, cancelled, past_due
    billing_cycle: str  # monthly, yearly
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    price: int
    usage: UsageStats
    available_plans: List[PlanInfo]
    days_until_reset: int
