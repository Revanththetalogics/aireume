"""Analytics overview — command center KPIs and attention cards."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.backend.services.analytics_hub_service import build_analytics_hub

ROLE_DEFAULT_SLICE = {
    "admin": "screening",
    "recruiter": "screening",
    "viewer": "funnel",
    "hiring_manager": "hm",
}

ROLE_KPIS = {
    "admin": ["total_analyzed", "avg_fit_score", "pending_hm_review", "ats_failure_count"],
    "recruiter": ["total_analyzed", "avg_fit_score", "pipeline_shortlist_rate", "pending_hm_review"],
    "viewer": ["total_analyzed", "pipeline_shortlist_rate"],
    "hiring_manager": ["pending_hm_review", "hm_advance_rate", "hm_reject_rate"],
}


def build_analytics_overview(
    db: Session,
    tenant_id: int,
    *,
    period: str = "last_30_days",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    requisition_id: Optional[int] = None,
    recruiter_id: Optional[int] = None,
    include_pii: bool = True,
    user_role: str = "recruiter",
) -> dict[str, Any]:
    """Build command-center overview from hub slices."""
    hub = build_analytics_hub(
        db,
        tenant_id,
        period=period,
        start_date=start_date,
        end_date=end_date,
        requisition_id=requisition_id,
        recruiter_id=recruiter_id,
        slices=["screening", "funnel", "hm", "leadership", "ats", "interviews"],
        include_pii=include_pii,
        user_role=user_role,
    )

    screening = hub["slices"].get("screening", {})
    kpis_src = screening.get("kpis", {})
    hm = hub["slices"].get("hm", {})
    ats = hub["slices"].get("ats", {})
    interviews = hub["slices"].get("interviews", {})

    outcomes = hm.get("outcome_distribution", {})
    hm_advanced = outcomes.get("advance", 0) or 0
    hm_rejected = outcomes.get("reject", 0) or 0
    hm_decided = hm_advanced + hm_rejected

    kpi_values = {
        "total_analyzed": kpis_src.get("total_analyzed", 0),
        "avg_fit_score": kpis_src.get("avg_fit_score", 0),
        "recommendation_shortlist_rate": kpis_src.get("recommendation_shortlist_rate", 0),
        "pipeline_shortlist_rate": kpis_src.get("pipeline_shortlist_rate", 0),
        "pending_hm_review": hub["attention"].get("pending_hm_review", 0),
        "stale_candidate_count": len(hub["attention"].get("stale_candidates", [])),
        "zero_pipeline_count": len(hub["attention"].get("zero_pipeline_requisitions", [])),
        "ats_failure_count": ats.get("sync_failed", 0),
        "interview_completion_rate": interviews.get("kpis", {}).get("completion_rate", 0),
        "hm_advance_rate": round(100 * hm_advanced / hm_decided, 1) if hm_decided else 0,
        "hm_reject_rate": round(100 * hm_rejected / hm_decided, 1) if hm_decided else 0,
        "hm_submitted": hm.get("submissions_sent", 0),
    }

    role_kpi_keys = ROLE_KPIS.get(user_role, ROLE_KPIS["recruiter"])
    role_kpis = [
        {"key": key, "value": kpi_values.get(key, 0)}
        for key in role_kpi_keys
    ]

    mini_trend = screening.get("trends", {}).get("analyses_by_day") or screening.get("analyses_by_day", [])

    return {
        "period": hub["period"],
        "start_date": hub["start_date"],
        "end_date": hub["end_date"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "default_slice": ROLE_DEFAULT_SLICE.get(user_role, "screening"),
        "attention": hub["attention"],
        "role_kpis": role_kpis,
        "mini_trend": mini_trend[-14:],
        "filter_options": hub["filter_options"],
        "filters": hub["filters"],
    }
