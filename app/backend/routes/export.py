"""
ATS Export — CSV and Excel export of screening results.
"""
import json
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User

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
