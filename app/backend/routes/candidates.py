"""
Candidate management routes.

New endpoints vs original:
  POST /{candidate_id}/analyze-jd   — re-analyze existing candidate against a new JD
                                       (no file upload — uses stored profile)

Enriched responses:
  GET  ""                — now returns current_role, total_years_exp
  GET  "/{id}"           — now returns full profile fields + skills_snapshot
"""
import json
import logging
from datetime import datetime, date, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import Candidate, ScreeningResult, User
from app.backend.models.schemas import CandidateNameUpdate, AnalyzeJdRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


@router.get("")
def list_candidates(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Candidate).filter(Candidate.tenant_id == current_user.tenant_id)
    if search:
        q = f"%{search}%"
        query = query.filter(
            (Candidate.name.ilike(q)) | (Candidate.email.ilike(q))
        )

    total      = query.count()
    candidates = (
        query.order_by(Candidate.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Fetch all screening results for these candidates in a single query
    candidate_ids = [c.id for c in candidates]
    results_map = {}
    if candidate_ids:
        all_results = (
            db.query(ScreeningResult)
            .filter(ScreeningResult.candidate_id.in_(candidate_ids))
            .order_by(ScreeningResult.timestamp.desc())
            .all()
        )
        for r in all_results:
            if r.candidate_id not in results_map:
                results_map[r.candidate_id] = []
            results_map[r.candidate_id].append(r)

    result = []
    for c in candidates:
        candidate_results = results_map.get(c.id, [])
        result_count = len(candidate_results)
        best = candidate_results[0] if candidate_results else None
        best_score = None
        if best:
            try:
                best_score = json.loads(best.analysis_result).get("fit_score")
            except Exception as e:
                logger.warning("Non-critical: Failed to parse best analysis result: %s", e)

        result.append({
            "id":              c.id,
            "name":            c.name,
            "email":           c.email,
            "phone":           c.phone,
            "created_at":      c.created_at,
            "result_count":    result_count,
            "best_score":      best_score,
            # Enriched profile fields
            "current_role":    c.current_role,
            "current_company": c.current_company,
            "total_years_exp": c.total_years_exp,
            "profile_quality": c.profile_quality,
        })

    return {"candidates": result, "total": total, "page": page, "page_size": page_size}


@router.patch("/{candidate_id}")
def update_candidate(
    candidate_id: int,
    body: CandidateNameUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == current_user.tenant_id,
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate.name = body.name
    db.commit()
    db.refresh(candidate)
    return {"id": candidate.id, "name": candidate.name}


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == current_user.tenant_id,
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    results = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.candidate_id == candidate_id)
        .order_by(ScreeningResult.timestamp.desc())
        .all()
    )

    history = []
    for r in results:
        try:
            analysis = json.loads(r.analysis_result)
        except Exception as e:
            logger.warning("Non-critical: Failed to parse analysis result for result %s: %s", r.id, e)
            analysis = {}
        history.append({
            "id":                   r.id,
            "timestamp":            r.timestamp,
            "status":               r.status,
            "fit_score":            analysis.get("fit_score"),
            "final_recommendation": analysis.get("final_recommendation"),
            "risk_level":           analysis.get("risk_level"),
            "score_breakdown":      analysis.get("score_breakdown", {}),
            "matched_skills":       analysis.get("matched_skills", []),
            "missing_skills":       analysis.get("missing_skills", []),
            "job_role":             analysis.get("job_role"),
            "analysis_quality":     analysis.get("analysis_quality"),
        })

    # Skills snapshot from stored profile
    skills_snapshot = []
    if candidate.parsed_skills:
        try:
            skills_snapshot = json.loads(candidate.parsed_skills)[:15]
        except Exception as e:
            logger.warning("Non-critical: Failed to parse parsed_skills: %s", e)

    contact_info: dict = {}
    if getattr(candidate, "parser_snapshot_json", None):
        try:
            snap = json.loads(candidate.parser_snapshot_json)
            contact_info = dict(snap.get("contact_info") or {})
        except Exception as e:
            logger.warning("Non-critical: Failed to parse parser_snapshot_json: %s", e)
            contact_info = {}
    if not contact_info:
        contact_info = {
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
        }
    else:
        # Recruiter-edited columns win over stale snapshot
        if candidate.name:
            contact_info["name"] = candidate.name
        if candidate.email is not None:
            contact_info["email"] = candidate.email
        if candidate.phone is not None:
            contact_info["phone"] = candidate.phone

    return {
        "id":                candidate.id,
        "name":              candidate.name,
        "email":             candidate.email,
        "phone":             candidate.phone,
        "contact_info":      contact_info,
        "created_at":        candidate.created_at,
        "profile_updated_at": candidate.profile_updated_at,
        # Enriched profile
        "current_role":      candidate.current_role,
        "current_company":   candidate.current_company,
        "total_years_exp":   candidate.total_years_exp,
        "profile_quality":   candidate.profile_quality,
        "skills_snapshot":   skills_snapshot,
        "has_stored_profile": bool(candidate.raw_resume_text),
        "has_full_parser_snapshot": bool(getattr(candidate, "parser_snapshot_json", None)),
        "history":           history,
    }


@router.post("/{candidate_id}/analyze-jd")
async def analyze_existing_candidate(
    candidate_id: int,
    body: AnalyzeJdRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Re-analyze an existing candidate against a new Job Description.

    No file upload required — the candidate's parsed profile (skills, education,
    work experience, gap analysis) is loaded from the database. Only the hybrid
    scoring phase runs, making this ~3× faster than a full re-upload analysis.
    """
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == current_user.tenant_id,
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if not candidate.raw_resume_text:
        raise HTTPException(
            status_code=422,
            detail=(
                "This candidate does not have a stored profile yet. "
                "Please re-upload their resume to generate a profile before using this endpoint."
            ),
        )

    if len(body.job_description.split()) < 80:
        raise HTTPException(
            status_code=400,
            detail="Job description is too brief (under 80 words). Please provide more detail.",
        )

    # Prefer full parser snapshot (all fields); else reconstruct from denormalized columns
    if getattr(candidate, "parser_snapshot_json", None):
        try:
            parsed_data = json.loads(candidate.parser_snapshot_json)
            if not isinstance(parsed_data, dict):
                raise ValueError("snapshot not an object")
            ci = parsed_data.setdefault("contact_info", {})
            if candidate.name:
                ci["name"] = candidate.name
            if candidate.email is not None:
                ci["email"] = candidate.email
            if candidate.phone is not None:
                ci["phone"] = candidate.phone
            if not parsed_data.get("raw_text") and candidate.raw_resume_text:
                parsed_data["raw_text"] = candidate.raw_resume_text
        except Exception as e:
            logger.warning("Non-critical: Failed to parse parser_snapshot_json for candidate %s: %s", candidate.id, e)
            parsed_data = {
                "raw_text":       candidate.raw_resume_text,
                "skills":         json.loads(candidate.parsed_skills   or "[]"),
                "education":      json.loads(candidate.parsed_education or "[]"),
                "work_experience": json.loads(candidate.parsed_work_exp or "[]"),
                "contact_info":   {
                    "name":  candidate.name,
                    "email": candidate.email,
                    "phone": candidate.phone,
                },
            }
    else:
        parsed_data = {
            "raw_text":       candidate.raw_resume_text,
            "skills":         json.loads(candidate.parsed_skills   or "[]"),
            "education":      json.loads(candidate.parsed_education or "[]"),
            "work_experience": json.loads(candidate.parsed_work_exp or "[]"),
            "contact_info":   {
                "name":  candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
            },
        }
    gap_analysis = json.loads(candidate.gap_analysis_json or "{}")

    # Use DB JD cache
    from app.backend.routes.analyze import _get_or_cache_jd
    jd_analysis = _get_or_cache_jd(db, body.job_description)

    from app.backend.services.hybrid_pipeline import run_hybrid_pipeline
    try:
        result = await run_hybrid_pipeline(
            resume_text=candidate.raw_resume_text,
            job_description=body.job_description,
            parsed_data=parsed_data,
            gap_analysis=gap_analysis,
            scoring_weights=body.scoring_weights,
            jd_analysis=jd_analysis,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    # Persist result
    db_result = ScreeningResult(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        resume_text=candidate.raw_resume_text,
        jd_text=body.job_description,
        parsed_data=json.dumps(parsed_data, default=_json_default),
        analysis_result=json.dumps(result, default=_json_default),
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    result["result_id"]      = db_result.id
    result["candidate_id"]   = candidate_id
    result["candidate_name"] = candidate.name
    return result
