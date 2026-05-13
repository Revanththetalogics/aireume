"""
Enterprise PDF report generation for ARIA screening results.

Uses Jinja2 + WeasyPrint to render a multi-page A4 PDF from
ScreeningResult, InterviewEvaluation and OverallAssessment data.
"""

import json
import os
from datetime import datetime
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from ..models.db_models import InterviewEvaluation, OverallAssessment, ScreeningResult


def _safe_json(text: str | None) -> dict:
    """Parse JSON text, returning empty dict on failure."""
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    """Remove duplicates preserving original order (case-insensitive)."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def generate_pdf_report(result_id: int, db: Session, current_user_id: int) -> bytes:
    """
    Generate an enterprise PDF report for a screening result.

    Args:
        result_id: Primary key of the ScreeningResult.
        db: SQLAlchemy session.
        current_user_id: ID of the user requesting the report (auditing).

    Returns:
        Raw PDF bytes.
    """
    # ── 1. Fetch ScreeningResult ──────────────────────────────────────────
    result = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.id == result_id)
        .first()
    )
    if not result:
        raise ValueError(f"ScreeningResult {result_id} not found")

    # ── 2. Parse JSON blobs ───────────────────────────────────────────────
    analysis = _safe_json(result.analysis_result)
    parsed = _safe_json(result.parsed_data)

    # ── 3. Fetch related records ──────────────────────────────────────────
    evaluations = (
        db.query(InterviewEvaluation)
        .filter(InterviewEvaluation.result_id == result_id)
        .all()
    )

    overall = (
        db.query(OverallAssessment)
        .filter(OverallAssessment.result_id == result_id)
        .first()
    )

    # ── 4. Build candidate info (merged_data > parsed_data > candidate row)
    contact_info = analysis.get("contact_info") or parsed.get("contact_info", {})

    candidate_name = (
        analysis.get("candidate_name")
        or contact_info.get("name")
        or "Unknown Candidate"
    )
    try:
        if result.candidate and result.candidate.name:
            candidate_name = result.candidate.name
    except Exception:
        pass  # Lazy-loading may fail if session is detached

    current_role = ""
    try:
        if result.candidate and result.candidate.current_role:
            current_role = result.candidate.current_role
        elif analysis.get("current_role"):
            current_role = analysis.get("current_role")
        elif parsed.get("current_role"):
            current_role = parsed.get("current_role")
    except Exception:
        current_role = analysis.get("current_role", "") or parsed.get("current_role", "")

    total_years = None
    try:
        if result.candidate and result.candidate.total_years_exp is not None:
            total_years = result.candidate.total_years_exp
        elif analysis.get("total_years_exp") is not None:
            total_years = analysis.get("total_years_exp")
        elif parsed.get("total_years_exp") is not None:
            total_years = parsed.get("total_years_exp")
    except Exception:
        total_years = analysis.get("total_years_exp") or parsed.get("total_years_exp")

    # ── 5. Scores & recommendations ───────────────────────────────────────
    fit_score = analysis.get("fit_score", 0) or 0
    final_recommendation = analysis.get("final_recommendation", "")
    final_rationale = analysis.get(
        "final_rationale", analysis.get("recommendation_rationale", "")
    )

    recruiter_recommendation = ""
    overall_assessment_text = ""
    if overall:
        recruiter_recommendation = overall.recruiter_recommendation or ""
        overall_assessment_text = overall.overall_assessment or ""

    # ── 6. Strengths / weaknesses (top 3) ─────────────────────────────────
    strengths = (analysis.get("strengths") or [])[:3]
    weaknesses = (analysis.get("weaknesses") or [])[:3]

    # ── 7. Role title ─────────────────────────────────────────────────────
    role_title = ""
    try:
        if result.role_template and result.role_template.name:
            role_title = result.role_template.name
    except Exception:
        pass
    if not role_title:
        role_title = (
            analysis.get("role_title")
            or analysis.get("jd_name")
            or parsed.get("role_title")
            or ""
        )

    # ── 8. Score breakdown (with safe defaults) ──────────────────────────
    sb = analysis.get("score_breakdown", {})
    score_breakdown = {
        "skill_match": sb.get("skill_match", 0) or 0,
        "experience_match": sb.get("experience_match", 0) or 0,
        "domain_fit": sb.get("domain_fit", 0) or 0,
        "education": sb.get("education", 0) or 0,
        "stability": sb.get("stability", 0) or 0,
        "architecture": sb.get("architecture", sb.get("timeline", 0)) or 0,
    }

    # ── 9. Skills ─────────────────────────────────────────────────────────
    matched_skills = analysis.get("matched_skills") or []
    missing_skills = analysis.get("missing_skills") or []

    # ── 10. Risk signals ──────────────────────────────────────────────────
    risk_signals = analysis.get("risk_signals") or []

    # ── 11. Employment gaps ───────────────────────────────────────────────
    employment_gaps = analysis.get("employment_gaps") or []
    if not employment_gaps:
        try:
            if result.candidate and result.candidate.gap_analysis_json:
                gap_data = _safe_json(result.candidate.gap_analysis_json)
                employment_gaps = gap_data.get("gaps") or []
        except Exception:
            pass

    # ── 12. Interview evaluation summary ──────────────────────────────────
    eval_summary: dict[str, dict[str, Any]] = {}
    for ev in evaluations:
        cat = (ev.question_category or "General").replace("_", " ").title()
        if cat not in eval_summary:
            eval_summary[cat] = {
                "strong": 0,
                "adequate": 0,
                "weak": 0,
                "notes": [],
            }
        rating = (ev.rating or "").lower()
        if rating in eval_summary[cat]:
            eval_summary[cat][rating] += 1
        if ev.notes:
            eval_summary[cat]["notes"].append(ev.notes)

    # ── 13. Follow-up questions ───────────────────────────────────────────
    follow_up_questions: list[str] = []

    # From weak-rated evaluation areas
    weak_categories: set[str] = set()
    for ev in evaluations:
        if ev.rating and ev.rating.lower() == "weak":
            cat = (ev.question_category or "this area").replace("_", " ")
            if cat not in weak_categories:
                weak_categories.add(cat)
                follow_up_questions.append(
                    f"Can you walk us through a specific example demonstrating your expertise in {cat}?"
                )

    # From missing skills
    for skill in missing_skills[:5]:
        follow_up_questions.append(
            f"How would you approach ramping up on {skill} if required for this role?"
        )

    follow_up_questions = _dedupe_preserve_order(follow_up_questions)
    follow_up_questions = follow_up_questions[:8]

    # Fallback to AI-generated interview questions
    if not follow_up_questions:
        interview_questions = analysis.get("interview_questions") or []
        if interview_questions:
            follow_up_questions = interview_questions[:8]
        else:
            follow_up_questions = [
                "Can you describe your most relevant project experience?",
                "What motivates you about this role?",
                "How do you handle tight deadlines and competing priorities?",
            ]

    # ── 14. Render Jinja2 template ────────────────────────────────────────
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("report.html")

    html_out = template.render(
        generated_at=datetime.now().strftime("%B %d, %Y at %H:%M"),
        candidate_name=candidate_name,
        current_role=current_role,
        total_years=total_years,
        contact_email=contact_info.get("email", ""),
        contact_phone=contact_info.get("phone", ""),
        fit_score=fit_score,
        recruiter_recommendation=recruiter_recommendation,
        overall_assessment=overall_assessment_text,
        final_recommendation=final_recommendation,
        final_rationale=final_rationale,
        strengths=strengths,
        weaknesses=weaknesses,
        role_title=role_title,
        score_breakdown=score_breakdown,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        risk_signals=risk_signals,
        employment_gaps=employment_gaps,
        eval_summary=eval_summary,
        follow_up_questions=follow_up_questions,
        has_evaluations=bool(evaluations),
    )

    # ── 15. Convert to PDF ────────────────────────────────────────────────
    from weasyprint import HTML

    pdf_bytes = HTML(string=html_out).write_pdf()
    return pdf_bytes
