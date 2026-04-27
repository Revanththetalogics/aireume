"""Standardized risk penalty calculation — single source of truth."""

from app.backend.services.constants import RISK_SEVERITY_PENALTIES


def compute_risk_penalty(risk_signals: list[dict]) -> float:
    """Compute risk penalty from a list of risk signal dicts.

    Each signal should have a 'severity' key: 'high', 'medium', or 'low'.
    Returns total penalty score.
    """
    return sum(
        RISK_SEVERITY_PENALTIES.get(r.get("severity", "low"), 0)
        for r in risk_signals
    )
