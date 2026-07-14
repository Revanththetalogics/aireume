"""Unified screening analytics — single source of truth for hub and trends APIs."""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import RoleTemplate, ScreeningResult

_PERIOD_DAYS = {
    "last_7_days": 7,
    "last_30_days": 30,
    "last_90_days": 90,
}

STANDARD_SCORE_BUCKETS = ("0-20", "21-40", "41-60", "61-80", "81-100")


def period_to_since(period: str) -> datetime:
    days = _PERIOD_DAYS.get(period, 30)
    return datetime.now(timezone.utc) - timedelta(days=days)


def resolve_date_range(
    *,
    period: str = "last_30_days",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> tuple[datetime, datetime]:
    """Return inclusive UTC range for analytics queries."""
    now = datetime.now(timezone.utc)
    if start_date and end_date:
        start = datetime.fromisoformat(f"{start_date}T00:00:00").replace(tzinfo=timezone.utc)
        end = datetime.fromisoformat(f"{end_date}T23:59:59").replace(tzinfo=timezone.utc)
        return start, min(end, now)
    since = period_to_since(period)
    return since, now


def comparison_range(since: datetime, until: datetime) -> tuple[datetime, datetime]:
    """Prior window of equal length for period-over-period comparison."""
    span = until - since
    comp_until = since
    comp_since = since - span
    return comp_since, comp_until


def _parse_json(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def extract_fit_score(row: ScreeningResult, analysis: Optional[dict] = None) -> Optional[float]:
    analysis = analysis if analysis is not None else _parse_json(row.analysis_result)
    if row.deterministic_score is not None:
        return float(row.deterministic_score)
    raw = analysis.get("fit_score")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def extract_recommendation(row: ScreeningResult, analysis: Optional[dict] = None) -> Optional[str]:
    if row.consolidated_recommendation and str(row.consolidated_recommendation).strip():
        label = str(row.consolidated_recommendation).strip()
        if label.lower() not in ("unknown", "pending", "none"):
            return label
    analysis = analysis if analysis is not None else _parse_json(row.analysis_result)
    raw = (
        analysis.get("final_recommendation")
        or analysis.get("recommendation")
        or analysis.get("consolidated_recommendation")
    )
    if raw is None:
        return None
    label = str(raw).strip()
    if not label or label.lower() in ("unknown", "pending", "none"):
        return None
    return label


def score_to_bucket(score: float) -> str:
    clamped = max(0.0, min(100.0, score))
    if clamped <= 20:
        return "0-20"
    if clamped <= 40:
        return "21-40"
    if clamped <= 60:
        return "41-60"
    if clamped <= 80:
        return "61-80"
    return "81-100"


def iter_skill_gap_names(analysis: dict) -> list[str]:
    names: list[str] = []
    for gap in analysis.get("skill_gaps") or analysis.get("gaps") or analysis.get("missing_skills") or []:
        if isinstance(gap, str) and gap.strip():
            names.append(gap.strip())
        elif isinstance(gap, dict):
            name = gap.get("skill") or gap.get("name")
            if name and str(name).strip():
                names.append(str(name).strip())
    return names


def screening_base_query(
    db: Session,
    tenant_id: int,
    since: datetime,
    until: datetime,
    *,
    requisition_id: Optional[int] = None,
):
    q = db.query(ScreeningResult).filter(
        ScreeningResult.tenant_id == tenant_id,
        ScreeningResult.is_active == True,  # noqa: E712
        ScreeningResult.timestamp >= since,
        ScreeningResult.timestamp <= until,
    )
    if requisition_id:
        q = q.filter(ScreeningResult.requisition_id == requisition_id)
    return q


def aggregate_screening_rows(
    rows: list[ScreeningResult],
    *,
    include_jd_effectiveness: bool = True,
) -> dict[str, Any]:
    """Compute unified screening metrics from loaded ScreeningResult rows."""
    total = len(rows)
    fit_scores: list[float] = []
    recommendation_counter: Counter[str] = Counter()
    skill_gap_counter: Counter[str] = Counter()
    analyses_by_day: Counter[str] = Counter()
    score_buckets = {k: 0 for k in STANDARD_SCORE_BUCKETS}
    shortlisted_status = 0
    hired_status = 0
    recommendation_shortlist = 0
    jd_data: dict[int, dict] = {}

    for row in rows:
        analysis = _parse_json(row.analysis_result)
        score = extract_fit_score(row, analysis)
        if score is not None:
            fit_scores.append(score)
            score_buckets[score_to_bucket(score)] += 1

        rec = extract_recommendation(row, analysis)
        if rec:
            recommendation_counter[rec] += 1
            if "shortlist" in rec.lower():
                recommendation_shortlist += 1

        for skill in iter_skill_gap_names(analysis):
            skill_gap_counter[skill] += 1

        if row.timestamp:
            analyses_by_day[row.timestamp.strftime("%Y-%m-%d")] += 1

        if row.status == "shortlisted":
            shortlisted_status += 1
        if row.status == "hired":
            hired_status += 1

        if include_jd_effectiveness:
            jid = row.role_template_id
            if jid is not None:
                if jid not in jd_data:
                    jd_data[jid] = {"scores": [], "shortlisted": 0, "total": 0}
                jd_data[jid]["total"] += 1
                if score is not None:
                    jd_data[jid]["scores"].append(score)
                if row.status == "shortlisted":
                    jd_data[jid]["shortlisted"] += 1

    analyses_by_day_list = [
        {"date": day, "count": count}
        for day, count in sorted(analyses_by_day.items())
    ]
    top_skill_gaps = [
        {"skill": skill, "frequency": freq, "count": freq}
        for skill, freq in skill_gap_counter.most_common(15)
    ]
    score_distribution = [
        {"range": range_name, "count": count}
        for range_name, count in score_buckets.items()
    ]

    pass_through_rates = {
        "analyzed_to_shortlisted": round(shortlisted_status / total, 4) if total else 0,
        "shortlisted_to_hired": round(hired_status / shortlisted_status, 4) if shortlisted_status else 0,
    }

    return {
        "total_analyzed": total,
        "avg_fit_score": round(sum(fit_scores) / len(fit_scores), 1) if fit_scores else 0,
        "recommendation_distribution": dict(recommendation_counter),
        "recommendation_shortlist_rate": round(100 * recommendation_shortlist / total, 1) if total else 0,
        "pipeline_shortlist_rate": round(100 * shortlisted_status / total, 1) if total else 0,
        "hired_rate": round(100 * hired_status / total, 1) if total else 0,
        "analyses_by_day": analyses_by_day_list,
        "top_skill_gaps": top_skill_gaps,
        "score_distribution": score_distribution,
        "pass_through_rates": pass_through_rates,
        "jd_data": jd_data,
    }


def build_jd_effectiveness(
    db: Session,
    jd_data: dict[int, dict],
) -> list[dict[str, Any]]:
    if not jd_data:
        return []
    templates = (
        db.query(RoleTemplate)
        .filter(RoleTemplate.id.in_(set(jd_data.keys())))
        .all()
    )
    jd_map = {t.id: t.name for t in templates}
    rows = []
    for jid, data in jd_data.items():
        avg_score = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0
        shortlist_rate = round(data["shortlisted"] / data["total"], 4) if data["total"] else 0
        rows.append({
            "jd_name": jd_map.get(jid, "Unknown JD"),
            "candidates": data["total"],
            "avg_score": avg_score,
            "shortlist_rate": shortlist_rate,
        })
    return rows


def build_screening_analytics(
    db: Session,
    tenant_id: int,
    *,
    period: str = "last_30_days",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    requisition_id: Optional[int] = None,
    compare: bool = False,
) -> dict[str, Any]:
    """Full screening analytics payload used by /api/analytics/screening and hub trends."""
    since, until = resolve_date_range(
        period=period,
        start_date=start_date,
        end_date=end_date,
    )
    rows = screening_base_query(
        db, tenant_id, since, until, requisition_id=requisition_id
    ).all()
    metrics = aggregate_screening_rows(rows)
    jd_effectiveness = build_jd_effectiveness(db, metrics.pop("jd_data"))

    payload: dict[str, Any] = {
        "period": period,
        "start_date": since.date().isoformat(),
        "end_date": until.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {"requisition_id": requisition_id},
        **metrics,
        "jd_effectiveness": jd_effectiveness,
    }

    if compare:
        comp_since, comp_until = comparison_range(since, until)
        comp_rows = screening_base_query(
            db, tenant_id, comp_since, comp_until, requisition_id=requisition_id
        ).all()
        comp_metrics = aggregate_screening_rows(comp_rows, include_jd_effectiveness=False)
        payload["comparison"] = {
            "period_label": "prior period",
            "start_date": comp_since.date().isoformat(),
            "end_date": comp_until.date().isoformat(),
            "total_analyzed": comp_metrics["total_analyzed"],
            "avg_fit_score": comp_metrics["avg_fit_score"],
            "pipeline_shortlist_rate": comp_metrics["pipeline_shortlist_rate"],
            "deltas": {
                "total_analyzed": metrics["total_analyzed"] - comp_metrics["total_analyzed"],
                "avg_fit_score": round(
                    metrics["avg_fit_score"] - comp_metrics["avg_fit_score"], 1
                ),
                "pipeline_shortlist_rate": round(
                    metrics["pipeline_shortlist_rate"] - comp_metrics["pipeline_shortlist_rate"], 1
                ),
            },
        }

    return payload
