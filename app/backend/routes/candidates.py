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
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import Candidate, ScreeningResult, User, RoleTemplate
from app.backend.models.schemas import CandidateNameUpdate, AnalyzeJdRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/candidates", tags=["candidates"])

# Separate router for JD-scoped candidate endpoints (paths live under /api/jd/)
jd_router = APIRouter(prefix="/api/jd", tags=["jd-candidates"])

# Allowed statuses for bulk shortlist updates
_VALID_STATUSES = {"pending", "shortlisted", "rejected", "in-review", "hired"}


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
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate status filter early
    if status and status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    # When status filter is active, we must join through ScreeningResult to find
    # candidates that have at least one result with that status.
    if status:
        candidate_ids_with_status = (
            db.query(ScreeningResult.candidate_id)
            .filter(
                ScreeningResult.tenant_id == current_user.tenant_id,
                ScreeningResult.status == status,
            )
            .distinct()
            .subquery()
        )
        query = db.query(Candidate).filter(
            Candidate.tenant_id == current_user.tenant_id,
            Candidate.id.in_(candidate_ids_with_status),
        )
    else:
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
        
        # Find the result with the highest fit_score and the latest status
        best_score = None
        latest_status = "pending"
        latest_result_id = None
        if candidate_results:
            try:
                scores = []
                for r in candidate_results:
                    analysis = json.loads(r.analysis_result)
                    fit_score = analysis.get("fit_score")
                    if fit_score is not None:
                        scores.append(fit_score)
                
                if scores:
                    best_score = max(scores)
            except Exception as e:
                logger.warning("Non-critical: Failed to parse analysis results for best_score: %s", e)

            # Latest result (first in desc-ordered list) provides the status
            latest = candidate_results[0]
            latest_status = latest.status or "pending"
            latest_result_id = latest.id

        result.append({
            "id":              c.id,
            "name":            c.name,
            "email":           c.email,
            "phone":           c.phone,
            "created_at":      c.created_at,
            "result_count":    result_count,
            "best_score":      best_score,
            "latest_status":   latest_status,
            "latest_result_id": latest_result_id,
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
            logger.warning("Non-critical: Failed to parse analysis_result for result %s: %s", r.id, e)
            analysis = {}

        # Log when analysis_result is empty or missing critical fields
        if not analysis or analysis.get("fit_score") is None:
            logger.warning(
                "analysis_result for screening_result_id=%s is empty or missing fit_score "
                "(has %d keys, fit_score=%s). Will reconstruct from parsed_data.",
                r.id, len(analysis), analysis.get("fit_score"),
            )

        # Parse and merge narrative_json if available
        narrative_data = {}
        if r.narrative_json:
            try:
                narrative_data = json.loads(r.narrative_json)
            except Exception as e:
                logger.warning("Non-critical: Failed to parse narrative_json for result %s: %s", r.id, e)

        # Parse parsed_data as fallback source for missing analysis_result fields
        # parsed_data is always saved correctly (not a placeholder like analysis_result can be)
        parsed = {}
        if r.parsed_data:
            try:
                parsed = json.loads(r.parsed_data)
            except Exception as e:
                logger.warning("Non-critical: Failed to parse parsed_data for result %s: %s", r.id, e)

        # Merge narrative data with analysis - narrative fields take precedence
        # but only for narrative-specific fields (strengths, weaknesses, etc.)
        # Preserve analysis fields like fit_score, final_recommendation
        merged_data = dict(analysis)
        if narrative_data:
            # Only merge narrative-specific fields, not core analysis fields
            narrative_fields = {
                "ai_enhanced", "fit_summary", "strengths", "concerns", "weaknesses",
                "recommendation_rationale", "explainability", "interview_questions"
            }
            for field in narrative_fields:
                if field in narrative_data:
                    merged_data[field] = narrative_data[field]

        # ── Ensure key fields exist with fallback to parsed_data ──────────────
        # When analysis_result is empty/incomplete (e.g., DB save failed during SSE
        # streaming), reconstruct essential fields from parsed_data and other DB
        # columns so the Candidates page report matches the post-analysis report.

        if not merged_data.get("contact_info"):
            merged_data["contact_info"] = parsed.get("contact_info") or {
                "name": candidate.name,
                "email": candidate.email,
                "phone": candidate.phone,
            }

        if not merged_data.get("candidate_profile"):
            # Reconstruct candidate_profile from parsed_data
            work_exp = parsed.get("work_experience", [])
            contact = parsed.get("contact_info", {})
            merged_data["candidate_profile"] = {
                "name": contact.get("name", ""),
                "email": contact.get("email", ""),
                "phone": contact.get("phone", ""),
                "skills_identified": parsed.get("skills", []),
                "education": parsed.get("education", []),
                "work_experience": work_exp,
                "career_summary": "",
                "total_effective_years": candidate.total_years_exp or 0,
                "current_role": work_exp[0].get("title", "") if work_exp else (candidate.current_role or ""),
                "current_company": work_exp[0].get("company", "") if work_exp else (candidate.current_company or ""),
            }

        if not merged_data.get("work_experience"):
            merged_data["work_experience"] = parsed.get("work_experience", [])

        # Ensure all fields expected by ReportPage / ResultCard have defaults
        merged_data.setdefault("fit_score", None)
        merged_data.setdefault("job_role", None)
        merged_data.setdefault("final_recommendation", "Pending")
        merged_data.setdefault("risk_level", None)
        merged_data.setdefault("score_breakdown", {})
        merged_data.setdefault("strengths", [])
        merged_data.setdefault("weaknesses", [])
        merged_data.setdefault("concerns", [])
        merged_data.setdefault("risk_signals", [])
        merged_data.setdefault("employment_gaps", [])
        merged_data.setdefault("skill_analysis", {})
        merged_data.setdefault("jd_analysis", {})
        merged_data.setdefault("edu_timeline_analysis", {})
        merged_data.setdefault("education_analysis", None)
        merged_data.setdefault("matched_skills", [])
        merged_data.setdefault("missing_skills", [])
        merged_data.setdefault("adjacent_skills", [])
        merged_data.setdefault("required_skills_count", 0)
        merged_data.setdefault("analysis_quality", "low")
        merged_data.setdefault("pipeline_errors", [])
        merged_data.setdefault("score_rationales", {})
        merged_data.setdefault("risk_summary", {})
        merged_data.setdefault("skill_depth", {})
        # Include the ScreeningResult status (pending/shortlisted/rejected/in-review/hired)
        merged_data.setdefault("status", r.status or "pending")
        # narrative_pending and ai_enhanced are computed from narrative_status below,
        # NOT from analysis_result (which may contain stale values)
        merged_data.pop("narrative_pending", None)
        merged_data.pop("ai_enhanced", None)

        # Resolve candidate name: candidate.name takes priority (may have been edited by recruiter)
        candidate_name = (
            (candidate.name or "").strip() or
            (merged_data.get("candidate_name") or "").strip() or
            (merged_data.get("contact_info", {}).get("name") or "").strip() or
            (merged_data.get("candidate_profile", {}).get("name") or "").strip() or
            None
        )

        # Build result with EXACT same structure as analysis result
        # This ensures ReportPage receives consistent data regardless of source
        result_item = {
            # IDs and metadata (minimal additions for UI)
            "id":                   r.id,
            "result_id":            r.id,
            "analysis_id":          r.id,  # For narrative polling
            "timestamp":            r.timestamp,
            "candidate_id":         r.candidate_id,
            "candidate_name":       candidate_name,

            # Narrative status fields (for UI polling)
            "narrative_status":     r.narrative_status or "pending",
            "narrative_error":      r.narrative_error,
            "ai_enhanced":          r.narrative_status == "ready" and r.narrative_json is not None,
            "narrative_pending":    r.narrative_status in ("pending", "processing"),
        }

        # Spread all analysis data - this ensures EXACT same structure as direct analysis
        # merged_data contains: fit_score, final_recommendation, candidate_profile,
        # contact_info, strengths, weaknesses, etc.
        result_item.update(merged_data)

        # Re-apply resolved candidate_name: merged_data.update() above may overwrite
        # candidate_name with the stale parsed value; the recruiter-edited candidate.name
        # must always win.
        result_item["candidate_name"] = candidate_name

        history.append(result_item)

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

    # ── Version Management ────────────────────────────────────────────────────
    # When re-analyzing with potentially different weights, create a new version
    # and archive the old one (Option C: Hybrid versioning approach)
    
    # Find current active version for this candidate (if any)
    current_version = db.query(ScreeningResult).filter(
        ScreeningResult.candidate_id == candidate_id,
        ScreeningResult.is_active == True,
    ).first()
    
    # Determine next version number
    max_version = db.query(ScreeningResult).filter(
        ScreeningResult.candidate_id == candidate_id
    ).count()
    next_version = max_version + 1
    
    # Archive current active version
    if current_version:
        current_version.is_active = False
        logger.info(f"Archived version {current_version.version_number} for candidate {candidate_id}")
    
    # Extract weight metadata from JD analysis
    weight_suggestion = jd_analysis.get("weight_suggestion")
    role_category = None
    weight_reasoning = None
    suggested_weights_json = None
    
    if weight_suggestion:
        role_category = weight_suggestion.get("role_category")
        weight_reasoning = weight_suggestion.get("reasoning")
        suggested_weights_json = json.dumps(weight_suggestion.get("suggested_weights", {}), default=_json_default)
    
    # Create new version as active
    db_result = ScreeningResult(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        resume_text=candidate.raw_resume_text,
        jd_text=body.job_description,
        parsed_data=json.dumps(parsed_data, default=_json_default),
        analysis_result=json.dumps(result, default=_json_default),
        is_active=True,
        version_number=next_version,
        role_category=role_category,
        weight_reasoning=weight_reasoning,
        suggested_weights_json=suggested_weights_json,
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    
    logger.info(f"Created version {next_version} for candidate {candidate_id} (now active)")

    result["result_id"]      = db_result.id
    result["candidate_id"]   = candidate_id
    result["candidate_name"] = candidate.name
    return result


@router.get("/{candidate_id}/resume")
def download_candidate_resume(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download or view the original uploaded resume file.
    PDFs are served inline for browser preview; DOCX/DOC/ODT force download.
    """
    candidate = db.query(Candidate).filter(
        Candidate.id == candidate_id,
        Candidate.tenant_id == current_user.tenant_id,
    ).first()

    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if not candidate.resume_file_data:
        raise HTTPException(
            status_code=404,
            detail="Resume file not stored for this candidate. Re-upload to enable download.",
        )

    filename = candidate.resume_filename or f"resume_{candidate_id}"
    lower_name = filename.lower()

    # Determine MIME type
    if lower_name.endswith(".pdf"):
        media_type = "application/pdf"
        disposition = "inline"  # Open in browser
    elif lower_name.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        disposition = f'attachment; filename="{filename}"'
    elif lower_name.endswith(".doc"):
        media_type = "application/msword"
        disposition = f'attachment; filename="{filename}"'
    elif lower_name.endswith(".odt"):
        media_type = "application/vnd.oasis.opendocument.text"
        disposition = f'attachment; filename="{filename}"'
    elif lower_name.endswith(".txt"):
        media_type = "text/plain"
        disposition = f'attachment; filename="{filename}"'
    elif lower_name.endswith(".rtf"):
        media_type = "application/rtf"
        disposition = f'attachment; filename="{filename}"'
    else:
        media_type = "application/octet-stream"
        disposition = f'attachment; filename="{filename}"'

    return Response(
        content=candidate.resume_file_data,
        media_type=media_type,
        headers={"Content-Disposition": disposition},
    )


# ─── JD-scoped candidate ranking & bulk shortlist ─────────────────────────────


@jd_router.get("/{jd_id}/candidates")
def get_jd_candidates(
    jd_id: int,
    status: Optional[str] = Query(None),
    sort_by: str = Query("fit_score"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all candidates screened against a specific JD, sorted and filtered.

    Joins ScreeningResult → Candidate so we can return name, email, and profile
    fields alongside the per-JD analysis data (fit_score, matched/missing skills, …).
    """
    # ── Verify JD exists and belongs to tenant ──────────────────────────────
    jd = db.query(RoleTemplate).filter(
        RoleTemplate.id == jd_id,
        RoleTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    # ── Build base query ────────────────────────────────────────────────────
    query = (
        db.query(ScreeningResult, Candidate)
        .join(Candidate, ScreeningResult.candidate_id == Candidate.id)
        .filter(
            ScreeningResult.role_template_id == jd_id,
            ScreeningResult.is_active == True,
            ScreeningResult.tenant_id == current_user.tenant_id,
        )
    )

    # Optional status filter
    if status:
        query = query.filter(ScreeningResult.status == status)

    rows = query.all()

    # ── Build candidate list ────────────────────────────────────────────────
    candidates = []
    for sr, cand in rows:
        analysis = {}
        try:
            analysis = json.loads(sr.analysis_result) if sr.analysis_result else {}
        except Exception as e:
            logger.warning("Failed to parse analysis_result for result %s: %s", sr.id, e)

        # Prefer deterministic_score when available; fall back to analysis_result
        fit_score = sr.deterministic_score
        if fit_score is None:
            fit_score = analysis.get("fit_score")

        candidates.append({
            "candidate_id":    cand.id,
            "result_id":       sr.id,
            "name":            cand.name,
            "email":           cand.email,
            "fit_score":       fit_score,
            "status":          sr.status or "pending",
            "recommendation":  analysis.get("final_recommendation", "Pending"),
            "matched_skills":  analysis.get("matched_skills", []),
            "missing_skills":  analysis.get("missing_skills", []),
            "total_years_exp": cand.total_years_exp,
            "current_role":    cand.current_role,
            "analyzed_at":     sr.timestamp,
        })

    # ── Sort ────────────────────────────────────────────────────────────────
    reverse = sort_order.lower() == "desc"

    if sort_by == "fit_score":
        candidates.sort(
            key=lambda c: (c["fit_score"] is None, c["fit_score"] or 0),
            reverse=reverse,
        )
    elif sort_by == "name":
        candidates.sort(
            key=lambda c: (c["name"] or "").lower(),
            reverse=reverse,
        )
    elif sort_by == "date":
        candidates.sort(
            key=lambda c: c["analyzed_at"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=reverse,
        )

    return {
        "jd_id":   jd_id,
        "jd_name": jd.name,
        "candidates": candidates,
        "total": len(candidates),
    }


@jd_router.post("/{jd_id}/shortlist")
def bulk_update_status(
    jd_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bulk-update the status of multiple ScreeningResults for a given JD.

    Body: {"result_ids": [1, 2, 3], "status": "shortlisted"}
    Valid statuses: pending, shortlisted, rejected, in-review, hired
    """
    result_ids = body.get("result_ids")
    new_status = body.get("status")

    # ── Validate payload ────────────────────────────────────────────────────
    if not isinstance(result_ids, list) or not result_ids:
        raise HTTPException(status_code=422, detail="result_ids must be a non-empty list")
    if not all(isinstance(rid, int) for rid in result_ids):
        raise HTTPException(status_code=422, detail="All result_ids must be integers")
    if not new_status or not isinstance(new_status, str):
        raise HTTPException(status_code=422, detail="status must be a non-empty string")
    if new_status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
        )

    # ── Verify JD belongs to tenant ─────────────────────────────────────────
    jd = db.query(RoleTemplate).filter(
        RoleTemplate.id == jd_id,
        RoleTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    # ── Bulk update ─────────────────────────────────────────────────────────
    updated = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.id.in_(result_ids),
            ScreeningResult.tenant_id == current_user.tenant_id,
            ScreeningResult.role_template_id == jd_id,
        )
        .update({ScreeningResult.status: new_status}, synchronize_session="fetch")
    )
    db.commit()

    return {"updated": updated}


@jd_router.get("/{jd_id}/stats")
def get_jd_stats(
    jd_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return candidate statistics for a specific JD."""
    # Verify JD belongs to tenant
    jd = db.query(RoleTemplate).filter(
        RoleTemplate.id == jd_id,
        RoleTemplate.tenant_id == current_user.tenant_id
    ).first()
    if not jd:
        raise HTTPException(404, "JD not found")

    # Count results by status
    results = db.query(ScreeningResult).filter(
        ScreeningResult.role_template_id == jd_id,
        ScreeningResult.tenant_id == current_user.tenant_id,
        ScreeningResult.is_active == True,
    ).all()

    by_status = {}
    total = 0
    score_sum = 0
    score_count = 0
    for r in results:
        total += 1
        status = r.status or "pending"
        by_status[status] = by_status.get(status, 0) + 1
        if r.deterministic_score is not None:
            score_sum += r.deterministic_score
            score_count += 1

    return {
        "total": total,
        "by_status": by_status,
        "avg_fit_score": round(score_sum / score_count, 1) if score_count > 0 else None
    }


@jd_router.get("/stats/batch")
def get_all_jd_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return candidate stats for all JDs belonging to tenant."""
    results = db.query(
        ScreeningResult.role_template_id,
        ScreeningResult.status,
        ScreeningResult.deterministic_score
    ).filter(
        ScreeningResult.tenant_id == current_user.tenant_id,
        ScreeningResult.is_active == True,
        ScreeningResult.role_template_id.isnot(None)
    ).all()

    stats = {}
    for r in results:
        jd_id = r.role_template_id
        if jd_id not in stats:
            stats[jd_id] = {"total": 0, "by_status": {}, "scores": []}
        stats[jd_id]["total"] += 1
        status = r.status or "pending"
        stats[jd_id]["by_status"][status] = stats[jd_id]["by_status"].get(status, 0) + 1
        if r.deterministic_score is not None:
            stats[jd_id]["scores"].append(r.deterministic_score)

    result = {}
    for jd_id, s in stats.items():
        result[str(jd_id)] = {
            "total": s["total"],
            "by_status": s["by_status"],
            "avg_fit_score": round(sum(s["scores"]) / len(s["scores"]), 1) if s["scores"] else None
        }
    return result
