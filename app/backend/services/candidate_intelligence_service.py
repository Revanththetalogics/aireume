"""Build and persist candidate intelligence for interview planning."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.backend.services.interview_kit_context import (
    build_probe_areas_from_analysis,
    build_resume_anchors,
)

logger = logging.getLogger("aria.candidate_intelligence")


def build_candidate_intelligence(
    *,
    screening_result_id: int | None = None,
    analysis_result: dict[str, Any] | None = None,
    parsed_data: dict[str, Any] | None = None,
    gap_analysis: dict[str, Any] | None = None,
    probe_areas: list[dict[str, Any]] | None = None,
    fit_score: int | float | None = None,
) -> dict[str, Any]:
    """Aggregate JD/resume comparison into a reusable CI artifact."""
    analysis_result = analysis_result or {}
    parsed_data = parsed_data or {}
    profile = analysis_result.get("candidate_profile") or {}
    if not profile.get("work_experience") and parsed_data:
        profile = {**profile, "work_experience": parsed_data.get("work_experience") or []}

    skill_analysis = analysis_result.get("skill_analysis") or {}
    matched = (
        skill_analysis.get("matched_required")
        or skill_analysis.get("matched_skills")
        or []
    )
    missing = (
        skill_analysis.get("missing_required")
        or skill_analysis.get("missing_skills")
        or skill_analysis.get("gap_skills")
        or []
    )
    risk_signals = analysis_result.get("risk_signals") or []

    if probe_areas is None:
        probe_areas = build_probe_areas_from_analysis(
            matched=list(matched),
            missing=list(missing),
            gap_analysis=gap_analysis,
            risk_signals=risk_signals,
        )

    resume_anchors = build_resume_anchors(profile, parsed_data, probe_areas)

    strengths = []
    for skill in matched[:5]:
        if isinstance(skill, str):
            strengths.append({
                "claim": f"Resume shows {skill}",
                "evidence": "Matched in skill analysis",
                "confidence": 0.8,
            })

    gaps = []
    for skill in missing[:5]:
        if isinstance(skill, str):
            gaps.append({
                "skill": skill,
                "severity": "high",
                "interview_priority": len(gaps) + 1,
            })

    claims_to_validate = []
    for probe in probe_areas[:8]:
        if not isinstance(probe, dict):
            continue
        category = probe.get("category", "")
        if category in ("skill_validation", "risk_validation", "employment_gap"):
            claims_to_validate.append({
                "claim": probe.get("reasoning") or probe.get("skill") or category,
                "source": "resume",
                "risk": probe.get("priority", "medium"),
                "category": category,
            })

    interview_priorities = []
    for probe in sorted(
        probe_areas,
        key=lambda p: {"high": 0, "medium": 1, "low": 2}.get(
            (p.get("priority") or "low") if isinstance(p, dict) else "low", 3
        ),
    ):
        if isinstance(probe, dict) and probe.get("reasoning"):
            interview_priorities.append(str(probe["reasoning"]))
    if not interview_priorities and missing:
        interview_priorities.append(f"Validate gap: {missing[0]}")

    score = fit_score
    if score is None:
        score = analysis_result.get("fit_score") or analysis_result.get("deterministic_score") or 50
    try:
        hiring_confidence = max(0.0, min(1.0, float(score) / 100.0))
    except (TypeError, ValueError):
        hiring_confidence = 0.5

    return {
        "version": 1,
        "screening_result_id": screening_result_id,
        "strengths": strengths,
        "gaps": gaps,
        "claims_to_validate": claims_to_validate,
        "probe_areas": probe_areas,
        "interview_priorities": interview_priorities[:6],
        "resume_anchors": resume_anchors,
        "hiring_confidence_pre_interview": round(hiring_confidence, 2),
    }


def merge_ci_into_kit_context(context: dict[str, Any], ci: dict[str, Any]) -> dict[str, Any]:
    """Attach CI fields to LLM/kit generation context."""
    merged = dict(context)
    merged["candidate_intelligence"] = ci
    merged["probe_areas"] = ci.get("probe_areas") or context.get("probe_areas") or []
    merged["resume_anchors"] = ci.get("resume_anchors") or context.get("resume_anchors") or {}
    merged["interview_priorities"] = ci.get("interview_priorities") or []
    return merged


def ci_from_screening_row(row: Any) -> dict[str, Any] | None:
    """Load persisted CI from a ScreeningResult row."""
    raw = getattr(row, "candidate_intelligence_json", None)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None
