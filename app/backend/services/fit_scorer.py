"""Standardized fit score computation — single source of truth."""

from typing import Any, Dict, List, Optional

from app.backend.services.constants import (
    DEFAULT_WEIGHTS,
    RECOMMENDATION_THRESHOLDS,
)
from app.backend.services.risk_calculator import compute_risk_penalty


def compute_fit_score(
    scores: Dict[str, Any],
    scoring_weights: Optional[Dict] = None,
    risk_signals: Optional[List[dict]] = None,
    risk_penalty: Optional[float] = None,
) -> Dict[str, Any]:
    """Compute weighted fit score, risk signals, and recommendation.

    When custom scoring_weights are provided, they are applied to scoring.
    When no custom weights are provided, DEFAULT_WEIGHTS from constants.py is used.
    """
    w = (scoring_weights or DEFAULT_WEIGHTS).copy()

    skill_score    = scores.get("skill_score",    50)
    exp_score      = scores.get("exp_score",       50)
    arch_score     = scores.get("arch_score",      50)
    edu_score      = scores.get("edu_score",       60)
    timeline_score = scores.get("timeline_score", 85)
    domain_score   = scores.get("domain_score",    60)
    actual_years   = scores.get("actual_years",    0)
    required_years = scores.get("required_years",  0)
    matched_skills = scores.get("matched_skills",  [])
    missing_skills = scores.get("missing_skills",  [])
    required_count = scores.get("required_count",  0)
    employment_gaps = scores.get("employment_gaps", [])
    short_stints    = scores.get("short_stints",   [])

    # ── Risk signals (deterministic Python — not LLM) ─────────────────────────
    if risk_signals is None:
        risk_signals = []

        has_critical_gap = any(g.get("severity") == "critical" for g in employment_gaps)
        if has_critical_gap:
            risk_signals.append({"type": "gap",           "severity": "high",
                                  "description": "Critical employment gap detected (12+ months)"})

        skill_miss_pct = (len(missing_skills) / max(required_count, 1)) * 100
        if skill_miss_pct >= 50:
            risk_signals.append({"type": "skill_gap",     "severity": "high",
                                  "description": f"Missing {len(missing_skills)}/{required_count} required skills"})
        elif skill_miss_pct >= 30:
            risk_signals.append({"type": "skill_gap",     "severity": "medium",
                                  "description": f"Missing {len(missing_skills)}/{required_count} required skills"})

        if domain_score < 40:
            risk_signals.append({"type": "domain_mismatch", "severity": "medium",
                                  "description": "Candidate domain does not closely match role requirements"})

        if len(short_stints) >= 3:
            risk_signals.append({"type": "stability",     "severity": "medium",
                                  "description": f"{len(short_stints)} short stints (<6 months) detected"})
        elif len(short_stints) >= 2:
            risk_signals.append({"type": "stability",     "severity": "low",
                                  "description": f"{len(short_stints)} short stints detected"})

        if required_years > 0 and actual_years > required_years * 2:
            risk_signals.append({"type": "overqualified",  "severity": "low",
                                  "description": f"Candidate has {actual_years}y experience vs {required_years}y required"})

    # ── Risk penalty ──────────────────────────────────────────────────────────
    if risk_penalty is None:
        risk_penalty = compute_risk_penalty(risk_signals)

    # ── Fit score ──────────────────────────────────────────────────────────────
    fit_score = round(
        skill_score    * w.get("skills", DEFAULT_WEIGHTS["skills"])       +
        exp_score      * w.get("experience", DEFAULT_WEIGHTS["experience"])   +
        arch_score     * w.get("architecture", DEFAULT_WEIGHTS["architecture"]) +
        edu_score      * w.get("education", DEFAULT_WEIGHTS["education"])    +
        timeline_score * w.get("timeline", DEFAULT_WEIGHTS["timeline"])     +
        domain_score   * w.get("domain", DEFAULT_WEIGHTS["domain"])       -
        risk_penalty   * w.get("risk", DEFAULT_WEIGHTS["risk"])
    )
    fit_score = max(0, min(100, fit_score))

    # ── Recommendation ────────────────────────────────────────────────────────
    if fit_score >= RECOMMENDATION_THRESHOLDS["shortlist"]:
        recommendation = "Shortlist"
        risk_level = "Low"
    elif fit_score >= RECOMMENDATION_THRESHOLDS["consider"]:
        recommendation = "Consider"
        risk_level = "Medium" if risk_signals else "Low"
    else:
        recommendation = "Reject"
        risk_level = "High" if any(r["severity"] == "high" for r in risk_signals) else "Medium"

    return {
        "fit_score":            fit_score,
        "final_recommendation": recommendation,
        "risk_level":           risk_level,
        "risk_signals":         risk_signals,
        "risk_penalty":         risk_penalty,
        "score_breakdown": {
            "skill_match":      skill_score,
            "experience_match": exp_score,
            "stability":        timeline_score,
            "education":        edu_score,
            "architecture":     arch_score,
            "domain_fit":       domain_score,
            "timeline":         timeline_score,
            "risk_penalty":     risk_penalty,
        },
    }


def compute_deterministic_score(features: dict, eligibility, weights: Optional[Dict] = None) -> int:
    """Compute a deterministic score with hard caps based on eligibility and feature quality.

    Args:
        features: dict with keys:
            - core_skill_match: float (0-1)
            - secondary_skill_match: float (0-1)
            - domain_match: float (0-1)
            - relevant_experience: float (0-1, normalized)
            - total_experience: float (years)
        eligibility: EligibilityResult from eligibility_service
        weights: Optional dict supporting multiple schemas:
            - New schema: {core_competencies, experience, domain_fit, education, ...}
            - Legacy schema: {skills, experience, stability, education}
            - Internal schema: {skills, experience, architecture, education, timeline, domain, risk}
            - Direct schema: {core_skill_match, secondary_skill_match, domain_match, relevant_experience}
            Defaults to 40/15/25/20 split when None or when keys don't match.

    Returns:
        Integer score 0-100 with deterministic caps applied
    """
    # Default weight split for deterministic features
    w_core = 0.40
    w_secondary = 0.15
    w_domain = 0.25
    w_experience = 0.20
    
    if weights is not None:
        # Priority 1: Direct mapping (already in deterministic schema)
        if "core_skill_match" in weights:
            w_core = weights.get("core_skill_match", 0.40)
            w_secondary = weights.get("secondary_skill_match", 0.15)
            w_domain = weights.get("domain_match", 0.25)
            w_experience = weights.get("relevant_experience", 0.20)
        # Priority 2: New 7-weight schema (core_competencies, domain_fit, experience)
        elif "core_competencies" in weights:
            # Map new schema to deterministic features
            w_core = weights.get("core_competencies", 0.30)  # core skills
            w_secondary = weights.get("role_excellence", 0.10) * 0.5  # partial contribution
            w_domain = weights.get("domain_fit", 0.20)  # domain fit
            w_experience = weights.get("experience", 0.20)  # experience
            # Normalize to sum to 1.0
            total = w_core + w_secondary + w_domain + w_experience
            if total > 0:
                w_core = w_core / total
                w_secondary = w_secondary / total
                w_domain = w_domain / total
                w_experience = w_experience / total
        # Priority 3: Internal 7-weight schema (skills, domain, experience)
        elif "skills" in weights and "architecture" in weights:
            # Map internal schema to deterministic features
            w_core = weights.get("skills", 0.30)  # core skills
            w_secondary = weights.get("architecture", 0.15) * 0.5  # partial contribution
            w_domain = weights.get("domain", 0.10)  # domain fit
            w_experience = weights.get("experience", 0.20)  # experience
            # Normalize to sum to 1.0
            total = w_core + w_secondary + w_domain + w_experience
            if total > 0:
                w_core = w_core / total
                w_secondary = w_secondary / total
                w_domain = w_domain / total
                w_experience = w_experience / total
        # Priority 4: Legacy 4-weight schema (skills, experience, stability, education)
        elif "skills" in weights and "stability" in weights:
            w_core = weights.get("skills", 0.40)
            w_secondary = 0.05  # minimal secondary in legacy
            w_domain = weights.get("stability", 0.15) * 0.5  # partial contribution
            w_experience = weights.get("experience", 0.35)
            # Normalize to sum to 1.0
            total = w_core + w_secondary + w_domain + w_experience
            if total > 0:
                w_core = w_core / total
                w_secondary = w_secondary / total
                w_domain = w_domain / total
                w_experience = w_experience / total

    # Base score from weighted features
    score = (
        features.get("core_skill_match", 0) * w_core +
        features.get("secondary_skill_match", 0) * w_secondary +
        features.get("domain_match", 0) * w_domain +
        features.get("relevant_experience", 0) * w_experience
    ) * 100  # Scale to 0-100

    # Normalize to 0-100 range
    score = max(0, min(100, score))

    # Apply hard caps for ineligible candidates
    if not eligibility.eligible:
        score = min(score, 35)

    # Apply domain match cap
    if features.get("domain_match", 0) < 0.3:
        score = min(score, 35)

    # Apply core skill cap
    if features.get("core_skill_match", 0) < 0.3:
        score = min(score, 40)

    return int(score)


def explain_decision(features: dict, eligibility) -> dict:
    """Generate a structured, deterministic explanation of the scoring decision.

    Returns:
        {
            "decision": "Shortlist" | "Consider" | "Reject",
            "reasons": list of strings explaining the decision,
            "feature_summary": dict of feature scores,
            "caps_applied": list of cap reasons if any
        }
    """
    from app.backend.services.constants import RECOMMENDATION_THRESHOLDS

    score = compute_deterministic_score(features, eligibility)
    caps_applied = []
    reasons = []

    # Determine decision based on thresholds
    if score >= RECOMMENDATION_THRESHOLDS["shortlist"]:
        decision = "Shortlist"
    elif score >= RECOMMENDATION_THRESHOLDS["consider"]:
        decision = "Consider"
    else:
        decision = "Reject"

    # Build reasons
    if not eligibility.eligible:
        caps_applied.append("ineligible_cap_35")
        if eligibility.reason == "domain_mismatch":
            reasons.append(f"Domain mismatch: JD requires {eligibility.details.get('jd_domain', 'unknown')}, candidate is {eligibility.details.get('candidate_domain', 'unknown')}")
        elif eligibility.reason == "low_core_skills":
            reasons.append(f"Core skill match too low: {eligibility.details.get('core_skill_match', 0):.0%} (minimum 30%)")
        elif eligibility.reason == "no_relevant_experience":
            reasons.append("No relevant experience detected")

    if features.get("domain_match", 0) < 0.3:
        caps_applied.append("low_domain_cap_35")
        reasons.append(f"Low domain match: {features.get('domain_match', 0):.0%}")

    if features.get("core_skill_match", 0) < 0.3:
        caps_applied.append("low_core_skills_cap_40")
        reasons.append(f"Low core skill match: {features.get('core_skill_match', 0):.0%}")

    if not reasons:
        if decision == "Shortlist":
            reasons.append("Strong match across all criteria")
        elif decision == "Consider":
            reasons.append("Moderate match — review recommended")
        else:
            reasons.append("Below threshold across multiple criteria")

    return {
        "decision": decision,
        "score": score,
        "reasons": reasons,
        "feature_summary": {k: round(v, 3) if isinstance(v, float) else v for k, v in features.items()},
        "caps_applied": caps_applied,
    }
