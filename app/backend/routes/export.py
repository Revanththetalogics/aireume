"""
ATS Export — CSV and Excel export of screening results.
"""
import json
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import (
    ScreeningResult, User, RoleTemplate, Candidate,
    OverallAssessment, InterviewEvaluation,
)

router = APIRouter(prefix="/api", tags=["export"])


def _fetch_results(db: Session, tenant_id: int, ids: list[int] | None):
    query = db.query(ScreeningResult).filter(ScreeningResult.tenant_id == tenant_id)
    if ids:
        query = query.filter(ScreeningResult.id.in_(ids))
    return query.order_by(ScreeningResult.timestamp.desc()).all()


def _results_to_rows(results: list) -> list[dict]:
    rows = []
    for r in results:
        analysis = json.loads(r.analysis_result)
        parsed   = json.loads(r.parsed_data)
        contact  = parsed.get("contact_info", {})
        rows.append({
            "ID":                   r.id,
            "Timestamp":            r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "",
            "Candidate Name":       contact.get("name", ""),
            "Email":                contact.get("email", ""),
            "Phone":                contact.get("phone", ""),
            "Fit Score":            analysis.get("fit_score", ""),
            "Recommendation":       analysis.get("final_recommendation", ""),
            "Risk Level":           analysis.get("risk_level", ""),
            "Status":               r.status or "pending",
            "Skill Match %":        analysis.get("score_breakdown", {}).get("skill_match", ""),
            "Experience Match %":   analysis.get("score_breakdown", {}).get("experience_match", ""),
            "Stability %":          analysis.get("score_breakdown", {}).get("stability", ""),
            "Education %":          analysis.get("score_breakdown", {}).get("education", ""),
            "Matched Skills":       ", ".join(analysis.get("matched_skills", [])),
            "Missing Skills":       ", ".join(analysis.get("missing_skills", [])),
            "Strengths":            " | ".join(analysis.get("strengths", [])),
            "Weaknesses":           " | ".join(analysis.get("weaknesses", [])),
        })
    return rows


@router.get("/export/csv")
def export_csv(
    ids: Optional[str] = Query(None, description="Comma-separated result IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    results = _fetch_results(db, current_user.tenant_id, id_list)
    rows    = _results_to_rows(results)

    import csv
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    output.seek(0)
    filename = f"aria_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/excel")
def export_excel(
    ids: Optional[str] = Query(None, description="Comma-separated result IDs"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import pandas as pd

    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()] if ids else None
    results = _fetch_results(db, current_user.tenant_id, id_list)
    rows    = _results_to_rows(results)

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Screening Results")
    output.seek(0)

    filename = f"aria_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


from app.backend.services.handoff_service import build_handoff_package


@router.get("/jd/{jd_id}/handoff-package")
async def get_handoff_package(
    jd_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a structured HM Handoff Package for shortlisted candidates."""
    package = build_handoff_package(
        db,
        tenant_id=current_user.tenant_id,
        jd_id=jd_id,
        viewer_user_id=current_user.id,
        generated_by_email=current_user.email,
    )
    if not package:
        raise HTTPException(status_code=404, detail="Job description not found")
    return package


# ─── Enterprise PDF Report ──────────────────────────────────────────────────

@router.get("/export/{result_id}/pdf-report")
def download_pdf_report(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and download an enterprise PDF report for a single screening result."""
    import logging
    log = logging.getLogger(__name__)

    from ..services.pdf_report_service import generate_pdf_report

    # Verify user has access to this result (same tenant)
    result = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.id == result_id,
            ScreeningResult.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    try:
        pdf_bytes = generate_pdf_report(result_id, db, current_user.id)
    except Exception as e:
        log.exception("PDF report generation failed for result_id=%s: %s", result_id, str(e))
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(e)}"
        )

    candidate_name = "Candidate"
    if result.analysis_result:
        ar = (
            json.loads(result.analysis_result)
            if isinstance(result.analysis_result, str)
            else result.analysis_result
        )
        candidate_name = ar.get("candidate_name", "Candidate").replace(" ", "_")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename={candidate_name}_Assessment_Report.pdf"
            )
        },
    )


# ─── Adverse Action Report ───────────────────────────────────────────────────

@router.get("/export/{result_id}/adverse-action")
def get_adverse_action_report(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an EEOC-compliant adverse action report for a screening result."""
    from app.backend.services.adverse_action_service import get_adverse_action_service

    result = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.id == result_id,
            ScreeningResult.tenant_id == current_user.tenant_id,
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    analysis = (
        json.loads(result.analysis_result)
        if isinstance(result.analysis_result, str)
        else result.analysis_result
    )

    candidate_name = None
    if result.candidate_id:
        candidate = db.query(Candidate).filter(Candidate.id == result.candidate_id).first()
        if candidate:
            candidate_name = candidate.name

    service = get_adverse_action_service()
    report = service.generate_report(
        analysis_result=analysis,
        transcript_text=result.resume_text or "",
        jd_text=result.jd_text or "",
        candidate_id=result.candidate_id,
        candidate_name=candidate_name,
    )
    return report
