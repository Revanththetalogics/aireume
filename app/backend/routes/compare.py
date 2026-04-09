"""
Candidate comparison endpoint — compare up to 5 screening results side-by-side.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User
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
        analysis = json.loads(r.analysis_result)
        parsed   = json.loads(r.parsed_data)
        comparison.append({
            "id":                   r.id,
            "timestamp":            r.timestamp,
            "status":               r.status,
            "candidate_id":         r.candidate_id,
            "fit_score":            analysis.get("fit_score", 0),
            "final_recommendation": analysis.get("final_recommendation", ""),
            "risk_level":           analysis.get("risk_level", ""),
            "matched_skills":       analysis.get("matched_skills", []),
            "missing_skills":       analysis.get("missing_skills", []),
            "score_breakdown":      analysis.get("score_breakdown", {}),
            "strengths":            analysis.get("strengths", [])[:3],  # top 3 strengths
            "weaknesses":           analysis.get("weaknesses", [])[:3],  # top 3 weaknesses
            "education_analysis":   analysis.get("education_analysis", ""),
            "candidate_name":       parsed.get("contact_info", {}).get("name", f"Candidate {r.id}"),
            # Enhanced comparison fields
            "employment_gaps":      len(analysis.get("employment_gaps", [])),  # gap count
            "interview_questions_preview": (
                analysis.get("interview_questions", {}).get("technical", [])[:2]
            ),  # first 2 technical questions
            "analysis_quality":     analysis.get("analysis_quality", "medium"),
            "adjacent_skills":      analysis.get("adjacent_skills", [])[:5],  # top 5
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
