from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime


# ─── Core analysis ────────────────────────────────────────────────────────────

class EmploymentGap(BaseModel):
    start_date: str
    end_date: str
    duration_months: int


class RiskSignal(BaseModel):
    type: str
    description: str


class ScoreBreakdown(BaseModel):
    skill_match: Optional[int] = 0
    experience_match: Optional[int] = 0
    stability: Optional[int] = 0
    education: Optional[int] = 0


class InterviewQuestions(BaseModel):
    technical_questions: List[str] = []
    behavioral_questions: List[str] = []
    culture_fit_questions: List[str] = []


class ScoringWeights(BaseModel):
    skills: float = 0.40
    experience: float = 0.35
    stability: float = 0.15
    education: float = 0.10


class AnalysisResponse(BaseModel):
    fit_score: int
    strengths: List[str]
    weaknesses: List[str]
    employment_gaps: List[EmploymentGap]
    education_analysis: str
    risk_signals: List[Any]
    final_recommendation: str
    score_breakdown: Optional[ScoreBreakdown] = None
    matched_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []
    risk_level: Optional[str] = "Low"
    interview_questions: Optional[InterviewQuestions] = None
    required_skills_count: Optional[int] = 0
    result_id: Optional[int] = None
    candidate_id: Optional[int] = None
    candidate_name: Optional[str] = None


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
