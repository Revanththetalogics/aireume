"""Serialize post-interview outcome fields from ScreeningResult rows."""

from __future__ import annotations

from typing import Any


def outcome_fields_from_result(result: Any) -> dict[str, Any]:
    """Return outcome dict safe for JSON API responses."""
    if result is None:
        return {
            "call_fit_score": None,
            "call_source": None,
            "consolidated_recommendation": None,
            "consolidated_reasoning": None,
            "call_completed_at": None,
        }

    completed_at = getattr(result, "call_completed_at", None)
    return {
        "call_fit_score": getattr(result, "call_fit_score", None),
        "call_source": getattr(result, "call_source", None),
        "consolidated_recommendation": getattr(result, "consolidated_recommendation", None),
        "consolidated_reasoning": getattr(result, "consolidated_reasoning", None),
        "call_completed_at": completed_at.isoformat() if completed_at else None,
    }
