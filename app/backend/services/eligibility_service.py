"""
Eligibility engine — deterministic hard-reject gates applied before scoring.
Returns eligibility status with structured reasons for rejection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EligibilityResult:
    eligible: bool
    reason: Optional[str] = None
    details: dict = field(default_factory=dict)


# Threshold below which two domains are considered a mismatch
DOMAIN_SIMILARITY_MISMATCH_THRESHOLD = 0.2


def _compute_domain_similarity_for_eligibility(
    jd_domain: dict, candidate_domain: dict
) -> float:
    """Compute cosine similarity between JD and candidate domain score vectors.

    Falls back to binary name comparison when score vectors are unavailable.
    """
    jd_scores = jd_domain.get("scores", {})
    cand_scores = candidate_domain.get("scores", {})

    if not jd_scores or not cand_scores:
        # Fallback to binary if scores not available
        if jd_domain.get("domain", "unknown") == candidate_domain.get("domain", "unknown"):
            return jd_domain.get("confidence", 0)
        return 0.0

    # Get union of all domains
    all_domains = set(jd_scores.keys()) | set(cand_scores.keys())

    # Compute cosine similarity
    dot_product = sum(jd_scores.get(d, 0) * cand_scores.get(d, 0) for d in all_domains)
    jd_magnitude = sum(v ** 2 for v in jd_scores.values()) ** 0.5
    cand_magnitude = sum(v ** 2 for v in cand_scores.values()) ** 0.5

    if jd_magnitude == 0 or cand_magnitude == 0:
        return 0.0

    return round(dot_product / (jd_magnitude * cand_magnitude), 3)


def check_eligibility(
    jd_domain,
    candidate_domain,
    core_skill_match: float,
    relevant_experience: float,
) -> EligibilityResult:
    """Check candidate eligibility using deterministic rules.

    Args:
        jd_domain: Domain dict from detect_domain_from_jd() with keys
            "domain" (str), "confidence" (float), "scores" (dict).
            Also accepts plain str for backward compatibility.
        candidate_domain: Domain dict from detect_domain_from_resume(), same shape.
            Also accepts plain str for backward compatibility.
        core_skill_match: Ratio of core skills matched (0.0-1.0)
        relevant_experience: Years of relevant experience

    Returns:
        EligibilityResult with eligible flag and reason if rejected
    """
    # Normalise to dict shape (backward compatibility with string callers)
    if isinstance(jd_domain, str):
        jd_domain = {"domain": jd_domain, "confidence": 0.5, "scores": {}}
    if isinstance(candidate_domain, str):
        candidate_domain = {"domain": candidate_domain, "confidence": 0.5, "scores": {}}

    jd_name = jd_domain.get("domain", "unknown")
    cand_name = candidate_domain.get("domain", "unknown")
    jd_conf = jd_domain.get("confidence", 0.0)
    cand_conf = candidate_domain.get("confidence", 0.0)

    # Rule 1: Domain mismatch (only enforce when both domains are detected with confidence)
    if jd_name != "unknown" and cand_name != "unknown" and jd_conf >= 0.3 and cand_conf >= 0.3:
        similarity = _compute_domain_similarity_for_eligibility(jd_domain, candidate_domain)
        if similarity < DOMAIN_SIMILARITY_MISMATCH_THRESHOLD:
            return EligibilityResult(
                eligible=False,
                reason="domain_mismatch",
                details={
                    "jd_domain": jd_name,
                    "candidate_domain": cand_name,
                    "jd_confidence": jd_conf,
                    "candidate_confidence": cand_conf,
                    "domain_similarity": similarity,
                },
            )

    # Rule 2: Core skill match too low
    if core_skill_match < 0.3:
        return EligibilityResult(
            eligible=False,
            reason="low_core_skills",
            details={
                "core_skill_match": core_skill_match,
                "threshold": 0.3,
            },
        )

    # Rule 3: No relevant experience
    if relevant_experience <= 0:
        return EligibilityResult(
            eligible=False,
            reason="no_relevant_experience",
            details={
                "relevant_experience": relevant_experience,
            },
        )

    # All gates passed
    return EligibilityResult(eligible=True)
