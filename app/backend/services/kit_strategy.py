"""Derive recruiter interview strategy from the stored interview kit (single source of truth)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.backend.models.db_models import ScreeningResult
from app.backend.services.interview_kit_loader import (
    _build_analysis_fallback_kit,
    _extract_interview_questions_from_result,
    flatten_interview_kit,
    resolve_interview_kit_for_voice,
)
from app.backend.services.interview_kit_loader import _find_screening_result  # noqa: F401


def _depth_from_config(config: dict[str, Any]) -> str:
    depth = (config.get("depth") or "").lower()
    if depth in ("quick", "standard", "deep"):
        return depth
    minutes = config.get("duration_minutes") or 20
    if minutes <= 7:
        return "quick"
    if minutes >= 25:
        return "deep"
    return "standard"


def kit_questions_for_depth(
    interview_questions: dict[str, Any],
    depth: str,
    *,
    analysis: dict[str, Any] | None = None,
    parsed_data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Slice flattened kit questions by interview depth."""
    from app.backend.services.interview_kit_loader import slice_kit_for_depth

    return slice_kit_for_depth(
        interview_questions,
        depth,
        analysis=analysis,
        parsed_data=parsed_data,
    )


def strategy_from_kit(
    interview_questions: dict[str, Any],
    *,
    depth: str = "standard",
    candidate_name: str = "there",
    role_title: str = "",
    analysis: dict[str, Any] | None = None,
    parsed_data: dict[str, Any] | None = None,
    candidate_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build recruiter-compatible strategy JSON from interview kit."""
    questions_flat = kit_questions_for_depth(
        interview_questions,
        depth,
        analysis=analysis,
        parsed_data=parsed_data,
    )

    briefing = interview_questions.get("candidate_briefing") or {}
    priorities = (candidate_intelligence or {}).get("interview_priorities") or []
    objective = (
        "; ".join(priorities[:3])
        if priorities
        else (
            f"Verify {candidate_name}'s fit for {role_title or 'the role'} "
            "using personalized resume-driven screen questions."
        )
    )
    planned = []
    for idx, q in enumerate(questions_flat, start=1):
        spoken = q.get("spoken_text") or q.get("text", "")
        planned.append(
            {
                "sequence_number": idx,
                "category": q.get("category", "technical"),
                "question_text": spoken,
                "question_context": "; ".join(q.get("what_to_listen_for") or [])[:200],
                "intent": q.get("intent") or spoken,
                "scoring_criteria": q.get("scoring_criteria") or {},
                "estimated_minutes": 2,
                "target_skills": [],
            }
        )

    duration_map = {"quick": 5, "standard": 15, "deep": 25}
    return {
        "source": "interview_kit",
        "depth": depth,
        "objective": objective,
        "focus_areas": list({q.get("category") for q in questions_flat if q.get("category")}),
        "candidate_briefing": briefing,
        "thread_transitions": interview_questions.get("thread_transitions") or {},
        "planned_questions": planned,
        "questions": planned,
        "time_plan": {
            "opening_rapport": 1,
            "technical": max(2, len([q for q in planned if q["category"] == "technical"]) * 2),
            "behavioral": 3,
            "experience": 4,
            "closing": 1,
        },
        "branching_rules": [
            "If answer is thin, use kit follow-up before advancing.",
            "Score each answer against kit scoring_criteria.",
        ],
        "duration_minutes": duration_map.get(depth, 15),
        "kit_question_count": len(planned),
    }


def load_kit_strategy_for_screening(
    db: Session,
    *,
    tenant_id: int,
    candidate_id: int,
    jd_id: int | None,
    screening_result_id: int | None,
    config: dict[str, Any] | None = None,
    role_title: str = "",
    candidate_name: str = "there",
) -> dict[str, Any]:
    """Load interview kit from screening result and return strategy for recruiter session."""
    config = config or {}
    depth = _depth_from_config(config)

    result = None
    if screening_result_id:
        result = db.get(ScreeningResult, screening_result_id)

    interview_questions: dict[str, Any] = {}
    analysis: dict[str, Any] = {}
    parsed: dict[str, Any] = {}
    candidate_intelligence: dict[str, Any] | None = None

    if result:
        interview_questions = _extract_interview_questions_from_result(result)
        try:
            analysis = json.loads(result.analysis_result or "{}")
        except json.JSONDecodeError:
            analysis = {}
        try:
            parsed = json.loads(result.parsed_data or "{}")
        except json.JSONDecodeError:
            parsed = {}
        from app.backend.services.candidate_intelligence_service import ci_from_screening_row

        candidate_intelligence = ci_from_screening_row(result)
        if not interview_questions:
            interview_questions = _build_analysis_fallback_kit(result, role_title=role_title)

    return strategy_from_kit(
        interview_questions,
        depth=depth,
        candidate_name=candidate_name,
        role_title=role_title,
        analysis=analysis,
        parsed_data=parsed,
        candidate_intelligence=candidate_intelligence,
    )
