from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


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


class AnalysisResponse(BaseModel):
    fit_score: int  # 0-100 composite
    strengths: List[str]
    weaknesses: List[str]
    employment_gaps: List[EmploymentGap]
    education_analysis: str
    risk_signals: List[str]          # LLM returns plain strings in agent pipeline
    final_recommendation: str        # "Shortlist" | "Consider" | "Reject"
    # Enterprise fields from agent pipeline
    score_breakdown: Optional[ScoreBreakdown] = None
    matched_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []
    risk_level: Optional[str] = "Low"  # "Low" | "Medium" | "High"


class ScreeningResultResponse(BaseModel):
    id: int
    timestamp: datetime
    analysis_result: dict

    class Config:
        from_attributes = True
