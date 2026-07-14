"""Custom report builder — field catalog, column picker, group-by, exports."""

from __future__ import annotations

import base64
import csv
import io
import json
import secrets
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    ATSSyncLog,
    Candidate,
    Requisition,
    RequisitionCandidate,
    SavedReport,
    ScreeningResult,
    ScheduledReport,
    UsageLog,
    User,
    VoiceScreeningSession,
)
from app.backend.services.report_builder_service import _to_csv, _to_xlsx, list_report_templates, run_report
from app.backend.services.screening_analytics_service import resolve_date_range

FIELD_CATALOG: dict[str, dict[str, Any]] = {
    "screening_results": {
        "label": "Screening analyses",
        "description": "Resume screening results with scores and recommendations",
        "columns": [
            {"key": "id", "label": "Analysis ID", "type": "integer"},
            {"key": "candidate_id", "label": "Candidate ID", "type": "integer"},
            {"key": "candidate_name", "label": "Candidate name", "type": "string"},
            {"key": "requisition_id", "label": "Requisition ID", "type": "integer"},
            {"key": "requisition_title", "label": "Requisition title", "type": "string"},
            {"key": "deterministic_score", "label": "Fit score", "type": "number"},
            {"key": "status", "label": "Pipeline status", "type": "string"},
            {"key": "consolidated_recommendation", "label": "AI recommendation", "type": "string"},
            {"key": "call_fit_score", "label": "Call fit score", "type": "number"},
            {"key": "timestamp", "label": "Analyzed at", "type": "datetime"},
        ],
        "group_by_options": ["requisition_title", "status", "consolidated_recommendation"],
    },
    "requisition_candidates": {
        "label": "Pipeline candidates",
        "description": "Candidates on requisitions with pipeline and HM status",
        "columns": [
            {"key": "requisition_id", "label": "Requisition ID", "type": "integer"},
            {"key": "requisition_title", "label": "Requisition title", "type": "string"},
            {"key": "candidate_id", "label": "Candidate ID", "type": "integer"},
            {"key": "candidate_name", "label": "Candidate name", "type": "string"},
            {"key": "pipeline_status", "label": "Pipeline status", "type": "string"},
            {"key": "submission_status", "label": "Submission status", "type": "string"},
            {"key": "hm_outcome", "label": "HM outcome", "type": "string"},
            {"key": "added_at", "label": "Added at", "type": "datetime"},
        ],
        "group_by_options": ["requisition_title", "pipeline_status", "submission_status", "hm_outcome"],
    },
    "requisitions": {
        "label": "Requisitions",
        "description": "Open and closed requisitions",
        "columns": [
            {"key": "id", "label": "Requisition ID", "type": "integer"},
            {"key": "title", "label": "Title", "type": "string"},
            {"key": "status", "label": "Status", "type": "string"},
            {"key": "candidate_count", "label": "Candidate count", "type": "integer"},
            {"key": "calibrated_at", "label": "Calibrated at", "type": "datetime"},
            {"key": "created_at", "label": "Created at", "type": "datetime"},
        ],
        "group_by_options": ["status"],
    },
    "interviews": {
        "label": "AI interviews",
        "description": "Voice screening session outcomes",
        "columns": [
            {"key": "id", "label": "Session ID", "type": "integer"},
            {"key": "candidate_id", "label": "Candidate ID", "type": "integer"},
            {"key": "status", "label": "Status", "type": "string"},
            {"key": "fit_score", "label": "Call fit score", "type": "number"},
            {"key": "resume_score", "label": "Resume score", "type": "number"},
            {"key": "created_at", "label": "Created at", "type": "datetime"},
            {"key": "completed_at", "label": "Completed at", "type": "datetime"},
        ],
        "group_by_options": ["status"],
    },
    "team_activity": {
        "label": "Team activity",
        "description": "Recruiter analysis volume",
        "columns": [
            {"key": "user_id", "label": "User ID", "type": "integer"},
            {"key": "user_email", "label": "Email", "type": "string"},
            {"key": "analyses", "label": "Analyses", "type": "integer"},
            {"key": "period", "label": "Period", "type": "string"},
        ],
        "group_by_options": ["user_email"],
    },
    "ats_sync_logs": {
        "label": "ATS sync logs",
        "description": "Integration sync attempts and failures",
        "columns": [
            {"key": "connection_id", "label": "Connection ID", "type": "integer"},
            {"key": "direction", "label": "Direction", "type": "string"},
            {"key": "entity_type", "label": "Entity type", "type": "string"},
            {"key": "success", "label": "Success", "type": "boolean"},
            {"key": "error_message", "label": "Error", "type": "string"},
            {"key": "created_at", "label": "Created at", "type": "datetime"},
        ],
        "group_by_options": ["entity_type", "success"],
    },
}

VALID_ENTITIES = frozenset(FIELD_CATALOG.keys())
VALID_SCHEDULES = frozenset({"daily", "weekly", "monthly"})


def get_field_catalog() -> dict[str, Any]:
    return {
        "entities": FIELD_CATALOG,
        "templates": list_report_templates(),
    }


def _fetch_entity_rows(
    db: Session,
    tenant_id: int,
    entity: str,
    since: datetime,
    until: datetime,
    *,
    requisition_id: Optional[int] = None,
    recruiter_id: Optional[int] = None,
    include_pii: bool = True,
) -> list[dict[str, Any]]:
    if entity == "screening_results":
        q = (
            db.query(ScreeningResult, Candidate, Requisition)
            .outerjoin(Candidate, Candidate.id == ScreeningResult.candidate_id)
            .outerjoin(Requisition, Requisition.id == ScreeningResult.requisition_id)
            .filter(
                ScreeningResult.tenant_id == tenant_id,
                ScreeningResult.timestamp >= since,
                ScreeningResult.timestamp <= until,
            )
        )
        if requisition_id:
            q = q.filter(ScreeningResult.requisition_id == requisition_id)
        rows = []
        for sr, cand, req in q.all():
            rows.append({
                "id": sr.id,
                "candidate_id": sr.candidate_id,
                "candidate_name": cand.name if cand and include_pii else f"Candidate #{sr.candidate_id}",
                "requisition_id": sr.requisition_id,
                "requisition_title": req.title if req else None,
                "deterministic_score": sr.deterministic_score,
                "status": sr.status,
                "consolidated_recommendation": sr.consolidated_recommendation,
                "call_fit_score": sr.call_fit_score,
                "timestamp": sr.timestamp.isoformat() if sr.timestamp else None,
            })
        return rows

    if entity == "requisition_candidates":
        q = (
            db.query(RequisitionCandidate, Requisition, Candidate)
            .join(Requisition, Requisition.id == RequisitionCandidate.requisition_id)
            .outerjoin(Candidate, Candidate.id == RequisitionCandidate.candidate_id)
            .filter(
                Requisition.tenant_id == tenant_id,
                RequisitionCandidate.added_at >= since,
                RequisitionCandidate.added_at <= until,
            )
        )
        if requisition_id:
            q = q.filter(RequisitionCandidate.requisition_id == requisition_id)
        return [
            {
                "requisition_id": req.id,
                "requisition_title": req.title,
                "candidate_id": rc.candidate_id,
                "candidate_name": cand.name if cand and include_pii else f"Candidate #{rc.candidate_id}",
                "pipeline_status": rc.pipeline_status,
                "submission_status": rc.submission_status,
                "hm_outcome": rc.hm_outcome,
                "added_at": rc.added_at.isoformat() if rc.added_at else None,
            }
            for rc, req, cand in q.all()
        ]

    if entity == "requisitions":
        q = db.query(Requisition).filter(
            Requisition.tenant_id == tenant_id,
            Requisition.created_at >= since,
            Requisition.created_at <= until,
        )
        if requisition_id:
            q = q.filter(Requisition.id == requisition_id)
        reqs = q.all()
        counts = {}
        if reqs:
            from sqlalchemy import func
            count_rows = (
                db.query(RequisitionCandidate.requisition_id, func.count(RequisitionCandidate.id))
                .filter(RequisitionCandidate.requisition_id.in_([r.id for r in reqs]))
                .group_by(RequisitionCandidate.requisition_id)
                .all()
            )
            counts = dict(count_rows)
        return [
            {
                "id": r.id,
                "title": r.title,
                "status": r.status,
                "candidate_count": counts.get(r.id, 0),
                "calibrated_at": r.calibrated_at.isoformat() if r.calibrated_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reqs
        ]

    if entity == "interviews":
        q = db.query(VoiceScreeningSession).filter(
            VoiceScreeningSession.tenant_id == tenant_id,
            VoiceScreeningSession.created_at >= since,
            VoiceScreeningSession.created_at <= until,
        )
        rows = []
        for s in q.all():
            fit_score = None
            if s.assessment_json:
                try:
                    assessment = json.loads(s.assessment_json)
                    fit_score = assessment.get("overall_score") or assessment.get("score")
                except (json.JSONDecodeError, TypeError):
                    pass
            rows.append({
                "id": s.id,
                "candidate_id": s.candidate_id,
                "status": s.status,
                "fit_score": fit_score,
                "resume_score": None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "completed_at": s.ended_at.isoformat() if s.ended_at else None,
            })
        return rows

    if entity == "team_activity":
        q = (
            db.query(UsageLog.user_id, User.email, UsageLog.quantity)
            .join(User, User.id == UsageLog.user_id)
            .filter(
                UsageLog.tenant_id == tenant_id,
                UsageLog.action == "resume_analysis",
                UsageLog.created_at >= since,
                UsageLog.created_at <= until,
            )
        )
        if recruiter_id:
            q = q.filter(UsageLog.user_id == recruiter_id)
        totals: dict[int, dict] = {}
        for user_id, email, qty in q.all():
            if user_id not in totals:
                totals[user_id] = {"user_id": user_id, "user_email": email if include_pii else f"User #{user_id}", "analyses": 0}
            totals[user_id]["analyses"] += qty or 0
        return list(totals.values())

    if entity == "ats_sync_logs":
        return [
            {
                "connection_id": log.connection_id,
                "direction": log.direction,
                "entity_type": log.entity_type,
                "success": log.success,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in db.query(ATSSyncLog).filter(
                ATSSyncLog.tenant_id == tenant_id,
                ATSSyncLog.created_at >= since,
                ATSSyncLog.created_at <= until,
            ).all()
        ]

    raise ValueError(f"Unknown entity: {entity}")


def _apply_group_by(rows: list[dict], group_by: list[str]) -> list[dict]:
    if not group_by or not rows:
        return rows
    buckets: dict[tuple, list] = defaultdict(list)
    for row in rows:
        key = tuple(row.get(g, "") for g in group_by)
        buckets[key].append(row)
    out = []
    for key, group_rows in sorted(buckets.items(), key=lambda x: -len(x[1])):
        entry = {g: key[i] for i, g in enumerate(group_by)}
        entry["row_count"] = len(group_rows)
        out.append(entry)
    return out


def _pick_columns(rows: list[dict], columns: list[str]) -> list[dict]:
    if not columns:
        return rows
    return [{c: row.get(c) for c in columns} for row in rows]


def run_custom_report(
    db: Session,
    tenant_id: int,
    definition: dict[str, Any],
    *,
    include_pii: bool = True,
    format: str = "json",
) -> dict[str, Any]:
    """Execute a custom report definition."""
    entity = definition.get("entity") or definition.get("template_id")
    if definition.get("template_id") and not definition.get("entity"):
        return run_report(
            db,
            tenant_id,
            template_id=definition["template_id"],
            period=definition.get("period", "last_30_days"),
            requisition_id=definition.get("requisition_id"),
            recruiter_id=definition.get("recruiter_id"),
            format=format,
        )

    if entity not in VALID_ENTITIES:
        raise ValueError(f"entity must be one of {sorted(VALID_ENTITIES)}")

    period = definition.get("period", "last_30_days")
    since, until = resolve_date_range(
        period=period,
        start_date=definition.get("start_date"),
        end_date=definition.get("end_date"),
    )

    rows = _fetch_entity_rows(
        db,
        tenant_id,
        entity,
        since,
        until,
        requisition_id=definition.get("requisition_id"),
        recruiter_id=definition.get("recruiter_id"),
        include_pii=include_pii,
    )

    columns = definition.get("columns") or [c["key"] for c in FIELD_CATALOG[entity]["columns"]]
    group_by = definition.get("group_by") or []

    if group_by:
        rows = _apply_group_by(rows, group_by)
        columns = group_by + ["row_count"]
    else:
        rows = _pick_columns(rows, columns)

    payload: dict[str, Any] = {
        "entity": entity,
        "columns": columns,
        "group_by": group_by or None,
        "rows": rows,
        "row_count": len(rows),
        "period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": format,
    }

    if format == "csv":
        payload["csv"] = _to_csv(payload)
    elif format == "xlsx":
        payload["xlsx_base64"] = base64.b64encode(_to_xlsx(payload)).decode("ascii")

    return payload


# ── Saved reports CRUD ────────────────────────────────────────────────────────

def _serialize_report(row: SavedReport, *, include_definition: bool = True) -> dict[str, Any]:
    out = {
        "id": row.id,
        "name": row.name,
        "shared_with_tenant": row.shared_with_tenant,
        "share_token": row.share_token if row.shared_with_tenant else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "owner_user_id": row.user_id,
    }
    if include_definition:
        out["definition"] = row.definition or {}
    return out


def list_saved_reports(db: Session, tenant_id: int, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(SavedReport)
        .filter(
            SavedReport.tenant_id == tenant_id,
            (SavedReport.user_id == user_id) | (SavedReport.shared_with_tenant.is_(True)),
        )
        .order_by(SavedReport.updated_at.desc())
        .all()
    )
    return [_serialize_report(r) for r in rows]


def create_saved_report(
    db: Session,
    tenant_id: int,
    user_id: int,
    *,
    name: str,
    definition: dict,
) -> dict[str, Any]:
    row = SavedReport(
        tenant_id=tenant_id,
        user_id=user_id,
        name=name.strip(),
        definition=definition,
    )
    db.add(row)
    db.flush()
    return _serialize_report(row)


def update_saved_report(
    db: Session,
    tenant_id: int,
    user_id: int,
    report_id: int,
    *,
    name: Optional[str] = None,
    definition: Optional[dict] = None,
) -> dict[str, Any]:
    row = (
        db.query(SavedReport)
        .filter(SavedReport.id == report_id, SavedReport.tenant_id == tenant_id, SavedReport.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("Saved report not found")
    if name is not None:
        row.name = name.strip()
    if definition is not None:
        row.definition = definition
    db.flush()
    return _serialize_report(row)


def delete_saved_report(db: Session, tenant_id: int, user_id: int, report_id: int) -> None:
    row = (
        db.query(SavedReport)
        .filter(SavedReport.id == report_id, SavedReport.tenant_id == tenant_id, SavedReport.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("Saved report not found")
    db.query(ScheduledReport).filter(ScheduledReport.saved_report_id == report_id).delete()
    db.delete(row)


def share_saved_report(db: Session, tenant_id: int, user_id: int, report_id: int) -> dict[str, Any]:
    row = (
        db.query(SavedReport)
        .filter(SavedReport.id == report_id, SavedReport.tenant_id == tenant_id, SavedReport.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("Saved report not found")
    row.shared_with_tenant = True
    if not row.share_token:
        row.share_token = secrets.token_urlsafe(32)
    db.flush()
    return _serialize_report(row)


def unshare_saved_report(db: Session, tenant_id: int, user_id: int, report_id: int) -> dict[str, Any]:
    row = (
        db.query(SavedReport)
        .filter(SavedReport.id == report_id, SavedReport.tenant_id == tenant_id, SavedReport.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("Saved report not found")
    row.shared_with_tenant = False
    db.flush()
    return _serialize_report(row)


# ── Scheduled reports ─────────────────────────────────────────────────────────

def _next_run_from_schedule(schedule: str, *, after: Optional[datetime] = None) -> datetime:
    from datetime import timedelta
    base = after or datetime.now(timezone.utc)
    if schedule == "daily":
        return base + timedelta(days=1)
    if schedule == "weekly":
        return base + timedelta(weeks=1)
    if schedule == "monthly":
        return base + timedelta(days=30)
    raise ValueError(f"schedule must be one of {sorted(VALID_SCHEDULES)}")


def _serialize_schedule(row: ScheduledReport) -> dict[str, Any]:
    return {
        "id": row.id,
        "saved_report_id": row.saved_report_id,
        "schedule": row.schedule,
        "recipients": row.recipients or [],
        "enabled": row.enabled,
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def list_scheduled_reports(db: Session, tenant_id: int, user_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(ScheduledReport)
        .filter(ScheduledReport.tenant_id == tenant_id, ScheduledReport.user_id == user_id)
        .order_by(ScheduledReport.next_run_at.asc())
        .all()
    )
    return [_serialize_schedule(r) for r in rows]


def create_scheduled_report(
    db: Session,
    tenant_id: int,
    user_id: int,
    *,
    saved_report_id: int,
    schedule: str,
    recipients: list[str],
) -> dict[str, Any]:
    if schedule not in VALID_SCHEDULES:
        raise ValueError(f"schedule must be one of {sorted(VALID_SCHEDULES)}")
    report = (
        db.query(SavedReport)
        .filter(SavedReport.id == saved_report_id, SavedReport.tenant_id == tenant_id)
        .first()
    )
    if not report:
        raise ValueError("Saved report not found")
    if report.user_id != user_id and not report.shared_with_tenant:
        raise ValueError("Cannot schedule a report you do not own")

    row = ScheduledReport(
        tenant_id=tenant_id,
        user_id=user_id,
        saved_report_id=saved_report_id,
        schedule=schedule,
        recipients=recipients,
        enabled=True,
        next_run_at=_next_run_from_schedule(schedule),
    )
    db.add(row)
    db.flush()
    return _serialize_schedule(row)


def update_scheduled_report(
    db: Session,
    tenant_id: int,
    user_id: int,
    schedule_id: int,
    *,
    schedule: Optional[str] = None,
    recipients: Optional[list[str]] = None,
    enabled: Optional[bool] = None,
) -> dict[str, Any]:
    row = (
        db.query(ScheduledReport)
        .filter(ScheduledReport.id == schedule_id, ScheduledReport.tenant_id == tenant_id, ScheduledReport.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("Scheduled report not found")
    if schedule is not None:
        if schedule not in VALID_SCHEDULES:
            raise ValueError(f"schedule must be one of {sorted(VALID_SCHEDULES)}")
        row.schedule = schedule
        row.next_run_at = _next_run_from_schedule(schedule)
    if recipients is not None:
        row.recipients = recipients
    if enabled is not None:
        row.enabled = enabled
    db.flush()
    return _serialize_schedule(row)


def delete_scheduled_report(db: Session, tenant_id: int, user_id: int, schedule_id: int) -> None:
    row = (
        db.query(ScheduledReport)
        .filter(ScheduledReport.id == schedule_id, ScheduledReport.tenant_id == tenant_id, ScheduledReport.user_id == user_id)
        .first()
    )
    if not row:
        raise ValueError("Scheduled report not found")
    db.delete(row)


def process_due_scheduled_reports(db: Session) -> int:
    """Run all due scheduled reports and email CSV attachments."""
    now = datetime.now(timezone.utc)
    due = (
        db.query(ScheduledReport)
        .filter(
            ScheduledReport.enabled.is_(True),
            ScheduledReport.next_run_at <= now,
        )
        .all()
    )
    if not due:
        return 0

    from app.backend.services.email_service import email_service, get_tenant_email_service

    sent = 0
    for sched in due:
        report = db.query(SavedReport).filter(SavedReport.id == sched.saved_report_id).first()
        if not report:
            continue
        try:
            result = run_custom_report(
                db,
                sched.tenant_id,
                report.definition or {},
                include_pii=True,
                format="csv",
            )
            csv_body = result.get("csv", "")
            subject = f"Scheduled report: {report.name}"
            html = f"<p>Your scheduled analytics report <strong>{report.name}</strong> is attached below.</p><pre>{csv_body[:5000]}</pre>"
            svc = get_tenant_email_service(db, sched.tenant_id) or email_service
            for recipient in sched.recipients or []:
                if recipient:
                    svc.send_email(recipient, subject, html)
            sched.last_run_at = now
            sched.next_run_at = _next_run_from_schedule(sched.schedule, after=now)
            sent += 1
        except Exception:
            sched.next_run_at = _next_run_from_schedule(sched.schedule, after=now)
    db.commit()
    return sent
