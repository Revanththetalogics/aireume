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


# ─── HM Handoff Package ─────────────────────────────────────────────────────

# Dimensions shown in the comparison matrix (display name → JSON key in score_breakdown)
_MATRIX_DIMENSIONS = [
    ("Skill Match",  "skill_match"),
    ("Experience",   "experience_match"),
    ("Education",    "education"),
    ("Domain Fit",   "domain_fit"),
    ("Timeline",     "timeline"),
]


def _safe_json(text: str | None) -> dict:
    """Parse JSON text, returning empty dict on failure."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _build_interview_scores(db: Session, result_id: int) -> dict:
    """Build per-category interview evaluation summary for a screening result."""
    rows = (
        db.query(
            InterviewEvaluation.question_category,
            InterviewEvaluation.rating,
            func.count(InterviewEvaluation.id),
        )
        .filter(InterviewEvaluation.result_id == result_id)
        .group_by(InterviewEvaluation.question_category, InterviewEvaluation.rating)
        .all()
    )
    # Organise: { category: { rating: count, ... }, ... }
    by_cat: dict[str, dict[str, int]] = {}
    for category, rating, count in rows:
        by_cat.setdefault(category, {})[rating] = count

    # Compute average impression per category
    out: dict[str, dict] = {}
    for category, rating_counts in by_cat.items():
        # Determine average impression: pick the most frequent rating
        avg_impression = max(rating_counts, key=rating_counts.get) if rating_counts else ""
        out[category] = {
            "rating_counts": rating_counts,
            "avg_impression": avg_impression,
        }
    return out


@router.get("/jd/{jd_id}/handoff-package")
async def get_handoff_package(
    jd_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return a structured HM Handoff Package for all shortlisted candidates
    under a given Job Description (role template).
    """
    # 1. Verify JD exists and belongs to tenant
    jd = db.query(RoleTemplate).filter(
        RoleTemplate.id == jd_id,
        RoleTemplate.tenant_id == current_user.tenant_id,
    ).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    # 2. Query shortlisted, active results for this JD
    results = (
        db.query(ScreeningResult)
        .join(Candidate, ScreeningResult.candidate_id == Candidate.id)
        .filter(
            ScreeningResult.role_template_id == jd_id,
            ScreeningResult.status == "shortlisted",
            ScreeningResult.is_active == True,
            ScreeningResult.tenant_id == current_user.tenant_id,
        )
        .all()
    )

    # 3. Pre-load OverallAssessment for current user in bulk
    result_ids = [r.id for r in results]
    assessments_rows: list[OverallAssessment] = []
    if result_ids:
        assessments_rows = (
            db.query(OverallAssessment)
            .filter(
                OverallAssessment.result_id.in_(result_ids),
                OverallAssessment.user_id == current_user.id,
            )
            .all()
        )
    assessment_map: dict[int, OverallAssessment] = {a.result_id: a for a in assessments_rows}

    # 4. Build candidate entries + comparison matrix data
    shortlisted_candidates = []
    comparison_candidates: dict[str, list] = {}

    for r in results:
        analysis = _safe_json(r.analysis_result)
        parsed   = _safe_json(r.parsed_data)
        sb       = analysis.get("score_breakdown", {})

        # Candidate info (from joined relationship)
        cand = r.candidate
        cand_name = getattr(cand, "name", None) or parsed.get("contact_info", {}).get("name", "Unknown")
        current_role = getattr(cand, "current_role", None) or ""
        total_years  = getattr(cand, "total_years_exp", None)

        # Experience summary — prefer analysis, fallback to candidate parsed data
        experience_summary = ""
        work_exp_list = analysis.get("work_experience", []) or []
        if not work_exp_list:
            try:
                work_exp_raw = getattr(cand, "parsed_work_exp", None)
                work_exp_list = json.loads(work_exp_raw) if work_exp_raw else []
            except (json.JSONDecodeError, TypeError):
                work_exp_list = []
        if isinstance(work_exp_list, list) and work_exp_list:
            first = work_exp_list[0] if isinstance(work_exp_list[0], dict) else {}
            experience_summary = first.get("title", "") or first.get("summary", "")
            if first.get("company"):
                experience_summary = f"{experience_summary} at {first['company']}".strip()
        if not experience_summary:
            total = total_years or analysis.get("_required_years")
            if total:
                experience_summary = f"{total} years of experience"

        # Education summary
        education_summary = analysis.get("education_analysis", "")
        if not education_summary:
            edu_list = []
            try:
                edu_raw = getattr(cand, "parsed_education", None)
                edu_list = json.loads(edu_raw) if edu_raw else []
            except (json.JSONDecodeError, TypeError):
                edu_list = []
            if isinstance(edu_list, list) and edu_list:
                first_edu = edu_list[0] if isinstance(edu_list[0], dict) else {}
                education_summary = ", ".join(
                    v for v in [
                        first_edu.get("degree", ""),
                        first_edu.get("institution", ""),
                    ] if v
                )

        # Recruiter notes & recommendation from OverallAssessment
        oa = assessment_map.get(r.id)
        recruiter_notes = getattr(oa, "overall_assessment", None) or ""
        recruiter_rec   = getattr(oa, "recruiter_recommendation", None) or ""

        # Interview scores
        interview_scores = _build_interview_scores(db, r.id)

        # Build candidate entry
        shortlisted_candidates.append({
            "candidate_id":             cand.id if cand else None,
            "result_id":                r.id,
            "name":                     cand_name,
            "fit_score":                analysis.get("fit_score"),
            "recommendation":           analysis.get("final_recommendation", ""),
            "strengths":                analysis.get("strengths", []),
            "weaknesses":               analysis.get("weaknesses", []),
            "matched_skills":           analysis.get("matched_skills", []),
            "missing_skills":           analysis.get("missing_skills", []),
            "experience_summary":       experience_summary,
            "education_summary":        education_summary,
            "current_role":             current_role,
            "total_years_exp":          total_years,
            "recruiter_notes":          recruiter_notes,
            "recruiter_recommendation": recruiter_rec,
            "interview_scores":         interview_scores,
        })

        # Comparison matrix row — fall back to `stability` for Timeline
        dim_values = []
        for _label, key in _MATRIX_DIMENSIONS:
            val = sb.get(key)
            if val is None and key == "timeline":
                val = sb.get("stability")
            dim_values.append(val if val is not None else 0)
        comparison_candidates[cand_name] = dim_values

    # 5. Assemble response
    return {
        "jd_name":               jd.name,
        "jd_id":                 jd.id,
        "generated_at":          datetime.now(timezone.utc).isoformat(),
        "generated_by":          current_user.email,
        "shortlisted_candidates": shortlisted_candidates,
        "comparison_matrix": {
            "dimensions": [label for label, _key in _MATRIX_DIMENSIONS],
            "candidates": comparison_candidates,
        },
        "total_shortlisted":     len(shortlisted_candidates),
    }
