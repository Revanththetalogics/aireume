"""Interview Kit evaluation and scorecard API."""
import json
import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.middleware.rbac import require_recruiter_or_admin
from app.backend.models.db_models import (
    InterviewEvaluation, OverallAssessment, ScreeningResult, User,
)
from app.backend.models.schemas import (
    EvaluationUpsert, EvaluationOut,
    OverallAssessmentUpsert,
    EvaluatorInfo, ScorecardDimension, ScorecardOut,
    DebriefRequest, DebriefContent, DebriefResponse,
    ScoreFeedbackRequest,
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
    current_user: User = Depends(require_recruiter_or_admin),
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
    current_user: User = Depends(require_recruiter_or_admin),
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
    current_user: User = Depends(require_recruiter_or_admin),
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

    # Get ALL team evaluations (with evaluator info eager-loaded)
    evals = db.query(InterviewEvaluation).options(
        joinedload(InterviewEvaluation.evaluator)
    ).filter(
        InterviewEvaluation.result_id == result_id,
    ).all()

    # Get interview questions to count totals
    iq = analysis.get("interview_questions", {})
    tech_total = len(iq.get("technical_questions", []))
    beh_total = len(iq.get("behavioral_questions", []))
    cult_total = len(iq.get("culture_fit_questions", []))
    exp_total = len(iq.get("experience_deep_dive_questions", []))

    # Build dimension summaries
    def build_dimension(category: str, total: int) -> ScorecardDimension:
        cat_evals = [e for e in evals if e.question_category == category]
        strong = sum(1 for e in cat_evals if e.rating == "strong")
        adequate = sum(1 for e in cat_evals if e.rating == "adequate")
        weak = sum(1 for e in cat_evals if e.rating == "weak")
        key_notes = [e.notes for e in cat_evals if e.notes and e.notes.strip()]
        evaluators = [
            EvaluatorInfo(
                user_id=e.user_id,
                email=e.evaluator.email if e.evaluator else "Unknown",
                rating=e.rating,
                question_index=e.question_index,
                notes=e.notes,
            )
            for e in cat_evals if e.rating
        ]
        return ScorecardDimension(
            category=category,
            total_questions=total,
            evaluated_count=len([e for e in cat_evals if e.rating]),
            strong_count=strong,
            adequate_count=adequate,
            weak_count=weak,
            key_notes=key_notes[:5],
            evaluators=evaluators,
        )

    tech_summary = build_dimension("technical", tech_total)
    beh_summary = build_dimension("behavioral", beh_total)
    cult_summary = build_dimension("culture_fit", cult_total)
    exp_summary = build_dimension("experience_deep_dive", exp_total)

    # Derive strengths/concerns from evaluations
    strengths = [e.notes for e in evals if e.rating == "strong" and e.notes and e.notes.strip()]
    concerns = [e.notes for e in evals if e.rating == "weak" and e.notes and e.notes.strip()]

    # Get overall assessment (by current user, for the editable field)
    overall = db.query(OverallAssessment).filter(
        and_(
            OverallAssessment.result_id == result_id,
            OverallAssessment.user_id == current_user.id,
        )
    ).first()

    # Find latest evaluation timestamp across ALL team evaluations
    latest_eval = max((e.updated_at for e in evals), default=None) if evals else None

    # Unique evaluators across all dimensions
    evaluator_emails = list({
        e.evaluator.email for e in evals if e.evaluator
    })

    return ScorecardOut(
        candidate_name=contact.get("name", "Unknown"),
        role_title=jd_analysis.get("role_title", "N/A"),
        fit_score=analysis.get("fit_score"),
        recommendation=analysis.get("final_recommendation"),
        evaluator_email=", ".join(evaluator_emails) if evaluator_emails else current_user.email,
        evaluated_at=latest_eval,
        technical_summary=tech_summary,
        behavioral_summary=beh_summary,
        culture_fit_summary=cult_summary,
        experience_deep_dive_summary=exp_summary,
        overall_assessment=overall.overall_assessment if overall else None,
        recruiter_recommendation=overall.recruiter_recommendation if overall else None,
        strengths_confirmed=strengths[:5],
        concerns_identified=concerns[:5],
        debrief=DebriefContent(**json.loads(overall.debrief_json)) if overall and overall.debrief_json else None,
        recruiter_score=overall.recruiter_score if overall else None,
    )


# ─── Endpoint 5: Generate LLM debrief ─────────────────────────────────────────

@router.post("/{result_id}/generate-debrief", response_model=DebriefResponse)
async def generate_debrief(
    result_id: int,
    body: DebriefRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter_or_admin),
):
    """Generate an LLM-powered debrief from recruiter conversation summary and evaluations."""
    result = _verify_result_access(result_id, current_user, db)

    # 1. Load analysis data
    analysis = json.loads(result.analysis_result) if result.analysis_result else {}
    parsed = json.loads(result.parsed_data) if result.parsed_data else {}

    # 2. Load all evaluations for this result
    evals = db.query(InterviewEvaluation).filter(
        InterviewEvaluation.result_id == result_id,
    ).all()

    # 3. Compute rating distribution
    categories = ["technical", "behavioral", "culture_fit", "experience_deep_dive"]
    rating_summary = {}
    for cat in categories:
        cat_evals = [e for e in evals if e.question_category == cat]
        rating_summary[cat] = {
            "strong": sum(1 for e in cat_evals if e.rating == "strong"),
            "adequate": sum(1 for e in cat_evals if e.rating == "adequate"),
            "weak": sum(1 for e in cat_evals if e.rating == "weak"),
            "total_rated": len([e for e in cat_evals if e.rating]),
        }

    # 4. Map recruiter's recommendation chip to advance/hold/reject
    RECOMMENDATION_MAP = {
        'strong_hire': 'advance',
        'lean_hire': 'advance',
        'no_decision': 'hold',
        'lean_no_hire': 'reject',
        'strong_no_hire': 'reject',
    }
    recruiter_recommendation_input = body.recommendation  # e.g. 'strong_hire'
    mapped_recommendation = RECOMMENDATION_MAP.get(recruiter_recommendation_input, None) if recruiter_recommendation_input else None

    # 5. Calculate recruiter score (40% rating distribution + 60% LLM sentiment)
    total_ratings = sum(r["total_rated"] for r in rating_summary.values())
    if total_ratings > 0:
        total_strong = sum(r["strong"] for r in rating_summary.values())
        total_adequate = sum(r["adequate"] for r in rating_summary.values())
        # Strong = 100, Adequate = 60, Weak = 20
        rating_score = ((total_strong * 100) + (total_adequate * 60) +
                        ((total_ratings - total_strong - total_adequate) * 20)) / total_ratings
    else:
        rating_score = 50  # neutral default

    # 5. Build LLM prompt
    candidate_name = parsed.get("contact_info", {}).get("name", "the candidate")
    role_title = analysis.get("jd_analysis", {}).get("role_title", "the role")
    fit_score = analysis.get("fit_score", "N/A")

    recruiter_rec_prompt_line = ""
    if recruiter_recommendation_input:
        recruiter_rec_prompt_line = f"\n## Recruiter's Recommendation: {recruiter_recommendation_input.replace('_', ' ').title()}"

    prompt = f"""You are a senior recruiting analyst. Based on the following data, generate a structured debrief of a phone screening call.

## Candidate: {candidate_name}
## Role: {role_title}
## AI Fit Score: {fit_score}%
{recruiter_rec_prompt_line}

## Rating Distribution from Phone Screen:
- Technical: {rating_summary['technical']}
- Behavioral: {rating_summary['behavioral']}
- Culture Fit: {rating_summary['culture_fit']}
- Experience Deep-Dive: {rating_summary['experience_deep_dive']}

## Recruiter's Conversation Summary:
{body.conversation_summary}

## Instructions:
Generate a JSON response with exactly this structure:
{{
  "overview": "2-3 sentence overview of the candidate's phone screen performance",
  "strengths": "Key strengths observed during the call (2-3 points)",
  "concerns": "Key concerns or gaps identified (2-3 points)",
  "recommendation_rationale": "Why you recommend the following action",
  "recommendation": "Advance" or "Hold" or "Reject",
  "sentiment_score": "<number 0-100 reflecting overall positive/negative sentiment of the recruiter's summary>"
}}

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation."""

    # 6. Call LLM (Gemini primary, Ollama fallback)

    debrief_data = None
    try:
        from app.backend.services.app_llm_client import generate_app_json

        debrief_data = await generate_app_json(
            prompt,
            max_output_tokens=1024,
            temperature=0.3,
            timeout=60.0,
            log_label="live_screen_debrief",
        )
    except Exception as e:
        logger.error("LLM debrief generation failed: %s", e)
        debrief_data = None

    # Fallback if LLM failed
    if debrief_data is None:
        # Derive recommendation from rating distribution
        if rating_score >= 70:
            fallback_rec = "advance"
            fallback_sentiment = 70
        elif rating_score >= 40:
            fallback_rec = "hold"
            fallback_sentiment = 50
        else:
            fallback_rec = "reject"
            fallback_sentiment = 30

        debrief_data = {
            "overview": f"Phone screen completed for {candidate_name} for {role_title}. AI-generated debrief unavailable; this summary is based on rating distribution only.",
            "strengths": "Refer to recruiter's conversation summary for observed strengths.",
            "concerns": "Refer to recruiter's conversation summary for identified concerns.",
            "recommendation_rationale": f"Recommendation based on rating distribution score ({int(rating_score)}/100). LLM analysis was not available.",
            "recommendation": fallback_rec,
            "sentiment_score": fallback_sentiment,
        }

    # 7. Compute final recruiter score
    sentiment_score = debrief_data.get("sentiment_score", 50)
    if isinstance(sentiment_score, str):
        try:
            sentiment_score = int(sentiment_score)
        except (ValueError, TypeError):
            sentiment_score = 50
    recruiter_score = int(rating_score * 0.4 + sentiment_score * 0.6)
    recruiter_score = max(0, min(100, recruiter_score))  # Clamp to 0-100
    recommendation = debrief_data.get("recommendation", "hold").lower().strip()
    if recommendation not in ("advance", "hold", "reject"):
        recommendation = "hold"

    # If recruiter selected a recommendation chip, prefer that over LLM-derived one
    if mapped_recommendation:
        recommendation = mapped_recommendation

    # 8. Store in OverallAssessment
    overall = db.query(OverallAssessment).filter(
        and_(
            OverallAssessment.result_id == result_id,
            OverallAssessment.user_id == current_user.id,
        )
    ).first()

    debrief_content = {
        "overview": debrief_data.get("overview", ""),
        "strengths": debrief_data.get("strengths", ""),
        "concerns": debrief_data.get("concerns", ""),
        "recommendation_rationale": debrief_data.get("recommendation_rationale", ""),
    }

    if overall:
        overall.debrief_json = json.dumps(debrief_content)
        overall.recruiter_score = recruiter_score
        overall.recruiter_recommendation = recommendation
        overall.overall_assessment = body.conversation_summary
        overall.updated_at = datetime.now(timezone.utc)
    else:
        overall = OverallAssessment(
            result_id=result_id,
            user_id=current_user.id,
            overall_assessment=body.conversation_summary,
            debrief_json=json.dumps(debrief_content),
            recruiter_score=recruiter_score,
            recruiter_recommendation=recommendation,
        )
        db.add(overall)

    from app.backend.services.consolidated_recommendation import (
        compute_consolidated_for_result,
        persist_outcome_to_screening_result,
    )

    analysis_score = analysis.get("fit_score") or result.deterministic_score
    outcome = compute_consolidated_for_result(
        db,
        result,
        analysis_score=analysis_score,
        call_score=recruiter_score,
        call_source="human",
        call_recommendation=recommendation,
        evidence=[debrief_content.get("recommendation_rationale", "")],
    )
    persist_outcome_to_screening_result(result, outcome, call_source="human")

    db.commit()

    try:
        from app.backend.services.webhook_service import dispatch_event_background
        from app.backend.db.database import SessionLocal
        dispatch_event_background(
            SessionLocal,
            result.tenant_id,
            "debrief.completed",
            {
                "result_id": result_id,
                "candidate_name": candidate_name,
                "role_title": role_title,
                "recommendation": recommendation,
                "recruiter_score": recruiter_score,
                "fit_score": fit_score,
                "summary": body.conversation_summary[:500],
            },
        )
    except Exception:
        pass

    return DebriefResponse(
        debrief=DebriefContent(**debrief_content),
        recruiter_score=recruiter_score,
        recommendation=recommendation.capitalize(),
    )


@router.post("/{result_id}/score-feedback")
def submit_score_feedback(
    result_id: int,
    body: ScoreFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter_or_admin),
):
    """Store recruiter feedback on AI fit score accuracy for role-level calibration."""
    result = _verify_result_access(result_id, current_user, db)
    try:
        analysis = json.loads(result.analysis_result) if result.analysis_result else {}
    except (json.JSONDecodeError, TypeError):
        analysis = {}

    analysis["score_feedback"] = {
        "sentiment": body.sentiment,
        "fit_score": analysis.get("fit_score") or result.deterministic_score,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "user_id": current_user.id,
    }
    result.analysis_result = json.dumps(analysis)
    db.commit()
    return {"ok": True, "sentiment": body.sentiment}
