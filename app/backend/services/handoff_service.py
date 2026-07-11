"""Build HM handoff packages for authenticated and public magic-link access."""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    Candidate,
    InterviewEvaluation,
    OverallAssessment,
    Requisition,
    RoleTemplate,
    ScreeningResult,
    User,
)

_MATRIX_DIMENSIONS = [
    ("Skill Match", "skill_match"),
    ("Experience", "experience_match"),
    ("Education", "education"),
    ("Domain Fit", "domain_fit"),
    ("Timeline", "timeline"),
]


def _safe_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _build_interview_scores(db: Session, result_id: int) -> dict:
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
    by_cat: dict[str, dict[str, int]] = {}
    for category, rating, count in rows:
        by_cat.setdefault(category, {})[rating] = count

    out: dict[str, dict] = {}
    for category, rating_counts in by_cat.items():
        avg_impression = max(rating_counts, key=rating_counts.get) if rating_counts else ""
        out[category] = {
            "rating_counts": rating_counts,
            "avg_impression": avg_impression,
        }
    return out


def build_handoff_package(
    db: Session,
    *,
    tenant_id: int,
    jd_id: Optional[int] = None,
    requisition_id: Optional[int] = None,
    viewer_user_id: Optional[int] = None,
    generated_by_email: Optional[str] = None,
    public_view: bool = False,
) -> dict:
    """Return structured HM handoff data for a requisition or legacy role template."""
    title = ""
    req = None
    jd = None

    if requisition_id:
        req = db.query(Requisition).filter(
            Requisition.id == requisition_id,
            Requisition.tenant_id == tenant_id,
        ).first()
        if not req:
            return None
        title = req.title
        results_q = db.query(ScreeningResult).join(
            Candidate, ScreeningResult.candidate_id == Candidate.id,
        ).filter(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.is_active == True,
            ScreeningResult.status == "shortlisted",
        )
        results_q = results_q.filter(
            (ScreeningResult.requisition_id == requisition_id)
            | (ScreeningResult.role_template_id == req.legacy_role_template_id)
        )
        results = results_q.all()
        entity_id = requisition_id
        entity_type = "requisition"
    elif jd_id:
        jd = db.query(RoleTemplate).filter(
            RoleTemplate.id == jd_id,
            RoleTemplate.tenant_id == tenant_id,
        ).first()
        if not jd:
            return None
        title = jd.name
        results = (
            db.query(ScreeningResult)
            .join(Candidate, ScreeningResult.candidate_id == Candidate.id)
            .filter(
                ScreeningResult.role_template_id == jd_id,
                ScreeningResult.status == "shortlisted",
                ScreeningResult.is_active == True,
                ScreeningResult.tenant_id == tenant_id,
            )
            .all()
        )
        entity_id = jd_id
        entity_type = "role_template"
    else:
        return None

    result_ids = [r.id for r in results]
    assessment_map: dict[int, OverallAssessment] = {}
    if result_ids and viewer_user_id:
        assessments_rows = (
            db.query(OverallAssessment)
            .filter(
                OverallAssessment.result_id.in_(result_ids),
                OverallAssessment.user_id == viewer_user_id,
            )
            .all()
        )
        assessment_map = {a.result_id: a for a in assessments_rows}

    shortlisted_candidates = []
    comparison_candidates: dict[str, list] = {}

    for r in results:
        analysis = _safe_json(r.analysis_result)
        parsed = _safe_json(r.parsed_data)
        sb = analysis.get("score_breakdown", {})

        cand = r.candidate
        cand_name = getattr(cand, "name", None) or parsed.get("contact_info", {}).get("name", "Unknown")
        current_role = getattr(cand, "current_role", None) or ""
        total_years = getattr(cand, "total_years_exp", None)

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
                    v for v in [first_edu.get("degree", ""), first_edu.get("institution", "")] if v
                )

        oa = assessment_map.get(r.id)
        recruiter_notes = getattr(oa, "overall_assessment", None) or ""
        recruiter_rec = getattr(oa, "recruiter_recommendation", None) or ""

        entry = {
            "candidate_id": None if public_view else (cand.id if cand else None),
            "result_id": None if public_view else r.id,
            "name": cand_name,
            "fit_score": analysis.get("fit_score"),
            "recommendation": analysis.get("final_recommendation", ""),
            "strengths": analysis.get("strengths", []),
            "weaknesses": analysis.get("weaknesses", []),
            "matched_skills": analysis.get("matched_skills", []),
            "missing_skills": analysis.get("missing_skills", []),
            "experience_summary": experience_summary,
            "education_summary": education_summary,
            "current_role": current_role,
            "total_years_exp": total_years,
            "recruiter_notes": recruiter_notes,
            "recruiter_recommendation": recruiter_rec,
            "interview_scores": _build_interview_scores(db, r.id),
        }
        shortlisted_candidates.append(entry)

        dim_values = []
        for _label, key in _MATRIX_DIMENSIONS:
            val = sb.get(key)
            if val is None and key == "timeline":
                val = sb.get("stability")
            dim_values.append(val if val is not None else 0)
        comparison_candidates[cand_name] = dim_values

    intake = {}
    criteria = {}
    if req:
        intake = _safe_json(req.intake_json)
        criteria = _safe_json(req.calibrated_criteria_json)

    return {
        "jd_name": title,
        "requisition_title": title,
        "jd_id": entity_id,
        "requisition_id": requisition_id or (req.id if req else None),
        "entity_type": entity_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": generated_by_email,
        "public_view": public_view,
        "intake_summary": intake,
        "calibrated_must_haves": criteria.get("must_haves") or [],
        "shortlisted_candidates": shortlisted_candidates,
        "comparison_matrix": {
            "dimensions": [label for label, _key in _MATRIX_DIMENSIONS],
            "candidates": comparison_candidates,
        },
        "total_shortlisted": len(shortlisted_candidates),
    }
