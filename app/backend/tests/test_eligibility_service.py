"""Tests for eligibility_service.py — deterministic eligibility gates."""

import pytest

from app.backend.services.eligibility_service import check_eligibility, EligibilityResult


class TestCheckEligibility:
    """Tests for check_eligibility."""

    def test_domain_mismatch_high_confidence_rejects(self):
        result = check_eligibility(
            jd_domain="embedded",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=5.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is False
        assert result.reason == "domain_mismatch"
        assert result.details["jd_domain"] == "embedded"
        assert result.details["candidate_domain"] == "backend"

    def test_domain_mismatch_low_confidence_passes(self):
        """Confidence < 0.3 should not trigger domain mismatch rejection."""
        result = check_eligibility(
            jd_domain="embedded",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=5.0,
            jd_domain_confidence=0.2,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is True

    def test_both_domains_unknown_passes(self):
        """Cannot detect mismatch when both domains are unknown."""
        result = check_eligibility(
            jd_domain="unknown",
            candidate_domain="unknown",
            core_skill_match=0.8,
            relevant_experience=5.0,
            jd_domain_confidence=0.0,
            candidate_domain_confidence=0.0,
        )
        assert result.eligible is True

    def test_low_core_skills_rejects(self):
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.2,
            relevant_experience=5.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is False
        assert result.reason == "low_core_skills"
        assert result.details["core_skill_match"] == 0.2
        assert result.details["threshold"] == 0.3

    def test_core_skill_boundary_passes(self):
        """core_skill_match == 0.3 is at the boundary and should pass."""
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.3,
            relevant_experience=5.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is True

    def test_no_relevant_experience_rejects(self):
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=0.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is False
        assert result.reason == "no_relevant_experience"

    def test_all_checks_pass(self):
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=5.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is True
        assert result.reason is None

    def test_priority_domain_mismatch_before_low_core_skills(self):
        """When both domain mismatch and low core skills apply, domain_mismatch should be returned first."""
        result = check_eligibility(
            jd_domain="embedded",
            candidate_domain="backend",
            core_skill_match=0.1,
            relevant_experience=0.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is False
        assert result.reason == "domain_mismatch"

    def test_priority_low_core_skills_before_no_experience(self):
        """When both low core skills and no experience apply, low_core_skills should be returned first."""
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.1,
            relevant_experience=0.0,
            jd_domain_confidence=0.5,
            candidate_domain_confidence=0.5,
        )
        assert result.eligible is False
        assert result.reason == "low_core_skills"
