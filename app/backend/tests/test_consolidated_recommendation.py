"""Tests for consolidated recommendation service."""
import pytest

from app.backend.services.consolidated_recommendation import (
    compute_consolidated,
    compute_consolidated_for_result,
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


def test_compute_for_result_uses_tenant_weights(db, auth_client):
    from app.backend.models.db_models import ScreeningResult, Tenant, User

    user = db.query(User).filter(User.email == "admin@testcorp.com").first()
    assert user is not None
    tenant = db.get(Tenant, user.tenant_id)
    tenant.metadata_json = '{"hiring_signal_weights": {"resume": 0.7, "interview": 0.3}}'
    sr = ScreeningResult(
        tenant_id=user.tenant_id,
        resume_text="x",
        jd_text="y",
        parsed_data="{}",
        analysis_result="{}",
    )
    out = compute_consolidated_for_result(
        db,
        sr,
        analysis_score=80,
        call_score=60,
        call_source="ai",
    )
    assert out["blended_score"] == 74
