"""Shared resume anchor and kit context builders."""

from __future__ import annotations

from typing import Any


def build_resume_anchors(
    profile: dict[str, Any],
    parsed_data: dict[str, Any] | None = None,
    probe_areas: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Extract candidate-specific anchors for kit personalization."""
    work = (parsed_data or {}).get("work_experience") or profile.get("work_experience") or []
    latest = work[0] if work and isinstance(work[0], dict) else {}
    name = (profile.get("name") or "Candidate").strip()
    return {
        "name": name.split()[0] if name else "there",
        "full_name": name,
        "current_company": (
            profile.get("current_company") or latest.get("company") or ""
        ).strip(),
        "current_role": (
            profile.get("current_role") or latest.get("title") or ""
        ).strip(),
        "years": profile.get("total_effective_years") or profile.get("total_years_exp") or 0,
        "latest_roles": [
            {
                "company": (e.get("company") or "").strip(),
                "title": (e.get("title") or e.get("role") or "").strip(),
                "duration": (e.get("duration") or "").strip(),
            }
            for e in work[:3]
            if isinstance(e, dict)
        ],
        "probe_areas": probe_areas or [],
    }


def format_resume_anchors_text(anchors: dict[str, Any]) -> str:
    """Human-readable block for LLM prompts."""
    lines = [
        f"Name: {anchors.get('full_name') or anchors.get('name', 'Candidate')}",
        f"Current: {anchors.get('current_role') or 'N/A'} at {anchors.get('current_company') or 'N/A'}",
        f"Experience: {anchors.get('years', 0)} years",
    ]
    for role in anchors.get("latest_roles") or []:
        if role.get("company") or role.get("title"):
            lines.append(
                f"- {role.get('title') or 'Role'} at {role.get('company') or 'Unknown'}"
                + (f" ({role.get('duration')})" if role.get("duration") else "")
            )
    probes = anchors.get("probe_areas") or []
    if probes:
        lines.append("PROBE AREAS:")
        for p in probes[:8]:
            if isinstance(p, dict):
                lines.append(
                    f"  - [{p.get('priority', 'medium').upper()}] "
                    f"{p.get('category', '')}: {p.get('reasoning', p.get('skill', ''))}"
                )
    return "\n".join(lines)


def build_probe_areas_from_analysis(
    *,
    matched: list[str],
    missing: list[str],
    gap_analysis: dict[str, Any] | None = None,
    risk_signals: list[Any] | None = None,
) -> list[dict[str, Any]]:
    """Lightweight probe list when InterviewContextEngine is unavailable."""
    probes: list[dict[str, Any]] = []
    matched_lower = {s.lower() for s in matched if isinstance(s, str)}
    for skill in missing[:6]:
        if isinstance(skill, str) and skill.lower() not in matched_lower:
            probes.append({
                "category": "skill_validation",
                "priority": "high",
                "skill": skill,
                "reasoning": f"'{skill}' is required but not clearly evidenced on the resume.",
            })
    gap_analysis = gap_analysis or {}
    for gap in (gap_analysis.get("employment_gaps") or gap_analysis.get("gaps") or [])[:2]:
        if isinstance(gap, dict):
            months = gap.get("duration_months") or gap.get("months") or 0
            if months >= 6:
                probes.append({
                    "category": "employment_gap",
                    "priority": "high",
                    "duration_months": months,
                    "reasoning": f"Employment gap of {months} months needs explanation.",
                })
    for risk in (risk_signals or [])[:3]:
        if isinstance(risk, dict):
            probes.append({
                "category": "risk_validation",
                "priority": "medium",
                "risk_type": risk.get("type") or risk.get("flag", "unknown"),
                "reasoning": risk.get("description") or risk.get("detail") or str(risk),
            })
    return probes
