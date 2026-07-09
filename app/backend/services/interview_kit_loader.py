"""Load and resolve interview kit questions for voice screening dispatch."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backend.models.db_models import (
    RecruiterInterviewSession,
    ScreeningResult,
    VoiceScreeningSession,
)

logger = logging.getLogger(__name__)

CATEGORY_ORDER = (
    "technical_questions",
    "behavioral_questions",
    "culture_fit_questions",
    "experience_deep_dive_questions",
)


def _normalize_question_item(item: Any) -> dict[str, Any] | None:
    if isinstance(item, str) and item.strip():
        return {
            "text": item.strip(),
            "what_to_listen_for": [],
            "follow_ups": [],
            "scoring_criteria": {},
        }
    if isinstance(item, dict):
        text = (item.get("text") or "").strip()
        if not text:
            return None
        return {
            "text": text,
            "what_to_listen_for": list(item.get("what_to_listen_for") or []),
            "follow_ups": list(item.get("follow_ups") or []),
            "scoring_criteria": dict(item.get("scoring_criteria") or {}),
        }
    return None


def flatten_interview_kit(interview_questions: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten categorized kit into an ordered list for the voice agent."""
    flat: list[dict[str, Any]] = []
    if not isinstance(interview_questions, dict):
        return flat

    category_labels = {
        "technical_questions": "technical",
        "behavioral_questions": "behavioral",
        "culture_fit_questions": "culture_fit",
        "experience_deep_dive_questions": "experience_deep_dive",
    }

    for key in CATEGORY_ORDER:
        items = interview_questions.get(key) or []
        if not isinstance(items, list):
            continue
        category = category_labels.get(key, key)
        for index, raw in enumerate(items):
            normalized = _normalize_question_item(raw)
            if not normalized:
                continue
            flat.append(
                {
                    "id": f"{category}-{index}",
                    "category": category,
                    "category_key": key,
                    "index": index,
                    **normalized,
                }
            )
    return flat


def _extract_interview_questions_from_result(result: ScreeningResult) -> dict[str, Any]:
    for source_name, raw in (
        ("narrative_json", result.narrative_json),
        ("analysis_result", result.analysis_result),
    ):
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        iq = payload.get("interview_questions")
        if isinstance(iq, dict) and any(
            isinstance(iq.get(k), list) and iq.get(k) for k in CATEGORY_ORDER
        ):
            logger.info(
                "Interview kit loaded from screening_result=%s via %s",
                result.id,
                source_name,
            )
            return iq
    return {}


def _find_screening_result(
    db: Session,
    *,
    tenant_id: int,
    candidate_id: int,
    jd_id: int | None,
    screening_result_id: int | None = None,
) -> ScreeningResult | None:
    if screening_result_id:
        row = db.execute(
            select(ScreeningResult).where(
                ScreeningResult.id == screening_result_id,
                ScreeningResult.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if row:
            return row

    if not jd_id:
        return None

    return db.execute(
        select(ScreeningResult)
        .where(
            ScreeningResult.tenant_id == tenant_id,
            ScreeningResult.candidate_id == candidate_id,
            ScreeningResult.role_template_id == jd_id,
            ScreeningResult.is_active == True,
        )
        .order_by(ScreeningResult.timestamp.desc())
    ).scalar_one_or_none()


def _build_analysis_fallback_kit(
    result: ScreeningResult,
    *,
    role_title: str = "",
) -> dict[str, Any]:
    """Build a better-than-frontend-template kit from deterministic analysis."""
    from app.backend.services.interview_kit_generator import generate_targeted_interview_kit

    try:
        analysis = json.loads(result.analysis_result or "{}")
    except json.JSONDecodeError:
        analysis = {}

    try:
        parsed = json.loads(result.parsed_data or "{}")
    except json.JSONDecodeError:
        parsed = {}

    skill_analysis = analysis.get("skill_analysis") or analysis.get("skills") or {}
    if not isinstance(skill_analysis, dict):
        skill_analysis = {}

    profile = analysis.get("candidate_profile") or {}
    if not profile.get("work_experience") and parsed:
        profile = {**profile, "work_experience": parsed.get("work_experience") or []}

    jd_analysis = analysis.get("jd_analysis") or {
        "title": role_title or analysis.get("role_title", "the role"),
        "key_responsibilities": analysis.get("key_responsibilities", []),
        "required_skills": analysis.get("required_skills", []),
    }

    return generate_targeted_interview_kit(
        profile=profile,
        jd_analysis=jd_analysis,
        skill_analysis=skill_analysis,
        parsed_data=parsed,
    )


def resolve_interview_kit_for_voice(
    db: Session,
    voice_session: VoiceScreeningSession,
) -> dict[str, Any]:
    """
    Resolve interview kit for a voice session.

    Returns:
        {
            "screening_result_id": int | None,
            "interview_questions": dict,
            "questions": list[dict],  # flattened
            "kit_source": "stored" | "fallback" | "empty",
            "kit_status": str | None,
        }
    """
    screening_result_id = None
    recruiter = db.execute(
        select(RecruiterInterviewSession).where(
            RecruiterInterviewSession.voice_session_id == voice_session.id
        )
    ).scalar_one_or_none()
    if recruiter and recruiter.screening_result_id:
        screening_result_id = recruiter.screening_result_id

    role_title = ""
    if voice_session.jd_id and voice_session.jd:
        role_title = voice_session.jd.name or ""

    result = _find_screening_result(
        db,
        tenant_id=voice_session.tenant_id,
        candidate_id=voice_session.candidate_id,
        jd_id=voice_session.jd_id,
        screening_result_id=screening_result_id,
    )

    interview_questions: dict[str, Any] = {}
    kit_source = "empty"
    kit_status = None

    if result:
        kit_status = getattr(result, "interview_kit_status", None)
        interview_questions = _extract_interview_questions_from_result(result)
        if interview_questions:
            kit_source = "stored"
        else:
            interview_questions = _build_analysis_fallback_kit(result, role_title=role_title)
            if interview_questions:
                kit_source = "fallback"
                kit_status = kit_status or "fallback"

    questions = flatten_interview_kit(interview_questions)
    return {
        "screening_result_id": result.id if result else screening_result_id,
        "interview_questions": interview_questions,
        "questions": questions,
        "kit_source": kit_source,
        "kit_status": kit_status,
        "role_title": role_title,
    }
