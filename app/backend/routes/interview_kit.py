"""Interview Kit evaluation and scorecard API."""
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    InterviewEvaluation, OverallAssessment, ScreeningResult, User,
)
from app.backend.models.schemas import (
    EvaluationUpsert, EvaluationOut,
    OverallAssessmentUpsert,
    ScorecardDimension, ScorecardOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/results", tags=["interview-kit"])


# ─── helpers ──────────────────────────────────────────────────────────────────

def _verify_result_access(result_id: int, current_user: User, db: Session) -> ScreeningResult:
    """Load a ScreeningResult and verify tenant ownership. Raises 404/403."""
    result = db.query(ScreeningResult).filter(ScreeningResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Screening result not found")
    if result.tenant_id and result.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return result


# ─── Endpoint 1: Upsert a single question evaluation ─────────────────────────

@router.put("/{result_id}/evaluations", response_model=EvaluationOut)
def upsert_evaluation(
    result_id: int,
    body: EvaluationUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_result_access(result_id, current_user, db)

    existing = db.query(InterviewEvaluation).filter(
        and_(
            InterviewEvaluation.result_id == result_id,
            InterviewEvaluation.user_id == current_user.id,
            InterviewEvaluation.question_category == body.question_category,
            InterviewEvaluation.question_index == body.question_index,
        )
    ).first()

    if existing:
        if body.rating is not None:
            existing.rating = body.rating
        if body.notes is not None:
            existing.notes = body.notes
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_eval = InterviewEvaluation(
            result_id=result_id,
            user_id=current_user.id,
            question_category=body.question_category,
            question_index=body.question_index,
            rating=body.rating,
            notes=body.notes,
        )
        db.add(new_eval)
        db.commit()
        db.refresh(new_eval)
        return new_eval


# ─── Endpoint 2: Get all evaluations for a result ─────────────────────────────

@router.get("/{result_id}/evaluations", response_model=List[EvaluationOut])
def get_evaluations(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_result_access(result_id, current_user, db)

    evals = db.query(InterviewEvaluation).filter(
        and_(
            InterviewEvaluation.result_id == result_id,
            InterviewEvaluation.user_id == current_user.id,
        )
    ).order_by(InterviewEvaluation.question_category, InterviewEvaluation.question_index).all()
    return evals


# ─── Endpoint 3: Save overall assessment ──────────────────────────────────────

@router.put("/{result_id}/evaluations/overall")
def upsert_overall_assessment(
    result_id: int,
    body: OverallAssessmentUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _verify_result_access(result_id, current_user, db)

    existing = db.query(OverallAssessment).filter(
        and_(
            OverallAssessment.result_id == result_id,
            OverallAssessment.user_id == current_user.id,
        )
    ).first()

    if existing:
        existing.overall_assessment = body.overall_assessment
        if body.recruiter_recommendation is not None:
            existing.recruiter_recommendation = body.recruiter_recommendation
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "id": existing.id}
    else:
        new_assessment = OverallAssessment(
            result_id=result_id,
            user_id=current_user.id,
            overall_assessment=body.overall_assessment,
            recruiter_recommendation=body.recruiter_recommendation,
        )
        db.add(new_assessment)
        db.commit()
        db.refresh(new_assessment)
        return {"status": "created", "id": new_assessment.id}


# ─── Endpoint 4: Generate scorecard ───────────────────────────────────────────

@router.get("/{result_id}/scorecard", response_model=ScorecardOut)
def get_scorecard(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = _verify_result_access(result_id, current_user, db)

    # Parse analysis data
    analysis = json.loads(result.analysis_result) if result.analysis_result else {}
    parsed = json.loads(result.parsed_data) if result.parsed_data else {}
    contact = parsed.get("contact_info", {})
    jd_analysis = analysis.get("jd_analysis", {})

    # Get user's evaluations
    evals = db.query(InterviewEvaluation).filter(
        and_(
            InterviewEvaluation.result_id == result_id,
            InterviewEvaluation.user_id == current_user.id,
        )
    ).all()

    # Get interview questions to count totals
    iq = analysis.get("interview_questions", {})
    tech_total = len(iq.get("technical_questions", []))
    beh_total = len(iq.get("behavioral_questions", []))
    cult_total = len(iq.get("culture_fit_questions", []))

    # Build dimension summaries
    def build_dimension(category: str, total: int) -> ScorecardDimension:
        cat_evals = [e for e in evals if e.question_category == category]
        strong = sum(1 for e in cat_evals if e.rating == "strong")
        adequate = sum(1 for e in cat_evals if e.rating == "adequate")
        weak = sum(1 for e in cat_evals if e.rating == "weak")
        key_notes = [e.notes for e in cat_evals if e.notes and e.notes.strip()]
        return ScorecardDimension(
            category=category,
            total_questions=total,
            evaluated_count=len(cat_evals),
            strong_count=strong,
            adequate_count=adequate,
            weak_count=weak,
            key_notes=key_notes[:5],
        )

    tech_summary = build_dimension("technical", tech_total)
    beh_summary = build_dimension("behavioral", beh_total)
    cult_summary = build_dimension("culture_fit", cult_total)

    # Derive strengths/concerns from evaluations
    strengths = [e.notes for e in evals if e.rating == "strong" and e.notes and e.notes.strip()]
    concerns = [e.notes for e in evals if e.rating == "weak" and e.notes and e.notes.strip()]

    # Get overall assessment
    overall = db.query(OverallAssessment).filter(
        and_(
            OverallAssessment.result_id == result_id,
            OverallAssessment.user_id == current_user.id,
        )
    ).first()

    # Find latest evaluation timestamp
    latest_eval = max((e.updated_at for e in evals), default=None) if evals else None

    return ScorecardOut(
        candidate_name=contact.get("name", "Unknown"),
        role_title=jd_analysis.get("role_title", "N/A"),
        fit_score=analysis.get("fit_score"),
        recommendation=analysis.get("final_recommendation"),
        evaluator_email=current_user.email,
        evaluated_at=latest_eval,
        technical_summary=tech_summary,
        behavioral_summary=beh_summary,
        culture_fit_summary=cult_summary,
        overall_assessment=overall.overall_assessment if overall else None,
        recruiter_recommendation=overall.recruiter_recommendation if overall else None,
        strengths_confirmed=strengths[:5],
        concerns_identified=concerns[:5],
    )
