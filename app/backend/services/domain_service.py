"""
Domain detection service — determines the professional domain
(e.g., embedded, data, backend) from JD text or resume skills/text.
"""

from app.backend.services.constants import DOMAIN_KEYWORDS


def detect_domain_from_jd(jd_text: str) -> dict:
    """Detect professional domain from job description text.
    
    Args:
        jd_text: Raw job description text
        
    Returns:
        {"domain": str, "confidence": float, "scores": dict}
        domain is the best-matching domain or "unknown"
        confidence is 0.0-1.0 based on match density
        scores is per-domain match counts for transparency
    """
    if not jd_text:
        return {"domain": "unknown", "confidence": 0.0, "scores": {}}
    
    text_lower = jd_text.lower()
    scores = {}
    
    for domain, keywords in DOMAIN_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[domain] = match_count / len(keywords) if keywords else 0.0
    
    if not scores or max(scores.values()) == 0:
        return {"domain": "unknown", "confidence": 0.0, "scores": scores}
    
    best_domain = max(scores, key=scores.get)
    confidence = scores[best_domain]
    
    # Require minimum confidence to declare a domain
    if confidence < 0.1:
        return {"domain": "unknown", "confidence": confidence, "scores": scores}
    
    return {"domain": best_domain, "confidence": round(confidence, 3), "scores": scores}


def detect_domain_from_resume(skills: list[str] = None, resume_text: str = None) -> dict:
    """Detect professional domain from resume skills and/or text.
    
    Args:
        skills: List of extracted skill strings
        resume_text: Raw resume text (optional, used as fallback)
        
    Returns:
        {"domain": str, "confidence": float, "scores": dict}
    """
    if not skills and not resume_text:
        return {"domain": "unknown", "confidence": 0.0, "scores": {}}
    
    # Build searchable text from skills + resume
    search_parts = []
    if skills:
        search_parts.append(" ".join(skills))
    if resume_text:
        search_parts.append(resume_text)
    combined_text = " ".join(search_parts).lower()
    
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw.lower() in combined_text)
        scores[domain] = match_count / len(keywords) if keywords else 0.0
    
    if not scores or max(scores.values()) == 0:
        return {"domain": "unknown", "confidence": 0.0, "scores": scores}
    
    best_domain = max(scores, key=scores.get)
    confidence = scores[best_domain]
    
    if confidence < 0.1:
        return {"domain": "unknown", "confidence": confidence, "scores": scores}
    
    return {"domain": best_domain, "confidence": round(confidence, 3), "scores": scores}
