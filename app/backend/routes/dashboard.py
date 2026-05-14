"""
Dashboard summary/activity and screening analytics endpoints.
"""
import json
import logging
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user, require_admin
from app.backend.models.db_models import Candidate, RoleTemplate, ScreeningResult, User
from app.backend.services.skill_trend_service import compute_monthly_snapshot, get_skill_trends

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard", "analytics"])


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _safe_parse_json(raw: Optional[str]) -> dict:
    """Safely parse a JSON string; return {} on failure."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _extract_fit_score(analysis: dict) -> Optional[float]:
    """Extract fit_score from analysis_result JSON, handling various types."""
    score = analysis.get("fit_score")
    if score is None:
        return None
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def _period_to_start(period: str) -> datetime:
    """Convert a period string to the corresponding start datetime (UTC)."""
    now = datetime.now(timezone.utc)
    mapping = {
        "last_7_days": timedelta(days=7),
        "last_30_days": timedelta(days=30),
        "last_90_days": timedelta(days=90),
    }
    delta = mapping.get(period, timedelta(days=30))
    return now - delta


# ── GET /api/dashboard/summary ─────────────────────────────────────────────────

@router.get("/api/dashboard/summary")
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    # ── Action items ────────────────────────────────────────────────────────────
    pending_review = (
        db.query(func.count(ScreeningResult.id))
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.status == "pending",
            ScreeningResult.is_active == True,
        )
        .scalar()
    ) or 0

    in_progress_analyses = (
        db.query(func.count(ScreeningResult.id))
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.narrative_status == "processing",
        )
        .scalar()
    ) or 0

    shortlisted_count = (
        db.query(func.count(ScreeningResult.id))
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.status == "shortlisted",
            ScreeningResult.is_active == True,
        )
        .scalar()
    ) or 0

    # ── Pipeline by JD ─────────────────────────────────────────────────────────
    # Fetch all active results for this tenant, grouped by role_template_id
    results = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.is_active == True,
        )
        .all()
    )

    # Collect unique role_template_ids
    jd_ids = {r.role_template_id for r in results if r.role_template_id is not None}
    jd_map: Dict[int, str] = {}
    if jd_ids:
        templates = db.query(RoleTemplate).filter(RoleTemplate.id.in_(jd_ids)).all()
        jd_map = {t.id: t.name for t in templates}

    # Group results by JD
    jd_groups: Dict[int, List[ScreeningResult]] = {}
    for r in results:
        jid = r.role_template_id
        if jid is None:
            continue
        jd_groups.setdefault(jid, []).append(r)

    pipeline_by_jd = []
    for jid, group in jd_groups.items():
        by_status: Dict[str, int] = Counter()
        fit_scores: List[float] = []
        for r in group:
            by_status[r.status or "pending"] += 1
            analysis = _safe_parse_json(r.analysis_result)
            score = _extract_fit_score(analysis)
            if score is not None:
                fit_scores.append(score)
        pipeline_by_jd.append({
            "jd_id": jid,
            "jd_name": jd_map.get(jid, "Unknown JD"),
            "total_candidates": len(group),
            "by_status": dict(by_status),
            "avg_fit_score": round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else 0,
        })

    # ── Weekly metrics ──────────────────────────────────────────────────────────
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    weekly_results = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.is_active == True,
            ScreeningResult.timestamp >= week_ago,
        )
        .all()
    )

    weekly_fit_scores: List[float] = []
    weekly_shortlisted = 0
    skill_gap_counter: Counter = Counter()
    for r in weekly_results:
        analysis = _safe_parse_json(r.analysis_result)
        score = _extract_fit_score(analysis)
        if score is not None:
            weekly_fit_scores.append(score)
        if r.status == "shortlisted":
            weekly_shortlisted += 1
        # Skill gaps
        missing = analysis.get("missing_skills", [])
        if isinstance(missing, list):
            for skill in missing:
                if isinstance(skill, str) and skill.strip():
                    skill_gap_counter[skill.strip()] += 1

    top_skill_gaps = [skill for skill, _ in skill_gap_counter.most_common(5)]

    return {
        "action_items": {
            "pending_review": pending_review,
            "in_progress_analyses": in_progress_analyses,
            "shortlisted_count": shortlisted_count,
        },
        "pipeline_by_jd": pipeline_by_jd,
        "weekly_metrics": {
            "analyses_this_week": len(weekly_results),
            "avg_fit_score": round(sum(weekly_fit_scores) / len(weekly_fit_scores), 1) if weekly_fit_scores else 0,
            "shortlist_rate": round(weekly_shortlisted / len(weekly_results), 2) if weekly_results else 0,
            "top_skill_gaps": top_skill_gaps,
        },
    }


# ── GET /api/dashboard/activity ────────────────────────────────────────────────

@router.get("/api/dashboard/activity")
async def get_dashboard_activity(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = current_user.tenant_id

    results = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.tenant_id == tenant_id)
        .order_by(ScreeningResult.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Pre-load candidate and JD names
    candidate_ids = {r.candidate_id for r in results if r.candidate_id is not None}
    jd_ids = {r.role_template_id for r in results if r.role_template_id is not None}

    candidate_map: Dict[int, str] = {}
    if candidate_ids:
        candidates = db.query(Candidate).filter(Candidate.id.in_(candidate_ids)).all()
        candidate_map = {c.id: (c.name or "Unknown") for c in candidates}

    jd_map: Dict[int, str] = {}
    if jd_ids:
        templates = db.query(RoleTemplate).filter(RoleTemplate.id.in_(jd_ids)).all()
        jd_map = {t.id: t.name for t in templates}

    activities = []
    for r in results:
        analysis = _safe_parse_json(r.analysis_result)
        fit_score = _extract_fit_score(analysis)
        recommendation = analysis.get("final_recommendation", "Pending")

        activities.append({
            "type": "analysis_completed",
            "candidate_name": candidate_map.get(r.candidate_id, "Unknown"),
            "jd_name": jd_map.get(r.role_template_id, "Unknown JD"),
            "fit_score": fit_score,
            "recommendation": recommendation,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "result_id": r.id,
        })

    return {"activities": activities}


# ── GET /api/analytics/screening ───────────────────────────────────────────────

@router.get("/api/analytics/screening")
async def get_screening_analytics(
    period: str = Query("last_30_days", pattern="^(last_7_days|last_30_days|last_90_days)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = current_user.tenant_id
    start_date = _period_to_start(period)

    # ── Base queryset ───────────────────────────────────────────────────────────
    results = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.is_active == True,
            ScreeningResult.timestamp >= start_date,
        )
        .all()
    )

    total_analyzed = len(results)

    # ── Fit scores & recommendation distribution ────────────────────────────────
    fit_scores: List[float] = []
    recommendation_counter: Counter = Counter()
    skill_gap_counter: Counter = Counter()
    analyses_by_day: Dict[str, int] = Counter()
    score_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    shortlisted = 0
    hired = 0

    # JD effectiveness tracking
    jd_data: Dict[int, dict] = {}  # jd_id -> {scores, shortlisted, total}

    for r in results:
        # Fit score
        analysis = _safe_parse_json(r.analysis_result)
        score = _extract_fit_score(analysis)
        if score is not None:
            fit_scores.append(score)
            # Bucket
            if score <= 20:
                score_buckets["0-20"] += 1
            elif score <= 40:
                score_buckets["21-40"] += 1
            elif score <= 60:
                score_buckets["41-60"] += 1
            elif score <= 80:
                score_buckets["61-80"] += 1
            else:
                score_buckets["81-100"] += 1

        # Recommendation
        rec = analysis.get("final_recommendation")
        if rec and isinstance(rec, str):
            recommendation_counter[rec] += 1

        # Skill gaps
        missing = analysis.get("missing_skills", [])
        if isinstance(missing, list):
            for skill in missing:
                if isinstance(skill, str) and skill.strip():
                    skill_gap_counter[skill.strip()] += 1

        # Day grouping
        if r.timestamp:
            day_key = r.timestamp.strftime("%Y-%m-%d")
            analyses_by_day[day_key] += 1

        # Status counts
        if r.status == "shortlisted":
            shortlisted += 1
        if r.status == "hired":
            hired += 1

        # JD effectiveness
        jid = r.role_template_id
        if jid is not None:
            if jid not in jd_data:
                jd_data[jid] = {"scores": [], "shortlisted": 0, "total": 0}
            jd_data[jid]["total"] += 1
            if score is not None:
                jd_data[jid]["scores"].append(score)
            if r.status == "shortlisted":
                jd_data[jid]["shortlisted"] += 1

    # Load JD names
    jd_ids = set(jd_data.keys())
    jd_map: Dict[int, str] = {}
    if jd_ids:
        templates = db.query(RoleTemplate).filter(RoleTemplate.id.in_(jd_ids)).all()
        jd_map = {t.id: t.name for t in templates}

    # Build analyses_by_day sorted list
    analyses_by_day_list = [
        {"date": day, "count": count}
        for day, count in sorted(analyses_by_day.items())
    ]

    # Build top_skill_gaps
    top_skill_gaps = [
        {"skill": skill, "frequency": freq}
        for skill, freq in skill_gap_counter.most_common(10)
    ]

    # Build score_distribution
    score_distribution = [
        {"range": range_name, "count": count}
        for range_name, count in score_buckets.items()
    ]

    # Pass-through rates
    pass_through_rates = {
        "analyzed_to_shortlisted": round(shortlisted / total_analyzed, 2) if total_analyzed else 0,
        "shortlisted_to_hired": round(hired / shortlisted, 2) if shortlisted else 0,
    }

    # JD effectiveness
    jd_effectiveness = []
    for jid, data in jd_data.items():
        avg_score = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0
        shortlist_rate = round(data["shortlisted"] / data["total"], 2) if data["total"] else 0
        jd_effectiveness.append({
            "jd_name": jd_map.get(jid, "Unknown JD"),
            "candidates": data["total"],
            "avg_score": avg_score,
            "shortlist_rate": shortlist_rate,
        })

    return {
        "period": period,
        "total_analyzed": total_analyzed,
        "avg_fit_score": round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else 0,
        "recommendation_distribution": dict(recommendation_counter),
        "analyses_by_day": analyses_by_day_list,
        "top_skill_gaps": top_skill_gaps,
        "score_distribution": score_distribution,
        "pass_through_rates": pass_through_rates,
        "jd_effectiveness": jd_effectiveness,
    }


# ── GET /api/analytics/skill-trends ───────────────────────────────────────────

@router.get("/api/analytics/skill-trends")
async def get_skill_trends_endpoint(
    role_category: Optional[str] = Query(None, description="Filter by role category"),
    months: int = Query(6, ge=1, le=24, description="Number of months to look back"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return skill trend time-series data for the tenant."""
    tenant_id = current_user.tenant_id
    return get_skill_trends(db, tenant_id, role_category=role_category, months=months)


# ── POST /api/analytics/skill-trends/compute ──────────────────────────────────

@router.post("/api/analytics/skill-trends/compute")
async def compute_skill_trends_endpoint(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: Compute skill frequency snapshot for the current month."""
    from datetime import date as _date
    tenant_id = current_user.tenant_id
    target = _date.today().replace(day=1)
    count = compute_monthly_snapshot(db, tenant_id, target_date=target)
    return {"snapshots_created": count, "period": target.strftime("%Y-%m")}
