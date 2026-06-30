"""
Domain detection service — domain-agnostic.

Instead of relying on a hardcoded list of software domains, this module uses:
  1. LLM-extracted domain keywords from the JD profile (if available).
  2. The shared SKILL_TAXONOMY as a fallback for broad domain detection.

The goal is to recognize any professional domain (SAP, Healthcare, Finance,
Legal, Manufacturing, etc.) without a hardcoded domain list.
"""

from typing import Dict, Any, List, Optional

from app.backend.services.constants import DOMAIN_KEYWORDS


def _normalize(text: str) -> str:
    return text.lower().strip()


def _score_by_keywords(text: str, keywords: List[str]) -> float:
    """Score how many of the given keywords appear in the text."""
    if not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return min(1.0, matches / max(len(keywords) * 0.15, 1.0))


def detect_domain_from_jd(jd_text: str, jd_analysis: Optional[Dict[str, Any]] = None) -> dict:
    """Detect professional domain from the JD text and optional JD profile.

    If a JD profile was extracted by the LLM, its domain label and keywords are
    used directly.  Otherwise, the legacy keyword-based detection is used as a
    fallback.

    Returns:
        {"domain": str, "confidence": float, "scores": dict, "keywords": list}
    """
    if not jd_text:
        return {"domain": "unknown", "confidence": 0.0, "scores": {}, "keywords": []}

    # Prefer LLM-extracted profile
    if jd_analysis and jd_analysis.get("_profile_source") in ("llm", "merged"):
        domain = jd_analysis.get("domain", "other")
        keywords = jd_analysis.get("domain_keywords", []) or []
        text_lower = jd_text.lower()
        confidence = _score_by_keywords(text_lower, keywords)
        return {
            "domain": domain,
            "confidence": round(max(0.1, confidence), 3),
            "scores": {domain: confidence},
            "keywords": keywords,
        }

    # Fallback: legacy keyword-based detection
    text_lower = jd_text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[domain] = match_count / len(keywords) if keywords else 0.0

    if not scores or max(scores.values()) == 0:
        return {"domain": "unknown", "confidence": 0.0, "scores": scores, "keywords": []}

    best_domain = max(scores, key=scores.get)
    confidence = scores[best_domain]

    if confidence < 0.1:
        return {"domain": "unknown", "confidence": confidence, "scores": scores, "keywords": []}

    return {
        "domain": best_domain,
        "confidence": round(confidence, 3),
        "scores": scores,
        "keywords": DOMAIN_KEYWORDS.get(best_domain, []),
    }


def detect_domain_from_resume(
    skills: Optional[List[str]] = None,
    resume_text: Optional[str] = None,
    jd_domain: Optional[Dict[str, Any]] = None,
) -> dict:
    """Detect how well the candidate's resume aligns with the JD domain.

    When a JD domain is provided, the candidate's domain is reported as the same
    label if enough of the JD's domain keywords are found in the resume/skills.
    This makes the system domain-agnostic: the candidate is matched against the
    JD's domain, not a fixed taxonomy.

    Args:
        skills: List of extracted skill strings.
        resume_text: Raw resume text (optional).
        jd_domain: Domain dict from detect_domain_from_jd(). If provided, the
            candidate domain is reported using the JD's domain label.

    Returns:
        {"domain": str, "confidence": float, "scores": dict, "keywords": list}
    """
    if not skills and not resume_text:
        return {"domain": "unknown", "confidence": 0.0, "scores": {}, "keywords": []}

    search_parts = []
    if skills:
        search_parts.append(" ".join(str(s) for s in skills))
    if resume_text:
        search_parts.append(resume_text)
    combined_text = " ".join(search_parts).lower()

    # If JD domain is provided, score candidate against its keywords
    if jd_domain:
        keywords = jd_domain.get("keywords", []) or jd_domain.get("domain_keywords", []) or []
        domain_label = jd_domain.get("domain", "other")
        confidence = _score_by_keywords(combined_text, keywords)
        return {
            "domain": domain_label,
            "confidence": round(max(0.1, confidence), 3),
            "scores": {domain_label: confidence},
            "keywords": keywords,
        }

    # Fallback: legacy keyword-based detection
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in combined_text)
        scores[domain] = match_count / len(keywords) if keywords else 0.0

    if not scores or max(scores.values()) == 0:
        return {"domain": "unknown", "confidence": 0.0, "scores": scores, "keywords": []}

    best_domain = max(scores, key=scores.get)
    confidence = scores[best_domain]

    if confidence < 0.1:
        return {"domain": "unknown", "confidence": confidence, "scores": scores, "keywords": []}

    return {
        "domain": best_domain,
        "confidence": round(confidence, 3),
        "scores": scores,
        "keywords": DOMAIN_KEYWORDS.get(best_domain, []),
    }
