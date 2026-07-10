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
            "intent": text,
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


DEPTH_LIMITS = {
    "quick": {"technical_questions": 2, "experience_deep_dive_questions": 1, "behavioral_questions": 1},
    "standard": None,
    "deep": None,
}


def _cap_category(items: list, limit: int | None) -> list:
    if limit is None:
        return list(items)
    return list(items)[:limit]


def slice_kit_for_depth(
    interview_questions: dict[str, Any],
    depth: str,
    *,
    analysis: dict[str, Any] | None = None,
    parsed_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Return flattened kit questions sized for quick / standard / deep.

    - quick: subset (~5–6 questions)
    - standard: full kit
    - deep: full kit + 2–4 extra technical probes
    """
    depth = (depth or "standard").lower()
    iq = dict(interview_questions or {})

    if depth == "quick":
        limits = DEPTH_LIMITS["quick"]
        sliced = {
            "candidate_briefing": iq.get("candidate_briefing") or {},
            "technical_questions": _cap_category(iq.get("technical_questions") or [], limits["technical_questions"]),
            "behavioral_questions": _cap_category(iq.get("behavioral_questions") or [], limits["behavioral_questions"]),
            "culture_fit_questions": [],
            "experience_deep_dive_questions": _cap_category(
                iq.get("experience_deep_dive_questions") or [],
                limits["experience_deep_dive_questions"],
            ),
        }
        return flatten_interview_kit(sliced)

    base = flatten_interview_kit(iq)

    if depth != "deep":
        return base

    from app.backend.services.interview_kit_generator import generate_deep_technical_extras

    existing_texts = {q.get("text", "") for q in base}
    skill_analysis = (analysis or {}).get("skill_analysis") or {
        "matched_skills": (analysis or {}).get("matched_skills") or [],
        "missing_skills": (analysis or {}).get("missing_skills") or [],
    }
    extras = generate_deep_technical_extras(
        profile=(analysis or {}).get("candidate_profile") or {},
        jd_analysis=(analysis or {}).get("jd_analysis") or {},
        skill_analysis=skill_analysis,
        parsed_data=parsed_data,
        count=4,
        existing_texts=existing_texts,
    )
    start_idx = len([q for q in base if q.get("category") == "technical"])
    for i, extra in enumerate(extras):
        base.append(
            {
                "id": f"technical-deep-{start_idx + i}",
                "category": "technical",
                "category_key": "technical_questions",
                "index": start_idx + i,
                **extra,
                "intent": extra.get("text", ""),
                "is_deep_extra": True,
            }
        )
    return base


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

    depth_label = "standard"
    if voice_session.interview_depth == "quick":
        depth_label = "quick"
    if recruiter and recruiter.interview_config_json:
        try:
            cfg = json.loads(recruiter.interview_config_json)
            if cfg.get("depth"):
                depth_label = str(cfg["depth"]).lower()
        except json.JSONDecodeError:
            pass

    analysis_data: dict[str, Any] = {}
    parsed_data: dict[str, Any] = {}
    if result:
        try:
            analysis_data = json.loads(result.analysis_result or "{}")
        except json.JSONDecodeError:
            analysis_data = {}
        try:
            parsed_data = json.loads(result.parsed_data or "{}")
        except json.JSONDecodeError:
            parsed_data = {}

    questions = slice_kit_for_depth(
        interview_questions,
        depth_label,
        analysis=analysis_data,
        parsed_data=parsed_data,
    )
    return {
        "screening_result_id": result.id if result else screening_result_id,
        "interview_questions": interview_questions,
        "questions": questions,
        "kit_source": kit_source,
        "kit_status": kit_status,
        "role_title": role_title,
        "depth": depth_label,
    }
