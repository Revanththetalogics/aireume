"""Custom report builder — templates, filtered exports, BI-ready payloads."""

from __future__ import annotations

import base64
import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.backend.models.db_models import Requisition, RequisitionCandidate, ScreeningResult
from app.backend.services.analytics_hub_service import build_analytics_hub, _since

REPORT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "funnel_by_requisition",
        "name": "Funnel by requisition",
        "description": "Pipeline stage counts per open requisition",
        "slice": "funnel",
    },
    {
        "id": "screening_volume",
        "name": "Screening volume & fit",
        "description": "Analyses, scores, and recommendations",
        "slice": "screening",
    },
    {
        "id": "interview_outcomes",
        "name": "Interview outcomes",
        "description": "AI screen sessions, completion, resume vs call delta",
        "slice": "interviews",
    },
    {
        "id": "hm_submissions",
        "name": "HM submissions & outcomes",
        "description": "Submissions sent, pending review, HM decisions",
        "slice": "hm",
    },
    {
        "id": "team_activity",
        "name": "Team activity",
        "description": "Recruiter workload and throughput",
        "slice": "team",
    },
    {
        "id": "ats_sync_health",
        "name": "ATS sync health",
        "description": "Connection health, failures, error summary",
        "slice": "ats",
    },
    {
        "id": "leadership_risk",
        "name": "Leadership risk flags",
        "description": "Open reqs with zero pipeline or stalled hiring",
        "slice": "leadership",
    },
    {
        "id": "candidate_pipeline_detail",
        "name": "Candidate pipeline detail",
        "description": "Row-level pipeline export for ops",
        "slice": "custom",
    },
]


def list_report_templates() -> list[dict[str, Any]]:
    return REPORT_TEMPLATES


def run_report(
    db: Session,
    tenant_id: int,
    *,
    template_id: str,
    period: str = "last_30_days",
    requisition_id: Optional[int] = None,
    format: str = "json",
) -> dict[str, Any]:
    """Execute a report template and return data or export payload."""
    template = next((t for t in REPORT_TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise ValueError(f"Unknown report template: {template_id}")

    if template_id == "candidate_pipeline_detail":
        rows = _pipeline_detail_rows(db, tenant_id, period, requisition_id)
        payload = {"template_id": template_id, "rows": rows, "row_count": len(rows)}
    else:
        hub = build_analytics_hub(
            db,
            tenant_id,
            period=period,
            requisition_id=requisition_id,
        )
        slice_key = template["slice"]
        payload = {
            "template_id": template_id,
            "template_name": template["name"],
            "period": period,
            "data": hub["slices"].get(slice_key, {}),
        }

    if format == "csv":
        payload["csv"] = _to_csv(payload)
    elif format == "xlsx":
        payload["xlsx_base64"] = base64.b64encode(_to_xlsx(payload)).decode("ascii")

    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    payload["format"] = format
    return payload


def _pipeline_detail_rows(
    db: Session,
    tenant_id: int,
    period: str,
    requisition_id: Optional[int],
) -> list[dict[str, Any]]:
    since = _since(period)
    q = (
        db.query(RequisitionCandidate, Requisition)
        .join(Requisition, Requisition.id == RequisitionCandidate.requisition_id)
        .filter(Requisition.tenant_id == tenant_id, RequisitionCandidate.added_at >= since)
    )
    if requisition_id:
        q = q.filter(RequisitionCandidate.requisition_id == requisition_id)
    out = []
    for rc, req in q.all():
        out.append({
            "requisition_id": req.id,
            "requisition_title": req.title,
            "candidate_id": rc.candidate_id,
            "pipeline_status": rc.pipeline_status,
            "submission_status": rc.submission_status,
            "hm_outcome": rc.hm_outcome,
            "added_at": rc.added_at.isoformat() if rc.added_at else None,
        })
    return out


def _to_csv(payload: dict[str, Any]) -> str:
    buf = io.StringIO()
    if "rows" in payload and payload["rows"]:
        writer = csv.DictWriter(buf, fieldnames=payload["rows"][0].keys())
        writer.writeheader()
        writer.writerows(payload["rows"])
    else:
        buf.write(json.dumps(payload.get("data", payload), indent=2))
    return buf.getvalue()


def _to_xlsx(payload: dict[str, Any]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    if "rows" in payload and payload["rows"]:
        rows = payload["rows"]
        headers = list(rows[0].keys())
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
    else:
        data = payload.get("data", payload)
        if isinstance(data, dict):
            ws.append(["key", "value"])
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                ws.append([key, value])
        else:
            ws.append(["data"])
            ws.append([json.dumps(data)])

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def bi_export_manifest(tenant_id: int) -> dict[str, Any]:
    """Semantic layer field dictionary for BI tools."""
    return {
        "tenant_id": tenant_id,
        "entities": {
            "screening_results": [
                "id", "candidate_id", "requisition_id", "deterministic_score",
                "status", "call_fit_score", "consolidated_recommendation", "timestamp",
            ],
            "requisition_candidates": [
                "requisition_id", "candidate_id", "pipeline_status",
                "submission_status", "hm_outcome", "added_at",
            ],
            "requisitions": [
                "id", "title", "status", "current_criteria_version", "calibrated_at",
            ],
            "ats_sync_logs": [
                "connection_id", "direction", "entity_type", "success", "error_message", "created_at",
            ],
        },
        "export_endpoints": {
            "hub": "/api/analytics/hub",
            "report_run": "/api/analytics/reports/run",
            "report_templates": "/api/analytics/reports/templates",
        },
    }
