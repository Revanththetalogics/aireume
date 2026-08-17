"""JD-scoped candidate ranking, shortlist, skill tags, and stats."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.backend.db.database import get_db, SessionLocal
from app.backend.middleware.auth import get_current_user
from app.backend.middleware.rbac import require_recruiter_or_admin
from app.backend.models.db_models import Candidate, ScreeningResult, User, RoleTemplate
from app.backend.services.recruiter.auto_trigger import RecruiterAutoTrigger
from app.backend.services.screening_outcome import outcome_fields_from_result

logger = logging.getLogger(__name__)

jd_router = APIRouter(prefix="/api/jd", tags=["jd-candidates"])

# Allowed statuses for bulk shortlist updates
_VALID_STATUSES = {"pending", "shortlisted", "rejected", "in-review", "hired"}


async def _schedule_auto_trigger(
    tenant_id: int,
    candidate_id: int,
    screening_result_id: int,
    new_status: str,
) -> None:
    """Fire-and-forget auto-trigger evaluation using a fresh DB session."""
    db = SessionLocal()
    try:
        trigger = RecruiterAutoTrigger(db)
        await trigger.evaluate_trigger(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            screening_result_id=screening_result_id,
            new_status=new_status,
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, OSError, RuntimeError, SQLAlchemyError) as e:
        logger.warning(
            "Auto-trigger evaluation failed: %s", e,
            extra={"error_code": "DB_ERROR" if isinstance(e, SQLAlchemyError) else "VALIDATION_ERROR"},
        )
    finally:
        db.close()


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

    # ── Deduplicate: keep only the latest ScreeningResult per candidate ──────
    # (a candidate may have been analysed multiple times against the same JD)
    latest_by_candidate: dict = {}
    for sr, cand in rows:
        existing = latest_by_candidate.get(cand.id)
        if existing is None:
            latest_by_candidate[cand.id] = (sr, cand)
        else:
            existing_sr, _ = existing
            existing_ts = existing_sr.timestamp or datetime.min.replace(tzinfo=timezone.utc)
            new_ts = sr.timestamp or datetime.min.replace(tzinfo=timezone.utc)
            if new_ts > existing_ts or (new_ts == existing_ts and sr.id > existing_sr.id):
                latest_by_candidate[cand.id] = (sr, cand)

    # ── Build candidate list ────────────────────────────────────────────────
    candidates = []
    for sr, cand in latest_by_candidate.values():
        analysis = {}
        try:
            analysis = json.loads(sr.analysis_result) if sr.analysis_result else {}
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(
                "Failed to parse analysis_result for result %s: %s", sr.id, e,
                extra={"error_code": "VALIDATION_ERROR"},
            )

        # Prefer deterministic_score when available; fall back to analysis_result
        fit_score = sr.deterministic_score
        if fit_score is None:
            fit_score = analysis.get("fit_score")

        # Resolve a usable display name — fall back to email prefix or "Unknown"
        display_name = cand.name
        if not display_name:
            if cand.email:
                display_name = cand.email.split("@")[0]
            else:
                display_name = f"Candidate #{cand.id}"

        # Skip candidates whose analysis is genuinely incomplete (no score, no name
        # from parsing) — they represent failed or queued analyses that haven't
        # produced any usable data yet.
        has_score = fit_score is not None and fit_score > 0
        has_name = bool(cand.name)
        if not has_score and not has_name:
            continue

        candidates.append({
            "candidate_id":    cand.id,
            "result_id":       sr.id,
            "name":            display_name,
            "email":           cand.email,
            "fit_score":       fit_score,
            "status":          sr.status or "pending",
            "recommendation":  analysis.get("final_recommendation", "Pending"),
            "matched_skills":  analysis.get("matched_skills", []),
            "missing_skills":  analysis.get("missing_skills", []),
            "total_years_exp": cand.total_years_exp,
            "current_role":    cand.current_role,
            "analyzed_at":     sr.timestamp,
            **outcome_fields_from_result(sr),
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_recruiter_or_admin),
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

    # ── Per-row update so each change is audited and pipeline stays in sync ─
    from app.backend.services.audit_service import log_field_change, log_tenant_event
    from app.backend.routes.analyze_helpers import _sync_pipeline_status_for_result

    results = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.id.in_(result_ids),
            ScreeningResult.tenant_id == current_user.tenant_id,
            ScreeningResult.role_template_id == jd_id,
        )
        .all()
    )
    updated = 0
    for result in results:
        old_status = result.status
        result.status = new_status
        log_field_change(
            db=db,
            tenant_id=current_user.tenant_id,
            entity_type="screening_result",
            entity_id=result.id,
            field_name="status",
            old_value=old_status,
            new_value=new_status,
            user_id=current_user.id,
        )
        log_tenant_event(
            db,
            actor=current_user,
            action="result.status_change",
            resource_type="screening_result",
            resource_id=result.id,
            details={"old_status": old_status, "new_status": new_status, "bulk": True},
        )
        _sync_pipeline_status_for_result(db, result.id, new_status)
        updated += 1
    db.commit()

    # Fire-and-forget auto-trigger evaluation for each updated screening result.
    # Uses a fresh session because the request-scoped DB may close after response.
    for result in results:
        if result.candidate_id:
            background_tasks.add_task(
                _schedule_auto_trigger,
                current_user.tenant_id,
                result.candidate_id,
                result.id,
                new_status,
            )

    return {"updated": updated}


@jd_router.get("/{jd_id}/skill-tags")
def get_jd_skill_tags(
    jd_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregated skill tags across all candidates analyzed for a JD.

    Response: {"skills": [...], "domain": str, "candidate_count": int}
    """
    from app.backend.services.skill_matcher import infer_domain_from_skills

    # Verify JD belongs to tenant
    jd = db.query(RoleTemplate).filter(
        RoleTemplate.id == jd_id,
        RoleTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    # Get all active screening results for this JD
    results = db.query(ScreeningResult).filter(
        ScreeningResult.role_template_id == jd_id,
        ScreeningResult.tenant_id == current_user.tenant_id,
        ScreeningResult.is_active == True,
    ).all()

    # Aggregate matched skills across all candidates
    skill_counts: dict = {}
    for r in results:
        try:
            analysis = json.loads(r.analysis_result) if r.analysis_result else {}
            for skill in analysis.get("matched_skills", []):
                if skill and isinstance(skill, str):
                    skill_counts[skill] = skill_counts.get(skill, 0) + 1
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as e:
            logger.warning(
                "Failed to parse analysis_result skills for result %s: %s", r.id, e,
                extra={"error_code": "VALIDATION_ERROR"},
            )

    # Sort by frequency descending, take top skills
    sorted_skills = sorted(skill_counts, key=skill_counts.get, reverse=True)[:20]
    domain = infer_domain_from_skills(sorted_skills) if sorted_skills else "General"

    return {
        "skills": sorted_skills,
        "domain": domain,
        "candidate_count": len(results),
    }


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
