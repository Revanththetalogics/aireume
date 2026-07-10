"""Tests for screening outcome serialization."""
from app.backend.services.screening_outcome import outcome_fields_from_result


class _FakeResult:
    call_fit_score = 78
    call_source = "ai"
    consolidated_recommendation = "advance"
    consolidated_reasoning = "Strong call."
    call_completed_at = None


def test_outcome_fields_from_result():
    fields = outcome_fields_from_result(_FakeResult())
    assert fields["call_fit_score"] == 78
    assert fields["call_source"] == "ai"
    assert fields["consolidated_recommendation"] == "advance"


def test_outcome_fields_none_safe():
    fields = outcome_fields_from_result(None)
    assert fields["call_fit_score"] is None
    assert fields["consolidated_recommendation"] is None
