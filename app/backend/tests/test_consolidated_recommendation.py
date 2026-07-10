"""Tests for consolidated recommendation service."""
import pytest

from app.backend.services.consolidated_recommendation import (
    compute_consolidated,
    stars_to_call_score,
    rubric_to_score,
)


def test_compute_without_call_score():
    out = compute_consolidated(analysis_score=65, call_score=None)
    assert out["analysis_score"] == 65
    assert out["call_score"] is None
    assert out["consolidated_recommendation"] == "advance"


def test_compute_with_call_raises_confidence():
    out = compute_consolidated(analysis_score=65, call_score=82, call_source="ai")
    assert out["call_score"] == 82
    assert out["blended_score"] > 65
    assert "ai" in out["consolidated_reasoning"].lower() or "AI" in out["consolidated_reasoning"]


def test_stars_to_call_score():
    assert stars_to_call_score(5) == 95
    assert stars_to_call_score(3) == 60


def test_rubric_to_score():
    assert rubric_to_score("strong") == 85
    assert rubric_to_score("weak") == 30
