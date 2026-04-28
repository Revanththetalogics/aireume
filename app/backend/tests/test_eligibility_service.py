"""Tests for eligibility_service.py — similarity-based eligibility gates."""

import pytest

from app.backend.services.eligibility_service import (
    check_eligibility,
    EligibilityResult,
    _compute_domain_similarity_for_eligibility,
    DOMAIN_SIMILARITY_MISMATCH_THRESHOLD,
)


class TestComputeDomainSimilarityForEligibility:
    """Tests for _compute_domain_similarity_for_eligibility."""

    def test_same_domain_high_similarity(self):
        """Identical score vectors should yield similarity near 1.0."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {"embedded": 0.6, "hardware": 0.3, "backend": 0.1}}
        cand = {"domain": "embedded", "confidence": 0.6, "scores": {"embedded": 0.6, "hardware": 0.3, "backend": 0.1}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert sim > 0.8

    def test_related_domains_medium_similarity(self):
        """Embedded + hardware share overlap — medium similarity."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {"embedded": 0.6, "hardware": 0.3, "backend": 0.1}}
        cand = {"domain": "hardware", "confidence": 0.5, "scores": {"embedded": 0.3, "hardware": 0.5, "backend": 0.2}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert 0.3 <= sim <= 0.9  # They share overlap, so moderate

    def test_unrelated_domains_low_similarity(self):
        """Embedded vs marketing (management) — low similarity."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {"embedded": 0.6, "hardware": 0.3, "backend": 0.1}}
        cand = {"domain": "management", "confidence": 0.5, "scores": {"management": 0.7, "backend": 0.2, "devops": 0.1}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert sim < 0.2

    def test_orthogonal_domains_near_zero(self):
        """Domains with no overlapping scores should have similarity near 0."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {"embedded": 0.8, "hardware": 0.2}}
        cand = {"domain": "management", "confidence": 0.5, "scores": {"management": 0.7, "frontend": 0.3}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert sim < 0.1

    def test_unknown_domain_fallback_binary(self):
        """When scores are empty, fallback to binary name comparison."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {}}
        cand = {"domain": "embedded", "confidence": 0.6, "scores": {}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert sim == 0.6  # Returns jd confidence since names match

    def test_unknown_domain_fallback_mismatch(self):
        """When scores are empty and names differ, returns 0."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {}}
        cand = {"domain": "backend", "confidence": 0.5, "scores": {}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert sim == 0.0

    def test_zero_magnitude_returns_zero(self):
        """All-zero score vectors should return 0."""
        jd = {"domain": "unknown", "confidence": 0.0, "scores": {"embedded": 0.0}}
        cand = {"domain": "unknown", "confidence": 0.0, "scores": {"embedded": 0.0}}
        sim = _compute_domain_similarity_for_eligibility(jd, cand)
        assert sim == 0.0

    def test_symmetry(self):
        """Similarity should be symmetric: sim(A, B) == sim(B, A)."""
        jd = {"domain": "embedded", "confidence": 0.6, "scores": {"embedded": 0.6, "hardware": 0.3}}
        cand = {"domain": "backend", "confidence": 0.5, "scores": {"embedded": 0.2, "backend": 0.6, "hardware": 0.1}}
        sim_ab = _compute_domain_similarity_for_eligibility(jd, cand)
        sim_ba = _compute_domain_similarity_for_eligibility(cand, jd)
        assert sim_ab == sim_ba


class TestCheckEligibility:
    """Tests for check_eligibility with similarity-based domain checks."""

    # ── Dict-based domain args (new API) ──

    def test_same_domain_dicts_passes(self):
        """Same domain with high similarity should pass."""
        jd = {"domain": "embedded", "confidence": 0.5, "scores": {"embedded": 0.6}}
        cand = {"domain": "embedded", "confidence": 0.5, "scores": {"embedded": 0.6}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is True

    def test_related_domains_dicts_passes(self):
        """Related domains (e.g. embedded + hardware) with similarity >= 0.2 should pass."""
        jd = {"domain": "embedded", "confidence": 0.5, "scores": {"embedded": 0.6, "hardware": 0.3, "backend": 0.1}}
        cand = {"domain": "hardware", "confidence": 0.5, "scores": {"embedded": 0.3, "hardware": 0.5, "backend": 0.2}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        # Similarity should be > 0.2 (related domains), so should pass
        assert result.eligible is True

    def test_unrelated_domains_dicts_rejects(self):
        """Unrelated domains with similarity < 0.2 should reject."""
        jd = {"domain": "embedded", "confidence": 0.5, "scores": {"embedded": 0.8, "hardware": 0.2}}
        cand = {"domain": "management", "confidence": 0.5, "scores": {"management": 0.7, "frontend": 0.3}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is False
        assert result.reason == "domain_mismatch"
        assert "domain_similarity" in result.details

    def test_low_confidence_dicts_passes(self):
        """Low confidence domains should not trigger mismatch rejection."""
        jd = {"domain": "embedded", "confidence": 0.2, "scores": {"embedded": 0.8}}
        cand = {"domain": "management", "confidence": 0.2, "scores": {"management": 0.7}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is True

    def test_unknown_domain_dicts_passes(self):
        """Unknown domains should not trigger mismatch."""
        jd = {"domain": "unknown", "confidence": 0.0, "scores": {}}
        cand = {"domain": "unknown", "confidence": 0.0, "scores": {}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is True

    # ── String-based domain args (backward compatibility) ──

    def test_string_domain_same_passes(self):
        """String domain args with same domain should pass (backward compat)."""
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is True

    def test_string_domain_different_rejects(self):
        """String domain args with different domains should reject (no scores → binary fallback → 0 similarity)."""
        result = check_eligibility(
            jd_domain="embedded",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is False
        assert result.reason == "domain_mismatch"

    def test_string_domain_unknown_passes(self):
        """String domain args with 'unknown' should pass."""
        result = check_eligibility(
            jd_domain="unknown",
            candidate_domain="unknown",
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is True

    # ── Other eligibility rules (unchanged) ──

    def test_low_core_skills_rejects(self):
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.2,
            relevant_experience=5.0,
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
        )
        assert result.eligible is True

    def test_no_relevant_experience_rejects(self):
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=0.0,
        )
        assert result.eligible is False
        assert result.reason == "no_relevant_experience"

    def test_all_checks_pass(self):
        result = check_eligibility(
            jd_domain="backend",
            candidate_domain="backend",
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is True
        assert result.reason is None

    def test_priority_domain_mismatch_before_low_core_skills(self):
        """When both domain mismatch and low core skills apply, domain_mismatch should be returned first."""
        jd = {"domain": "embedded", "confidence": 0.5, "scores": {"embedded": 0.8, "hardware": 0.2}}
        cand = {"domain": "management", "confidence": 0.5, "scores": {"management": 0.7, "frontend": 0.3}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.1,
            relevant_experience=0.0,
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
        )
        assert result.eligible is False
        assert result.reason == "low_core_skills"

    def test_mismatch_details_include_similarity(self):
        """Domain mismatch result should include domain_similarity in details."""
        jd = {"domain": "embedded", "confidence": 0.5, "scores": {"embedded": 0.8, "hardware": 0.2}}
        cand = {"domain": "management", "confidence": 0.5, "scores": {"management": 0.7, "frontend": 0.3}}
        result = check_eligibility(
            jd_domain=jd,
            candidate_domain=cand,
            core_skill_match=0.8,
            relevant_experience=5.0,
        )
        assert result.eligible is False
        assert "domain_similarity" in result.details
        assert result.details["domain_similarity"] < DOMAIN_SIMILARITY_MISMATCH_THRESHOLD
