"""
Candidate comparison endpoint — compare up to 5 screening results side-by-side.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User, Candidate
from app.backend.models.schemas import CompareRequest

router = APIRouter(prefix="/api", tags=["compare"])


@router.post("/compare")
def compare_candidates(
    body: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if len(body.candidate_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 candidate IDs required")
    if len(body.candidate_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 candidates per comparison")

    results = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.id.in_(body.candidate_ids),
            ScreeningResult.tenant_id == current_user.tenant_id
        )
        .all()
    )

    if len(results) < 2:
        raise HTTPException(status_code=404, detail="Not enough results found")

    comparison = []
    for r in results:
        def _safe_loads(data, field="data"):
            try:
                return json.loads(data) if data else {}
            except (json.JSONDecodeError, TypeError):
                logging.warning("Malformed JSON in %s for result id=%s", field, r.id)
                return {}

        analysis = _safe_loads(r.analysis_result, "analysis_result")
        parsed   = _safe_loads(r.parsed_data, "parsed_data")

        # Fetch Candidate record once for fallback lookups
        candidate = None
        if r.candidate_id:
            candidate = db.get(Candidate, r.candidate_id)

        # Resolve candidate name from multiple sources
        candidate_name = (
            (analysis.get("candidate_name") or "").strip() or
            (parsed.get("contact_info", {}).get("name") or "").strip() or
            (parsed.get("candidate_profile", {}).get("name") or "").strip() or
            (candidate.name if candidate and candidate.name else "")
        )

        # Final fallback
        if not candidate_name:
            candidate_name = f"Result #{r.id}"

        # Determine effective data source: prefer analysis, fallback to parsed
        # Check if analysis has essential fields; if not, use parsed_data as base
        has_analysis_data = bool(
            analysis.get("fit_score") is not None or
            analysis.get("score_breakdown")
        )

        # Get work_experience from parsed for profile fallback
        work_exp = parsed.get("work_experience", [])

        # Fallback for score fields: use analysis if present, otherwise 0/empty defaults
        fit_score = analysis.get("fit_score") if analysis.get("fit_score") is not None else 0
        score_breakdown = analysis.get("score_breakdown") or {}

        # Ensure score_breakdown has all expected keys with defaults
        if not isinstance(score_breakdown, dict):
            score_breakdown = {}
        score_breakdown.setdefault("skill_match", 0)
        score_breakdown.setdefault("experience_match", 0)
        score_breakdown.setdefault("education", 0)
        score_breakdown.setdefault("stability", 0)

        # Fallback for candidate_profile fields from Candidate table
        current_role = ""
        current_company = ""
        total_years_exp = 0

        if analysis.get("candidate_profile"):
            current_role = analysis["candidate_profile"].get("current_role", "")
            current_company = analysis["candidate_profile"].get("current_company", "")
            total_years_exp = analysis["candidate_profile"].get("total_effective_years", 0)

        # If still missing, fallback to parsed_data work_experience or Candidate table
        if not current_role:
            current_role = work_exp[0].get("title", "") if work_exp else (candidate.current_role if candidate and candidate.current_role else "")
        if not current_company:
            current_company = work_exp[0].get("company", "") if work_exp else (candidate.current_company if candidate and candidate.current_company else "")
        if not total_years_exp:
            total_years_exp = candidate.total_years_exp if candidate and candidate.total_years_exp else 0

        # Safe extraction of interview questions preview
        interview_questions = analysis.get("interview_questions") or {}
        if not isinstance(interview_questions, dict):
            interview_questions = {}
        technical_questions = interview_questions.get("technical", []) if isinstance(interview_questions.get("technical"), list) else []

        # Extract narrative fields for richer comparison
        fit_summary = analysis.get("fit_summary", "") or ""
        recommendation_rationale = analysis.get("recommendation_rationale", "") or ""
        dealbreakers = (analysis.get("dealbreakers", []) if isinstance(analysis.get("dealbreakers"), list) else [])[:3]
        differentiators = (analysis.get("differentiators", []) if isinstance(analysis.get("differentiators"), list) else [])[:3]
        hiring_decision = analysis.get("hiring_decision", {}) or {}

        comparison.append({
            "id":                   r.id,
            "timestamp":            r.timestamp,
            "status":               r.status,
            "candidate_id":         r.candidate_id,
            "fit_score":            fit_score,
            "final_recommendation": analysis.get("final_recommendation", ""),
            "risk_level":           analysis.get("risk_level", ""),
            "matched_skills":       analysis.get("matched_skills", []) if has_analysis_data else (parsed.get("skills", []) or []),
            "missing_skills":       analysis.get("missing_skills", []) if has_analysis_data else [],
            "score_breakdown":      score_breakdown,
            "strengths":            (analysis.get("strengths", []) if isinstance(analysis.get("strengths"), list) else [])[:3],
            "weaknesses":           (analysis.get("weaknesses", []) if isinstance(analysis.get("weaknesses"), list) else [])[:3],
            "education_analysis":   analysis.get("education_analysis", ""),
            "candidate_name":       candidate_name,
            # Enhanced comparison fields
            "employment_gaps":      len(analysis.get("employment_gaps", [])) if isinstance(analysis.get("employment_gaps"), list) else 0,
            "interview_questions_preview": technical_questions[:2],
            "analysis_quality":     analysis.get("analysis_quality", "medium"),
            "adjacent_skills":      (analysis.get("adjacent_skills", []) if isinstance(analysis.get("adjacent_skills"), list) else [])[:5],
            # Additional profile fields for richer comparison
            "current_role":         current_role,
            "current_company":      current_company,
            "total_years_exp":      total_years_exp,
            # NEW: Narrative quality fields for head-to-head comparison
            "fit_summary":          fit_summary,
            "recommendation_rationale": recommendation_rationale,
            "dealbreakers":         dealbreakers,
            "differentiators":      differentiators,
            "hiring_decision":      {
                "verdict": hiring_decision.get("verdict", "") if isinstance(hiring_decision, dict) else "",
                "confidence": hiring_decision.get("confidence", 0.0) if isinstance(hiring_decision, dict) else 0.0,
                "action_items": (hiring_decision.get("action_items", []) if isinstance(hiring_decision, dict) else [])[:2],
            },
        })

    # Determine category winners
    if comparison:
        max_fit      = max(c["fit_score"] for c in comparison)
        max_skill    = max(c["score_breakdown"].get("skill_match", 0) for c in comparison)
        max_exp      = max(c["score_breakdown"].get("experience_match", 0) for c in comparison)
        max_edu      = max(c["score_breakdown"].get("education", 0) for c in comparison)
        max_stability= max(c["score_breakdown"].get("stability", 0) for c in comparison)

        for c in comparison:
            c["winners"] = {
                "overall":    c["fit_score"] == max_fit,
                "skills":     c["score_breakdown"].get("skill_match", 0) == max_skill,
                "experience": c["score_breakdown"].get("experience_match", 0) == max_exp,
                "education":  c["score_breakdown"].get("education", 0) == max_edu,
                "stability":  c["score_breakdown"].get("stability", 0) == max_stability,
            }

    return {"candidates": comparison, "total": len(comparison)}
