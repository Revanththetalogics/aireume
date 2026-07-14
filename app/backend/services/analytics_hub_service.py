"""Analytics hub — interactive drill-down aggregates for all hiring slices."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    ATSSyncLog,
    ATSConnection,
    Candidate,
    Requisition,
    RequisitionCandidate,
    ScreeningResult,
    UsageLog,
    User,
    VoiceScreeningSession,
)
from app.backend.services.screening_analytics_service import (
    aggregate_screening_rows,
    build_screening_analytics,
    extract_fit_score,
    extract_recommendation,
    iter_skill_gap_names,
    resolve_date_range,
    screening_base_query,
)

VALID_SLICES = frozenset({
    "screening", "funnel", "interviews", "team", "hm", "leadership", "ats",
})

VALID_PERIODS = frozenset({"last_7_days", "last_30_days", "last_90_days"})


def _parse_json(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _candidate_label(candidate: Optional[Candidate], candidate_id: Optional[int]) -> str:
    if candidate and candidate.name and str(candidate.name).strip():
        return str(candidate.name).strip()
    if candidate_id:
        return f"Candidate #{candidate_id}"
    return "Unknown candidate"


def _resolve_candidate_display(
    candidate: Optional[Candidate],
    *,
    candidate_id: Optional[int] = None,
    analysis: Optional[dict] = None,
    parsed: Optional[dict] = None,
) -> tuple[str, Optional[str]]:
    analysis = analysis or {}
    parsed = parsed or {}
    name: Optional[str] = None
    email: Optional[str] = None

    if candidate:
        if candidate.name and str(candidate.name).strip():
            name = str(candidate.name).strip()
        email = candidate.email

    if not name:
        for candidate_name in (
            analysis.get("candidate_name"),
            (analysis.get("contact_info") or {}).get("name"),
            (analysis.get("candidate_profile") or {}).get("name"),
            (parsed.get("contact_info") or {}).get("name"),
        ):
            if candidate_name and str(candidate_name).strip():
                name = str(candidate_name).strip()
                break

    if not email:
        email = (
            (analysis.get("contact_info") or {}).get("email")
            or (parsed.get("contact_info") or {}).get("email")
        )

    display = name or _candidate_label(None, candidate_id)
    return display, email


def _mask_email(email: Optional[str], *, include_pii: bool) -> Optional[str]:
    if include_pii or not email:
        return email
    local, _, domain = email.partition("@")
    if not domain:
        return None
    masked = f"{local[:1]}***@{domain}" if local else f"***@{domain}"
    return masked


def _load_candidates(
    db: Session, tenant_id: int, candidate_ids: set[int]
) -> dict[int, Candidate]:
    if not candidate_ids:
        return {}
    rows = (
        db.query(Candidate)
        .filter(Candidate.tenant_id == tenant_id, Candidate.id.in_(candidate_ids))
        .all()
    )
    return {c.id: c for c in rows}


def _load_requisitions(
    db: Session, tenant_id: int, requisition_ids: set[int]
) -> dict[int, Requisition]:
    if not requisition_ids:
        return {}
    rows = (
        db.query(Requisition)
        .filter(Requisition.tenant_id == tenant_id, Requisition.id.in_(requisition_ids))
        .all()
    )
    return {r.id: r for r in rows}


def _latest_screening_by_candidate(
    db: Session,
    tenant_id: int,
    candidate_ids: set[int],
    *,
    requisition_id: Optional[int] = None,
) -> dict[int, ScreeningResult]:
    if not candidate_ids:
        return {}
    q = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.candidate_id.in_(candidate_ids),
            ScreeningResult.is_active == True,  # noqa: E712
        )
        .order_by(ScreeningResult.timestamp.desc())
    )
    if requisition_id:
        q = q.filter(ScreeningResult.requisition_id == requisition_id)
    latest: dict[int, ScreeningResult] = {}
    for row in q.all():
        if row.candidate_id and row.candidate_id not in latest:
            latest[row.candidate_id] = row
    return latest


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def validate_hub_filters(
    db: Session,
    tenant_id: int,
    *,
    requisition_id: Optional[int] = None,
    recruiter_id: Optional[int] = None,
) -> None:
    from fastapi import HTTPException

    if requisition_id is not None:
        req = (
            db.query(Requisition)
            .filter(Requisition.id == requisition_id, Requisition.tenant_id == tenant_id)
            .first()
        )
        if not req:
            raise HTTPException(status_code=404, detail="Requisition not found")
    if recruiter_id is not None:
        user = (
            db.query(User)
            .filter(
                User.id == recruiter_id,
                User.tenant_id == tenant_id,
                User.is_active == True,  # noqa: E712
            )
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="Recruiter not found")


def _filter_options(db: Session, tenant_id: int) -> dict[str, list[dict]]:
    reqs = (
        db.query(Requisition)
        .filter(Requisition.tenant_id == tenant_id)
        .order_by(Requisition.title.asc())
        .limit(200)
        .all()
    )
    recruiters = (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.is_active == True,  # noqa: E712
            User.role.in_(("admin", "recruiter")),
        )
        .order_by(User.email.asc())
        .all()
    )
    return {
        "requisitions": [{"id": r.id, "title": r.title} for r in reqs],
        "recruiters": [{"id": u.id, "email": u.email} for u in recruiters],
        "requisitions_truncated": len(reqs) >= 200,
    }


def build_analytics_hub(
    db: Session,
    tenant_id: int,
    *,
    period: str = "last_30_days",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    requisition_id: Optional[int] = None,
    recruiter_id: Optional[int] = None,
    slices: Optional[list[str]] = None,
    drill_limit: int = 100,
    drill_offset: int = 0,
    include_pii: bool = True,
    compare: bool = False,
    user_role: Optional[str] = None,
) -> dict[str, Any]:
    """Build analytics hub payload for interactive UI."""
    since, until = resolve_date_range(
        period=period,
        start_date=start_date,
        end_date=end_date,
    )
    requested = set(slices or VALID_SLICES)
    requested.discard("reports")

    result_slices: dict[str, Any] = {}
    if "screening" in requested:
        result_slices["screening"] = _screening_slice(
            db,
            tenant_id,
            since,
            until,
            requisition_id,
            drill_limit=drill_limit,
            drill_offset=drill_offset,
            include_pii=include_pii,
            compare=compare,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )
    if "funnel" in requested:
        result_slices["funnel"] = _funnel_slice(
            db, tenant_id, since, until, requisition_id, include_pii=include_pii
        )
    if "interviews" in requested:
        result_slices["interviews"] = _interviews_slice(
            db, tenant_id, since, until, requisition_id, include_pii=include_pii
        )
    if "team" in requested:
        result_slices["team"] = _team_slice(db, tenant_id, since, until, recruiter_id)
    if "hm" in requested:
        result_slices["hm"] = _hm_slice(
            db, tenant_id, since, until, requisition_id, include_pii=include_pii
        )
    if "leadership" in requested:
        result_slices["leadership"] = _leadership_slice(db, tenant_id)
    if "ats" in requested:
        result_slices["ats"] = _ats_slice(db, tenant_id, since, until)

    funnel = result_slices.get("funnel", {})
    hm = result_slices.get("hm", {})
    leadership = result_slices.get("leadership", {})

    attention = {}
    if user_role not in ("hiring_manager",):
        attention = {
            "stale_candidates": funnel.get("stale_candidates", [])[:10],
            "zero_pipeline_requisitions": leadership.get("risk_flags", {}).get("zero_pipeline", [])[:10],
            "pending_hm_review": hm.get("pending_hm_review", 0),
        }

    return {
        "period": period,
        "start_date": since.date().isoformat(),
        "end_date": until.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "requisition_id": requisition_id,
            "recruiter_id": recruiter_id,
        },
        "filter_options": _filter_options(db, tenant_id),
        "attention": attention,
        "slices": result_slices,
    }


def _screening_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    until: datetime,
    requisition_id: Optional[int],
    *,
    drill_limit: int = 100,
    drill_offset: int = 0,
    include_pii: bool = True,
    compare: bool = False,
    period: str = "last_30_days",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    base_q = screening_base_query(
        db, tenant_id, since, until, requisition_id=requisition_id
    )
    all_rows = base_q.order_by(ScreeningResult.timestamp.desc()).all()
    total_count = len(all_rows)
    metrics = aggregate_screening_rows(all_rows)
    rows = all_rows[drill_offset: drill_offset + drill_limit]

    from app.backend.services.screening_analytics_service import (
        build_jd_effectiveness,
        comparison_range,
        score_to_bucket,
    )
    jd_effectiveness = build_jd_effectiveness(db, metrics.pop("jd_data"))
    trends: dict[str, Any] = {
        "period": period,
        "start_date": since.date().isoformat(),
        "end_date": until.date().isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **metrics,
        "jd_effectiveness": jd_effectiveness,
    }
    if compare:
        comp_since, comp_until = comparison_range(since, until)
        comp_rows = screening_base_query(
            db, tenant_id, comp_since, comp_until, requisition_id=requisition_id
        ).all()
        comp_metrics = aggregate_screening_rows(comp_rows, include_jd_effectiveness=False)
        trends["comparison"] = {
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

    recs: Counter[str] = Counter()
    skill_gaps: Counter[str] = Counter()
    score_buckets: Counter[str] = Counter()
    drill_down: list[dict] = []

    candidate_ids = {r.candidate_id for r in rows if r.candidate_id}
    requisition_ids = {r.requisition_id for r in rows if r.requisition_id}
    candidates = _load_candidates(db, tenant_id, candidate_ids)
    requisitions = _load_requisitions(db, tenant_id, requisition_ids)

    for r in rows:
        analysis = _parse_json(r.analysis_result)
        score = extract_fit_score(r, analysis)
        if score is not None:
            score_buckets[score_to_bucket(score)] += 1
        rec_label = extract_recommendation(r, analysis)
        rec_key = (rec_label or "unscored").lower()
        recs[rec_key] += 1
        for name in iter_skill_gap_names(analysis):
            skill_gaps[name.lower()] += 1

        cand = candidates.get(r.candidate_id) if r.candidate_id else None
        req = requisitions.get(r.requisition_id) if r.requisition_id else None
        parsed = _parse_json(r.parsed_data)
        display_name, display_email = _resolve_candidate_display(
            cand,
            candidate_id=r.candidate_id,
            analysis=analysis,
            parsed=parsed,
        )
        drill_down.append({
            "id": r.id,
            "result_id": r.id,
            "candidate_id": r.candidate_id,
            "candidate_name": display_name,
            "candidate_email": _mask_email(display_email, include_pii=include_pii),
            "requisition_id": r.requisition_id,
            "requisition_title": req.title if req else None,
            "role_title": (req.title if req else None) or analysis.get("job_role"),
            "fit_score": score,
            "recommendation": rec_label,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        })

    return {
        "kpis": {
            "total_analyzed": metrics["total_analyzed"],
            "avg_fit_score": metrics["avg_fit_score"],
            "recommendation_shortlist_rate": metrics["recommendation_shortlist_rate"],
            "pipeline_shortlist_rate": metrics["pipeline_shortlist_rate"],
            "hired_rate": metrics["hired_rate"],
        },
        "recommendation_distribution": dict(recs) or metrics["recommendation_distribution"],
        "score_distribution": dict(score_buckets) or {
            row["range"]: row["count"] for row in metrics["score_distribution"]
        },
        "top_skill_gaps": metrics["top_skill_gaps"],
        "drill_down": drill_down,
        "drill_down_pagination": {
            "total_count": total_count,
            "limit": drill_limit,
            "offset": drill_offset,
            "has_more": drill_offset + drill_limit < total_count,
        },
        "trends": trends,
    }


def _funnel_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    until: datetime,
    requisition_id: Optional[int],
    *,
    include_pii: bool = True,
) -> dict[str, Any]:
    q = (
        db.query(RequisitionCandidate, Requisition)
        .join(Requisition, Requisition.id == RequisitionCandidate.requisition_id)
        .filter(
            Requisition.tenant_id == tenant_id,
            RequisitionCandidate.added_at >= since,
            RequisitionCandidate.added_at <= until,
        )
    )
    if requisition_id:
        q = q.filter(RequisitionCandidate.requisition_id == requisition_id)
    rows = q.all()

    stage_counts: Counter[str] = Counter()
    by_req: dict[int, dict] = {}
    stale: list[dict] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stale_candidate_ids: set[int] = set()

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
            stale_candidate_ids.add(rc.candidate_id)
            stale.append({
                "candidate_id": rc.candidate_id,
                "requisition_id": req.id,
                "requisition_title": req.title,
                "pipeline_status": stage,
                "updated_at": rc.updated_at.isoformat(),
            })

    stale_candidates = _load_candidates(db, tenant_id, stale_candidate_ids)
    for item in stale:
        cand = stale_candidates.get(item["candidate_id"])
        item["candidate_name"] = _candidate_label(cand, item["candidate_id"])
        item["candidate_email"] = _mask_email(
            cand.email if cand else None,
            include_pii=include_pii,
        )

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
    until: datetime,
    requisition_id: Optional[int],
    *,
    include_pii: bool = True,
) -> dict[str, Any]:
    q = db.query(VoiceScreeningSession).filter(
        VoiceScreeningSession.tenant_id == tenant_id,
        VoiceScreeningSession.created_at >= since,
        VoiceScreeningSession.created_at <= until,
    )
    if requisition_id:
        candidate_ids_for_req = set(
            db.query(RequisitionCandidate.candidate_id)
            .filter(RequisitionCandidate.requisition_id == requisition_id)
            .scalars()
            .all()
        )
        candidate_ids_for_req.discard(None)
        if not candidate_ids_for_req:
            return {
                "kpis": {"total_sessions": 0, "completion_rate": 0, "avg_duration_min": 0},
                "status_breakdown": {},
                "resume_vs_call_delta": [],
            }
        q = q.filter(VoiceScreeningSession.candidate_id.in_(candidate_ids_for_req))

    rows = q.all()
    status_counts: Counter[str] = Counter()
    completed = 0
    durations: list[int] = []
    resume_vs_call: list[dict] = []
    interview_candidate_ids: set[int] = set()

    session_candidate_ids = {
        s.candidate_id for s in rows if s.candidate_id and s.assessment_json
    }
    latest_screenings = _latest_screening_by_candidate(
        db,
        tenant_id,
        session_candidate_ids,
        requisition_id=requisition_id,
    )

    for s in rows:
        status_counts[s.status or "unknown"] += 1
        if s.status == "completed":
            completed += 1
            if s.duration_seconds:
                durations.append(s.duration_seconds)
        if s.assessment_json and s.candidate_id:
            try:
                assessment = json.loads(s.assessment_json)
                call_score = assessment.get("overall_score") or assessment.get("score")
                sr = latest_screenings.get(s.candidate_id)
                if call_score is not None and sr:
                    resume_score = extract_fit_score(sr)
                    if resume_score is not None:
                        interview_candidate_ids.add(s.candidate_id)
                        resume_vs_call.append({
                            "candidate_id": s.candidate_id,
                            "resume_score": int(resume_score),
                            "call_score": call_score,
                            "delta": int(call_score) - int(resume_score),
                        })
            except (json.JSONDecodeError, TypeError):
                pass

    interview_candidates = _load_candidates(db, tenant_id, interview_candidate_ids)
    for item in resume_vs_call:
        cand = interview_candidates.get(item["candidate_id"])
        item["candidate_name"] = _candidate_label(cand, item["candidate_id"])
        item["candidate_email"] = _mask_email(
            cand.email if cand else None,
            include_pii=include_pii,
        )

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
    until: datetime,
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
            UsageLog.created_at <= until,
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
        .filter(
            User.tenant_id == tenant_id,
            User.is_active == True,  # noqa: E712
            User.role.in_(("admin", "recruiter")),
        )
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
    until: datetime,
    requisition_id: Optional[int],
    *,
    include_pii: bool = True,
) -> dict[str, Any]:
    q = (
        db.query(RequisitionCandidate)
        .join(Requisition, Requisition.id == RequisitionCandidate.requisition_id)
        .filter(Requisition.tenant_id == tenant_id)
    )
    if requisition_id:
        q = q.filter(RequisitionCandidate.requisition_id == requisition_id)
    rows = q.all()

    submissions_in_period = 0
    outcomes: Counter[str] = Counter()
    pending_review = 0
    turnaround_hours: list[float] = []
    pending_submissions: list[dict] = []
    pending_candidate_ids: set[int] = set()

    for rc in rows:
        submitted_at = _ensure_aware(rc.submitted_at)
        outcome_at = _ensure_aware(rc.outcome_at)
        in_period = (
            submitted_at is not None
            and submitted_at >= since
            and submitted_at <= until
        )
        if in_period and rc.submission_status in ("submitted", "reviewed"):
            submissions_in_period += 1
        if rc.submission_status == "submitted" and not rc.hm_outcome:
            pending_review += 1
            pending_candidate_ids.add(rc.candidate_id)
            pending_submissions.append({
                "candidate_id": rc.candidate_id,
                "requisition_id": rc.requisition_id,
                "submitted_at": rc.submitted_at.isoformat() if rc.submitted_at else None,
            })
        if rc.hm_outcome and outcome_at and since <= outcome_at <= until:
            outcomes[rc.hm_outcome] += 1
        if submitted_at and outcome_at and since <= submitted_at <= until and since <= outcome_at <= until:
            delta = (outcome_at - submitted_at).total_seconds() / 3600
            turnaround_hours.append(delta)

    pending_candidates = _load_candidates(db, tenant_id, pending_candidate_ids)
    pending_req_ids = {item["requisition_id"] for item in pending_submissions}
    pending_reqs = _load_requisitions(db, tenant_id, pending_req_ids)
    for item in pending_submissions:
        cand = pending_candidates.get(item["candidate_id"])
        req = pending_reqs.get(item["requisition_id"])
        item["candidate_name"] = _candidate_label(cand, item["candidate_id"])
        item["candidate_email"] = _mask_email(
            cand.email if cand else None,
            include_pii=include_pii,
        )
        item["requisition_title"] = req.title if req else None

    pending_submissions.sort(
        key=lambda row: row.get("submitted_at") or "",
        reverse=True,
    )

    return {
        "submissions_sent": submissions_in_period,
        "pending_hm_review": pending_review,
        "outcome_distribution": dict(outcomes),
        "pending_submissions": pending_submissions[:30],
        "avg_turnaround_hours": round(sum(turnaround_hours) / len(turnaround_hours), 1)
        if turnaround_hours
        else None,
        "period_note": "Submissions and outcomes respect the selected date range; pending review is current snapshot.",
    }


def _leadership_slice(db: Session, tenant_id: int) -> dict[str, Any]:
    open_reqs = (
        db.query(Requisition)
        .filter(
            Requisition.tenant_id == tenant_id,
            Requisition.status.notin_(("filled", "closed", "cancelled")),
        )
        .all()
    )
    open_req_ids = [r.id for r in open_reqs]
    counts_by_req: dict[int, int] = {}
    if open_req_ids:
        rows = (
            db.query(
                RequisitionCandidate.requisition_id,
                func.count(RequisitionCandidate.id),
            )
            .filter(RequisitionCandidate.requisition_id.in_(open_req_ids))
            .group_by(RequisitionCandidate.requisition_id)
            .all()
        )
        counts_by_req = {rid: int(count) for rid, count in rows}

    zero_pipeline = []
    calibrated_no_screens = []
    for r in open_reqs:
        cand_count = counts_by_req.get(r.id, 0)
        if cand_count == 0:
            zero_pipeline.append({"id": r.id, "title": r.title, "status": r.status})
        if r.calibrated_criteria_json and cand_count == 0:
            calibrated_no_screens.append({"id": r.id, "title": r.title})

    return {
        "open_requisitions": len(open_reqs),
        "period_note": "Executive health reflects current open requisitions (not period-filtered).",
        "risk_flags": {
            "zero_pipeline": zero_pipeline[:20],
            "calibrated_no_candidates": calibrated_no_screens[:20],
        },
    }


def _ats_slice(
    db: Session,
    tenant_id: int,
    since: datetime,
    until: datetime,
) -> dict[str, Any]:
    connections = (
        db.query(ATSConnection)
        .filter(ATSConnection.tenant_id == tenant_id)
        .all()
    )
    conn_by_id = {c.id: c for c in connections}
    logs = (
        db.query(ATSSyncLog)
        .filter(
            ATSSyncLog.tenant_id == tenant_id,
            ATSSyncLog.created_at >= since,
            ATSSyncLog.created_at <= until,
        )
        .order_by(ATSSyncLog.created_at.desc())
        .limit(500)
        .all()
    )

    success = sum(1 for l in logs if l.success)
    failed = sum(1 for l in logs if not l.success)
    by_provider: Counter[str] = Counter()
    errors: Counter[str] = Counter()

    for l in logs:
        conn = conn_by_id.get(l.connection_id)
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
