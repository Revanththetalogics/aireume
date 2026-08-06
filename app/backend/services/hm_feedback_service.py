"""HM rejection feedback → intake and sourcing strategy suggestions."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.backend.models.db_models import Requisition
from app.backend.services.requisition_service import _json_dumps, _json_loads, calibrate_requisition

OUTCOME_REASON_CODES = {
    "too_junior": "Candidate too junior for the role",
    "wrong_skills": "Missing or wrong must-have skills",
    "wrong_seniority": "Seniority level mismatch",
    "culture_mismatch": "Culture or team fit concern",
    "compensation": "Compensation or level mismatch",
    "other": "Other (see notes)",
}

_REASON_SEARCH_HINTS: dict[str, str] = {
    "too_junior": "Prioritize candidates with more years in role and lead/ownership experience.",
    "wrong_skills": "Tighten sourcing on must-have skills; verify skill evidence before screen.",
    "wrong_seniority": "Adjust seniority filter in sourcing; confirm title band with HM.",
    "culture_mismatch": "Screen for team context and environment fit in intro calls.",
    "compensation": "Confirm level and compensation band before advancing candidates.",
    "other": "Review HM notes and update intake or search brief accordingly.",
}


def build_feedback_suggestions(
    req: Requisition,
    *,
    outcome_reason_code: str | None,
    outcome_notes: str | None,
) -> dict[str, Any]:
    """Return proposed updates from HM rejection — recruiter confirms before apply."""
    code = (outcome_reason_code or "other").strip().lower()
    intake = _json_loads(req.intake_json, {})
    search_brief = _json_loads(req.search_brief_json, {})
    suggestions: dict[str, Any] = {
        "outcome_reason_code": code,
        "outcome_reason_label": OUTCOME_REASON_CODES.get(code, OUTCOME_REASON_CODES["other"]),
        "outcome_notes": outcome_notes or "",
        "search_brief_additions": [],
        "intake_notes_addition": "",
        "recommended_actions": [],
    }

    hint = _REASON_SEARCH_HINTS.get(code, _REASON_SEARCH_HINTS["other"])
    suggestions["search_brief_additions"].append(hint)
    if outcome_notes and outcome_notes.strip():
        suggestions["search_brief_additions"].append(f"HM feedback: {outcome_notes.strip()}")

    if code == "wrong_skills":
        suggestions["recommended_actions"].append("Review must-haves with HM and recalibrate criteria.")
    elif code == "too_junior":
        suggestions["recommended_actions"].append("Raise seniority bar in intake and sourcing filters.")
    else:
        suggestions["recommended_actions"].append("Update search brief and intake notes from HM feedback.")

    suggestions["intake_notes_addition"] = (
        f"[HM reject — {suggestions['outcome_reason_label']}] {outcome_notes or ''}".strip()
    )
    suggestions["preview"] = {
        "current_search_brief": search_brief,
        "current_hm_notes": intake.get("hm_notes") or "",
    }
    return suggestions


def get_pending_feedback(req: Requisition) -> dict[str, Any] | None:
    """Return recruiter-visible pending HM feedback suggestions, if any."""
    brief = _json_loads(req.search_brief_json, {})
    pending = brief.get("pending_feedback")
    return pending if isinstance(pending, dict) and pending else None


def persist_pending_feedback(req: Requisition, suggestions: dict[str, Any]) -> None:
    """Store HM reject suggestions so recruiters can apply them later."""
    brief = _json_loads(req.search_brief_json, {})
    # Drop large preview blob — recruiters rebuild from current brief on apply UI
    stored = {k: v for k, v in suggestions.items() if k != "preview"}
    brief["pending_feedback"] = stored
    req.search_brief_json = _json_dumps(brief)


def clear_pending_feedback(req: Requisition) -> None:
    brief = _json_loads(req.search_brief_json, {})
    if "pending_feedback" in brief:
        brief.pop("pending_feedback", None)
        req.search_brief_json = _json_dumps(brief)


def apply_feedback_suggestions(
    db: Session,
    req: Requisition,
    suggestions: dict[str, Any],
    *,
    user_id: int | None,
    recalibrate: bool = False,
) -> Requisition:
    """Apply recruiter-confirmed feedback to search brief and intake."""
    intake = _json_loads(req.intake_json, {})
    search_brief = _json_loads(req.search_brief_json, {})
    additions = suggestions.get("search_brief_additions") or []
    history = search_brief.get("hm_feedback_history") or []
    history.append({
        "reason_code": suggestions.get("outcome_reason_code"),
        "notes": suggestions.get("outcome_notes"),
        "additions": additions,
    })
    search_brief["hm_feedback_history"] = history
    search_brief["latest_strategy"] = "\n".join(additions)
    req.search_brief_json = _json_dumps(search_brief)

    note = suggestions.get("intake_notes_addition") or ""
    if note:
        existing = (intake.get("hm_notes") or "").strip()
        intake["hm_notes"] = f"{existing}\n{note}".strip() if existing else note
        req.intake_json = _json_dumps(intake)

    if recalibrate and req.intake_status == "approved":
        calibrate_requisition(db, req, user_id=user_id, merge_jd=True)

    clear_pending_feedback(req)
    db.flush()
    return req
