"""Consolidated recommendation — derives hiring signal from analysis + call scores."""

from __future__ import annotations

from typing import Any

# Maps internal recommendation keys to user-facing labels
RECOMMENDATION_LABELS = {
    "advance_hm": "Advance to HM",
    "advance": "Advance",
    "hold": "Hold",
    "reject": "Reject",
    "strong_reject": "Strong Reject",
    "strong_advance": "Strong Advance",
}


def _clamp(score: int | float | None, default: int = 50) -> int:
    if score is None:
        return default
    try:
        return max(0, min(100, int(round(float(score)))))
    except (TypeError, ValueError):
        return default


def stars_to_call_score(rating: int | None) -> int | None:
    """Convert 1–5 star rating to 0–100 call score."""
    if rating is None:
        return None
    mapping = {1: 20, 2: 40, 3: 60, 4: 80, 5: 95}
    return mapping.get(int(rating), 50)


def rubric_to_score(rubric: str | None) -> int:
    """Map strong/adequate/weak rubric labels to numeric scores."""
    if not rubric:
        return 50
    key = str(rubric).lower().strip()
    return {"strong": 85, "adequate": 60, "weak": 30}.get(key, 50)


def average_scores(scores: list[int | float]) -> int | None:
    valid = [s for s in scores if s is not None]
    if not valid:
        return None
    return _clamp(sum(valid) / len(valid))


def compute_consolidated(
    *,
    analysis_score: int | float | None,
    call_score: int | float | None,
    call_source: str | None = None,
    call_recommendation: str | None = None,
    analysis_recommendation: str | None = None,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    """
    Derive consolidated recommendation from document analysis and call evidence.

    Returns:
        {
            "analysis_score": int,
            "call_score": int | None,
            "call_source": str | None,
            "consolidated_recommendation": str,
            "consolidated_label": str,
            "consolidated_reasoning": str,
            "confidence": "high" | "medium" | "low",
        }
    """
    doc_score = _clamp(analysis_score)
    live_score = _clamp(call_score) if call_score is not None else None

    if live_score is None:
        rec = _recommendation_from_score(doc_score)
        reasoning = (
            f"Document analysis score is {doc_score}/100. "
            "No phone screen completed yet — recommendation based on resume analysis only."
        )
        return {
            "analysis_score": doc_score,
            "call_score": None,
            "call_source": call_source,
            "consolidated_recommendation": rec,
            "consolidated_label": RECOMMENDATION_LABELS.get(rec, rec.replace("_", " ").title()),
            "consolidated_reasoning": reasoning,
            "confidence": "low",
        }

    # Weighted blend: call evidence weighted slightly higher (60/40)
    blended = int(doc_score * 0.4 + live_score * 0.6)
    delta = live_score - doc_score

    rec = _recommendation_from_blended(blended, call_recommendation, analysis_recommendation)

    source_label = "human recruiter screen" if call_source == "human" else "AI phone screen"
    direction = "confirmed" if abs(delta) <= 8 else ("raised" if delta > 0 else "lowered")

    parts = [
        f"Analysis: {doc_score}/100. {source_label.title()}: {live_score}/100.",
        f"Call evidence {direction} confidence in fit (delta {delta:+d}).",
        f"Blended signal: {blended}/100.",
    ]
    if evidence:
        parts.append(" ".join(evidence[:3]))
    if call_recommendation:
        parts.append(f"Call recommendation: {call_recommendation.replace('_', ' ')}.")

    confidence = "high" if abs(delta) <= 12 and blended >= 70 or blended <= 35 else "medium"
    if abs(delta) > 25:
        confidence = "medium"

    return {
        "analysis_score": doc_score,
        "call_score": live_score,
        "call_source": call_source,
        "consolidated_recommendation": rec,
        "consolidated_label": RECOMMENDATION_LABELS.get(rec, rec.replace("_", " ").title()),
        "consolidated_reasoning": " ".join(parts),
        "confidence": confidence,
        "blended_score": blended,
    }


def _recommendation_from_score(score: int) -> str:
    if score >= 80:
        return "advance_hm"
    if score >= 65:
        return "advance"
    if score >= 45:
        return "hold"
    if score >= 30:
        return "reject"
    return "strong_reject"


def _recommendation_from_blended(
    blended: int,
    call_rec: str | None,
    analysis_rec: str | None,
) -> str:
    hire_signals = {"strong_hire", "hire", "strong_yes", "yes", "lean_hire", "advance_hm", "advance"}
    reject_signals = {"no_hire", "strong_no_hire", "no", "strong_no", "lean_no_hire", "reject", "strong_reject"}

    if call_rec and call_rec.lower().replace(" ", "_") in hire_signals and blended >= 60:
        return "advance_hm" if blended >= 78 else "advance"
    if call_rec and call_rec.lower().replace(" ", "_") in reject_signals:
        return "strong_reject" if blended < 35 else "reject"

    return _recommendation_from_score(blended)


def persist_outcome_to_screening_result(
    result_row: Any,
    outcome: dict[str, Any],
    *,
    call_source: str,
) -> None:
    """Write consolidated outcome fields onto a ScreeningResult ORM row."""
    from datetime import datetime, timezone

    if outcome.get("call_score") is not None:
        result_row.call_fit_score = outcome["call_score"]
        result_row.call_source = call_source
        result_row.call_completed_at = datetime.now(timezone.utc)
    result_row.consolidated_recommendation = outcome.get("consolidated_recommendation")
    result_row.consolidated_reasoning = outcome.get("consolidated_reasoning")
