from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class EmploymentGap(BaseModel):
    start_date: str
    end_date: str
    duration_months: int


class RiskSignal(BaseModel):
    type: str
    description: str


class AnalysisResponse(BaseModel):
    fit_score: int  # 0-100
    strengths: List[str]
    weaknesses: List[str]
    employment_gaps: List[EmploymentGap]
    education_analysis: str
    risk_signals: List[RiskSignal]
    final_recommendation: str  # "Shortlist" | "Consider" | "Reject"


class ScreeningResultResponse(BaseModel):
    id: int
    timestamp: datetime
    analysis_result: dict

    class Config:
        from_attributes = True
