"""Tests for fitment adjuster risk handling."""

from app.backend.services.recruiter.fitment_adjuster import FitmentAdjuster


class TestFitmentAdjusterRisks:
    def test_excess_experience_not_validated_as_risk(self):
        adjuster = FitmentAdjuster()
        validated, dismissed = adjuster._assess_risks(
            ["Candidate has 13.3y experience vs 5y required"],
            [],
        )
        assert validated == []
        assert dismissed == ["Candidate has 13.3y experience vs 5y required"]

    def test_under_experience_can_still_validate(self):
        adjuster = FitmentAdjuster()
        validated, dismissed = adjuster._assess_risks(
            ["Candidate has 2y experience vs 5y required"],
            [],
        )
        assert len(validated) == 1
        assert dismissed == []

    def test_is_excess_experience_risk_detects_overqualification(self):
        assert FitmentAdjuster._is_excess_experience_risk("13.3y experience vs 5y required") is True
        assert FitmentAdjuster._is_excess_experience_risk("2y experience vs 5y required") is False
