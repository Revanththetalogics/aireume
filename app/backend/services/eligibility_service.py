"""
Eligibility engine — deterministic hard-reject gates applied before scoring.
Returns eligibility status with structured reasons for rejection.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EligibilityResult:
    eligible: bool
    reason: Optional[str] = None
    details: dict = field(default_factory=dict)


def check_eligibility(
    jd_domain: str,
    candidate_domain: str,
    core_skill_match: float,
    relevant_experience: float,
    jd_domain_confidence: float = 0.0,
    candidate_domain_confidence: float = 0.0,
) -> EligibilityResult:
    """Check candidate eligibility using deterministic rules.
    
    Args:
        jd_domain: Detected domain of the job description (e.g., "embedded", "backend")
        candidate_domain: Detected domain of the candidate's resume
        core_skill_match: Ratio of core skills matched (0.0-1.0)
        relevant_experience: Years of relevant experience
        jd_domain_confidence: Confidence of JD domain detection (0.0-1.0)
        candidate_domain_confidence: Confidence of candidate domain detection (0.0-1.0)
        
    Returns:
        EligibilityResult with eligible flag and reason if rejected
    """
    # Rule 1: Domain mismatch (only enforce when both domains are detected with confidence)
    if (
        jd_domain != "unknown"
        and candidate_domain != "unknown"
        and jd_domain != candidate_domain
        and jd_domain_confidence >= 0.3
        and candidate_domain_confidence >= 0.3
    ):
        return EligibilityResult(
            eligible=False,
            reason="domain_mismatch",
            details={
                "jd_domain": jd_domain,
                "candidate_domain": candidate_domain,
                "jd_confidence": jd_domain_confidence,
                "candidate_confidence": candidate_domain_confidence,
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
