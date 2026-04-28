"""Integration tests for the deterministic decision engine full flow."""

import pytest

from app.backend.services.domain_service import detect_domain_from_jd, detect_domain_from_resume
from app.backend.services.eligibility_service import check_eligibility, EligibilityResult
from app.backend.services.fit_scorer import compute_deterministic_score, explain_decision


class TestDeterministicIntegration:
    """End-to-end integration tests across all deterministic engine modules."""

    def test_cross_domain_candidate_gets_rejected(self):
        """A backend JD with an embedded candidate should score ≤ 35."""
        jd_text = "Looking for senior backend engineer with django, spring, fastapi, postgresql, redis, microservices, and rest api experience."
        resume_skills = ["rtos", "firmware", "microcontroller", "embedded linux", "arm cortex"]

        jd_domain = detect_domain_from_jd(jd_text)
        candidate_domain = detect_domain_from_resume(skills=resume_skills)

        assert jd_domain["domain"] == "backend"
        assert candidate_domain["domain"] == "embedded"
        assert jd_domain["confidence"] >= 0.3
        assert candidate_domain["confidence"] >= 0.3

        eligibility = check_eligibility(
            jd_domain=jd_domain,
            candidate_domain=candidate_domain,
            core_skill_match=0.2,
            relevant_experience=3.0,
        )
        assert eligibility.eligible is False
        assert eligibility.reason == "domain_mismatch"

        features = {
            "core_skill_match": 0.8,
            "secondary_skill_match": 0.5,
            "domain_match": 0.1,
            "relevant_experience": 0.6,
        }
        score = compute_deterministic_score(features, eligibility)
        assert score <= 35

        explanation = explain_decision(features, eligibility)
        assert explanation["decision"] == "Reject"
        assert "ineligible_cap_35" in explanation["caps_applied"]

    def test_same_domain_strong_candidate_gets_high_score(self):
        """A backend JD with a backend candidate and strong features should get a high score."""
        jd_text = "Senior backend role requiring fastapi, django, postgresql, microservices, and rest api."
        resume_skills = ["fastapi", "django", "postgresql", "microservices", "rest api", "redis", "celery"]

        jd_domain = detect_domain_from_jd(jd_text)
        candidate_domain = detect_domain_from_resume(skills=resume_skills)

        assert jd_domain["domain"] == "backend"
        assert candidate_domain["domain"] == "backend"

        eligibility = check_eligibility(
            jd_domain=jd_domain,
            candidate_domain=candidate_domain,
            core_skill_match=0.9,
            relevant_experience=5.0,
        )
        assert eligibility.eligible is True

        features = {
            "core_skill_match": 0.9,
            "secondary_skill_match": 0.8,
            "domain_match": 0.9,
            "relevant_experience": 0.8,
        }
        score = compute_deterministic_score(features, eligibility)
        assert score >= 70
        assert score <= 100

        explanation = explain_decision(features, eligibility)
        assert explanation["decision"] == "Shortlist"
        assert explanation["score"] == score
        assert explanation["caps_applied"] == []

    def test_explanation_matches_score_decision(self):
        """The explanation decision must always match the score-based decision."""
        jd_text = "Data scientist needed with pandas, numpy, etl, and sql skills."
        resume_skills = ["pandas", "numpy", "etl", "sql", "data pipeline"]

        jd_domain = detect_domain_from_jd(jd_text)
        candidate_domain = detect_domain_from_resume(skills=resume_skills)

        eligibility = check_eligibility(
            jd_domain=jd_domain,
            candidate_domain=candidate_domain,
            core_skill_match=0.5,
            relevant_experience=2.0,
        )

        features = {
            "core_skill_match": 0.5,
            "secondary_skill_match": 0.4,
            "domain_match": 0.5,
            "relevant_experience": 0.4,
        }
        score = compute_deterministic_score(features, eligibility)
        explanation = explain_decision(features, eligibility)

        # Verify score consistency
        assert explanation["score"] == score

        # Verify decision is based on same thresholds
        if score >= 72:
            assert explanation["decision"] == "Shortlist"
        elif score >= 45:
            assert explanation["decision"] == "Consider"
        else:
            assert explanation["decision"] == "Reject"

    def test_full_flow_with_low_skills_rejection(self):
        """Candidate in same domain but with very low core skills gets rejected."""
        jd_text = "DevOps engineer with kubernetes, docker, terraform, and ci/cd."
        resume_skills = ["kubernetes", "docker"]

        jd_domain = detect_domain_from_jd(jd_text)
        candidate_domain = detect_domain_from_resume(skills=resume_skills)

        assert jd_domain["domain"] == "devops"

        eligibility = check_eligibility(
            jd_domain=jd_domain,
            candidate_domain=candidate_domain,
            core_skill_match=0.1,
            relevant_experience=1.0,
        )
        assert eligibility.eligible is False
        assert eligibility.reason == "low_core_skills"

        features = {
            "core_skill_match": 0.1,
            "secondary_skill_match": 0.2,
            "domain_match": 0.4,
            "relevant_experience": 0.2,
        }
        score = compute_deterministic_score(features, eligibility)
        assert score <= 40  # low_core_skills cap

        explanation = explain_decision(features, eligibility)
        assert explanation["decision"] == "Reject"
        assert "low_core_skills_cap_40" in explanation["caps_applied"]
