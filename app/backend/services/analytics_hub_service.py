"""Analytics hub — interactive drill-down aggregates for all hiring slices."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    ATSSyncLog,
    ATSConnection,
    Requisition,
    RequisitionCandidate,
    ScreeningResult,
    UsageLog,
    User,
    VoiceScreeningSession,
)

_PERIOD_DAYS = {
    "last_7_days": 7,
    "last_30_days": 30,
    "last_90_days": 90,
}


def _since(period: str) -> datetime:
    days = _PERIOD_DAYS.get(period, 30)
    return datetime.now(timezone.utc) - timedelta(days=days)


def _parse_json(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def build_analytics_hub(
    db: Session,
    tenant_id: int,
    *,
    period: str = "last_30_days",
    requisition_id: Optional[int] = None,
    recruiter_id: Optional[int] = None,
) -> dict[str, Any]:
    """Build full analytics hub payload for interactive UI."""
    since = _since(period)

    screening = _screening_slice(db, tenant_id, since, requisition_id)
    funnel = _funnel_slice(db, tenant_id, since, requisition_id)
    interviews = _interviews_slice(db, tenant_id, since, requisition_id)
    team = _team_slice(db, tenant_id, since, recruiter_id)
    hm = _hm_slice(db, tenant_id, since, requisition_id)
    leadership = _leadership_slice(db, tenant_id, since)
    ats = _ats_slice(db, tenant_id, since)

    return {
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "requisition_id": requisition_id,
            "recruiter_id": recruiter_id,
        },
        "slices": {
            "screening": screening,
            "funnel": funnel,
            "interviews": interviews,
            "team": team,
            "hm": hm,
            "leadership": leadership,
            "ats": ats,
        },
    }


def _screening_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    requisition_id: Optional[int],
) -> dict[str, Any]:
    q = db.query(ScreeningResult).filter(
        ScreeningResult.tenant_id == tenant_id,
        ScreeningResult.is_active == True,  # noqa: E712
        ScreeningResult.timestamp >= since,
    )
    if requisition_id:
        q = q.filter(ScreeningResult.requisition_id == requisition_id)
    rows = q.all()

    total = len(rows)
    scores: list[float] = []
    recs: Counter[str] = Counter()
    skill_gaps: Counter[str] = Counter()
    score_buckets: Counter[str] = Counter()
    drill_down: list[dict] = []

    for r in rows:
        analysis = _parse_json(r.analysis_result)
        score = r.deterministic_score or analysis.get("fit_score")
        if score is not None:
            try:
                s = float(score)
                scores.append(s)
                bucket = f"{int(s // 10) * 10}-{int(s // 10) * 10 + 9}"
                score_buckets[bucket] += 1
            except (TypeError, ValueError):
                pass
        rec = str(analysis.get("recommendation") or "unknown").lower()
        recs[rec] += 1
        for gap in analysis.get("skill_gaps") or analysis.get("gaps") or []:
            name = gap if isinstance(gap, str) else gap.get("skill") or gap.get("name")
            if name:
                skill_gaps[str(name).lower()] += 1
        drill_down.append({
            "id": r.id,
            "candidate_id": r.candidate_id,
            "requisition_id": r.requisition_id,
            "fit_score": r.deterministic_score,
            "recommendation": analysis.get("recommendation"),
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        })

    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    shortlist_n = sum(v for k, v in recs.items() if "shortlist" in k)
    shortlist_rate = round(100 * shortlist_n / total, 1) if total else 0

    return {
        "kpis": {
            "total_analyzed": total,
            "avg_fit_score": avg_score,
            "shortlist_rate": shortlist_rate,
        },
        "recommendation_distribution": dict(recs),
        "score_distribution": dict(score_buckets),
        "top_skill_gaps": [
            {"skill": k, "count": v}
            for k, v in skill_gaps.most_common(15)
        ],
        "drill_down": drill_down[:100],
    }


def _funnel_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    requisition_id: Optional[int],
) -> dict[str, Any]:
    q = (
        db.query(RequisitionCandidate, Requisition)
        .join(Requisition, Requisition.id == RequisitionCandidate.requisition_id)
        .filter(Requisition.tenant_id == tenant_id, RequisitionCandidate.added_at >= since)
    )
    if requisition_id:
        q = q.filter(RequisitionCandidate.requisition_id == requisition_id)
    rows = q.all()

    stage_counts: Counter[str] = Counter()
    by_req: dict[int, dict] = {}
    stale: list[dict] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for rc, req in rows:
        stage = rc.pipeline_status or "pending"
        stage_counts[stage] += 1
        if req.id not in by_req:
            by_req[req.id] = {
                "requisition_id": req.id,
                "title": req.title,
                "stages": Counter(),
                "total": 0,
            }
        by_req[req.id]["stages"][stage] += 1
        by_req[req.id]["total"] += 1
        if rc.updated_at and rc.updated_at < stale_cutoff and stage in ("pending", "in-review"):
            stale.append({
                "candidate_id": rc.candidate_id,
                "requisition_id": req.id,
                "requisition_title": req.title,
                "pipeline_status": stage,
                "updated_at": rc.updated_at.isoformat(),
            })

    req_funnels = []
    for rid, data in by_req.items():
        stages = dict(data["stages"])
        req_funnels.append({
            "requisition_id": rid,
            "title": data["title"],
            "total": data["total"],
            "stages": stages,
            "shortlist_rate": round(
                100 * stages.get("shortlisted", 0) / data["total"], 1
            ) if data["total"] else 0,
        })
    req_funnels.sort(key=lambda x: x["total"], reverse=True)

    return {
        "stage_totals": dict(stage_counts),
        "by_requisition": req_funnels[:50],
        "stale_candidates": stale[:30],
        "conversion": {
            "to_shortlist": round(
                100 * stage_counts.get("shortlisted", 0) / max(sum(stage_counts.values()), 1), 1
            ),
            "to_hired": round(
                100 * stage_counts.get("hired", 0) / max(sum(stage_counts.values()), 1), 1
            ),
        },
    }


def _interviews_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    requisition_id: Optional[int],
) -> dict[str, Any]:
    q = db.query(VoiceScreeningSession).filter(
        VoiceScreeningSession.tenant_id == tenant_id,
        VoiceScreeningSession.created_at >= since,
    )
    rows = q.all()

    status_counts: Counter[str] = Counter()
    completed = 0
    durations: list[int] = []
    resume_vs_call: list[dict] = []

    for s in rows:
        status_counts[s.status or "unknown"] += 1
        if s.status == "completed":
            completed += 1
            if s.duration_seconds:
                durations.append(s.duration_seconds)
        if s.assessment_json:
            try:
                assessment = json.loads(s.assessment_json)
                call_score = assessment.get("overall_score") or assessment.get("score")
                if call_score is not None and s.candidate_id:
                    sr = (
                        db.query(ScreeningResult)
                        .filter(
                            ScreeningResult.tenant_id == tenant_id,
                            ScreeningResult.candidate_id == s.candidate_id,
                        )
                        .order_by(ScreeningResult.timestamp.desc())
                        .first()
                    )
                    if sr and sr.deterministic_score is not None:
                        resume_vs_call.append({
                            "candidate_id": s.candidate_id,
                            "resume_score": sr.deterministic_score,
                            "call_score": call_score,
                            "delta": int(call_score) - int(sr.deterministic_score),
                        })
            except (json.JSONDecodeError, TypeError):
                pass

    total = len(rows)
    return {
        "kpis": {
            "total_sessions": total,
            "completion_rate": round(100 * completed / total, 1) if total else 0,
            "avg_duration_min": round(sum(durations) / len(durations) / 60, 1) if durations else 0,
        },
        "status_breakdown": dict(status_counts),
        "resume_vs_call_delta": resume_vs_call[:50],
    }


def _team_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    recruiter_id: Optional[int],
) -> dict[str, Any]:
    analysis_actions = ["resume_analysis", "batch_analysis"]

    log_q = (
        db.query(
            UsageLog.user_id,
            func.coalesce(func.sum(UsageLog.quantity), 0).label("analyses"),
        )
        .filter(
            UsageLog.tenant_id == tenant_id,
            UsageLog.created_at >= since,
            UsageLog.action.in_(analysis_actions),
            UsageLog.user_id.isnot(None),
        )
        .group_by(UsageLog.user_id)
    )
    if recruiter_id:
        log_q = log_q.filter(UsageLog.user_id == recruiter_id)
    usage_by_user = {row.user_id: int(row.analyses) for row in log_q.all()}

    recruiters = (
        db.query(User)
        .filter(User.tenant_id == tenant_id, User.is_active == True)  # noqa: E712
        .all()
    )
    activity = []
    for u in recruiters:
        if recruiter_id and u.id != recruiter_id:
            continue
        count = usage_by_user.get(u.id, 0)
        if count == 0 and recruiter_id:
            continue
        activity.append({
            "user_id": u.id,
            "email": u.email,
            "name": u.email,
            "analyses": count,
        })
    activity.sort(key=lambda x: x["analyses"], reverse=True)

    return {"recruiter_activity": activity[:25]}


def _hm_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    requisition_id: Optional[int],
) -> dict[str, Any]:
    q = (
        db.query(RequisitionCandidate)
        .join(Requisition, Requisition.id == RequisitionCandidate.requisition_id)
        .filter(Requisition.tenant_id == tenant_id)
    )
    if requisition_id:
        q = q.filter(RequisitionCandidate.requisition_id == requisition_id)
    rows = q.all()

    submitted = 0
    outcomes: Counter[str] = Counter()
    pending_review = 0
    turnaround_hours: list[float] = []

    for rc in rows:
        if rc.submission_status == "submitted":
            submitted += 1
            if not rc.hm_outcome:
                pending_review += 1
        if rc.hm_outcome:
            outcomes[rc.hm_outcome] += 1
        if rc.submitted_at and rc.outcome_at:
            delta = (rc.outcome_at - rc.submitted_at).total_seconds() / 3600
            turnaround_hours.append(delta)

    return {
        "submissions_sent": submitted,
        "pending_hm_review": pending_review,
        "outcome_distribution": dict(outcomes),
        "avg_turnaround_hours": round(sum(turnaround_hours) / len(turnaround_hours), 1)
        if turnaround_hours
        else None,
    }


def _leadership_slice(db: Session, tenant_id: int, since: datetime) -> dict[str, Any]:
    reqs = (
        db.query(Requisition)
        .filter(Requisition.tenant_id == tenant_id)
        .all()
    )
    open_reqs = [r for r in reqs if r.status not in ("filled", "closed", "cancelled")]
    zero_pipeline = []
    calibrated_no_screens = []

    for r in open_reqs:
        cand_count = (
            db.query(func.count(RequisitionCandidate.id))
            .filter(RequisitionCandidate.requisition_id == r.id)
            .scalar()
        ) or 0
        if cand_count == 0:
            zero_pipeline.append({"id": r.id, "title": r.title, "status": r.status})
        if r.calibrated_criteria_json and cand_count == 0:
            calibrated_no_screens.append({"id": r.id, "title": r.title})

    return {
        "open_requisitions": len(open_reqs),
        "risk_flags": {
            "zero_pipeline": zero_pipeline[:20],
            "calibrated_no_candidates": calibrated_no_screens[:20],
        },
    }


def _ats_slice(db: Session, tenant_id: int, since: datetime) -> dict[str, Any]:
    connections = (
        db.query(ATSConnection)
        .filter(ATSConnection.tenant_id == tenant_id)
        .all()
    )
    logs = (
        db.query(ATSSyncLog)
        .filter(ATSSyncLog.tenant_id == tenant_id, ATSSyncLog.created_at >= since)
        .order_by(ATSSyncLog.created_at.desc())
        .limit(500)
        .all()
    )

    success = sum(1 for l in logs if l.success)
    failed = sum(1 for l in logs if not l.success)
    by_provider: Counter[str] = Counter()
    errors: Counter[str] = Counter()

    for l in logs:
        conn = next((c for c in connections if c.id == l.connection_id), None)
        provider = conn.provider if conn else "unknown"
        by_provider[provider] += 1
        if not l.success and l.error_message:
            errors[l.error_message[:120]] += 1

    return {
        "connections": len(connections),
        "active_connections": sum(1 for c in connections if c.is_active),
        "sync_total": len(logs),
        "sync_success_rate": round(100 * success / len(logs), 1) if logs else 0,
        "sync_failed": failed,
        "by_provider": dict(by_provider),
        "top_errors": [{"message": k, "count": v} for k, v in errors.most_common(10)],
        "recent_failures": [
            {
                "id": l.id,
                "connection_id": l.connection_id,
                "entity_type": l.entity_type,
                "error_message": l.error_message,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
            if not l.success
        ][:20],
    }
