"""
JD Quality Scoring Engine — pure-Python, zero-LLM scoring of job descriptions.

Scores a JD 0-100 across 5 dimensions (20 points each):
  1. Skill Clarity
  2. Experience Specificity
  3. Responsibility Quality
  4. Domain Coherence
  5. Completeness
"""

import re
from typing import Dict, List

from app.backend.services.constants import JOB_FUNCTION_SKILL_TAXONOMY

# ─── Constants ────────────────────────────────────────────────────────────────

SHORT_GENERIC_SKILLS = {
    "programming", "coding", "software", "technology", "tools",
    "it", "tech", "development", "engineering", "computer",
}

ACTION_VERBS = {
    "design", "build", "implement", "develop", "lead", "manage",
    "architect", "optimize", "maintain", "create", "deploy",
    "analyze", "collaborate", "drive", "establish", "define",
    "deliver", "ensure", "conduct", "evaluate", "coordinate",
}

GENERIC_PHRASES = [
    "various duties", "as needed", "other tasks", "ad hoc",
    "miscellaneous", "etc", "and so on",
]

SENIORITY_KEYWORDS = ["junior", "mid", "senior", "lead", "principal", "staff"]

EXPERIENCE_PATTERNS = [
    re.compile(r"\d[\d–\-\s]*\d?\s*\+?\s*years?\s*(of\s+)?(experience|exp)", re.I),
    re.compile(r"(\d+)\s*[-–to]+\s*(\d+)\s+years?\s*(of\s+)?(experience|exp)?", re.I),
    re.compile(r"(senior|junior|mid|lead|principal|staff)[- ]?level", re.I),
    re.compile(r"minimum\s+\d+\s+years?", re.I),
    re.compile(r"at least\s+\d+\s+years?", re.I),
]


# ─── Dimension scorers ────────────────────────────────────────────────────────

def _score_skill_clarity(jd_analysis: dict) -> tuple:
    """Score skill clarity (0-20)."""
    score = 0
    feedback_parts: List[str] = []

    required = jd_analysis.get("required_skills", []) or []
    nice_to_have = jd_analysis.get("nice_to_have_skills", []) or []

    # Both required and nice-to-have present?
    if required and nice_to_have:
        score += 5
    elif required or nice_to_have:
        score += 2
        feedback_parts.append("Include both required and nice-to-have skills for clarity")
    else:
        feedback_parts.append("No skills listed — add required and nice-to-have sections")

    # Required skills count optimal 4-12
    req_count = len(required)
    if 4 <= req_count <= 12:
        score += 5
    elif req_count < 3:
        score += 0
        feedback_parts.append(f"Only {req_count} required skills — aim for 4-12 specific requirements")
    elif req_count > 12:
        score += max(0, 5 - 3 * ((req_count - 12) // 3))
        feedback_parts.append(f"{req_count} required skills is excessive — narrow to 4-12 core ones")

    # Nice-to-have count optimal 2-8
    nth_count = len(nice_to_have)
    if 2 <= nth_count <= 8:
        score += 5
    elif nth_count == 0:
        score += 1
        feedback_parts.append("Add 2-8 nice-to-have skills to differentiate ideal candidates")
    elif nth_count > 8:
        score += max(0, 5 - (nth_count - 8))
        feedback_parts.append(f"{nth_count} nice-to-have skills is excessive — keep to 2-8")

    # Skills are specific (not generic)
    all_skills = [s.lower() for s in required + nice_to_have]
    generic_count = sum(1 for s in all_skills if s.strip() in SHORT_GENERIC_SKILLS)
    if generic_count == 0:
        score += 5
    elif generic_count <= 2:
        score += 3
        feedback_parts.append("Replace generic skill terms (e.g. 'programming') with specific ones (e.g. 'Python')")
    else:
        score += 1
        feedback_parts.append("Several skills are too generic — use specific technology or domain names")

    feedback = "; ".join(feedback_parts) if feedback_parts else "Skill listing is well-structured and specific"
    return score, feedback


def _score_experience_specificity(jd_analysis: dict, jd_text: str) -> tuple:
    """Score experience specificity (0-20)."""
    score = 0
    feedback_parts: List[str] = []

    # Explicit years requirement
    required_years = jd_analysis.get("required_years", 0)
    if required_years and required_years > 0:
        score += 10
    else:
        feedback_parts.append("Add specific years of experience required (e.g. '3-5 years')")

    # Seniority in title
    role_title = (jd_analysis.get("role_title") or "").lower()
    has_seniority_in_title = any(kw in role_title for kw in SENIORITY_KEYWORDS)
    if has_seniority_in_title:
        score += 5
    else:
        feedback_parts.append("Include seniority level in the job title (e.g. 'Senior', 'Lead')")

    # JD text mentions specific progression
    has_exp_pattern = any(p.search(jd_text) for p in EXPERIENCE_PATTERNS)
    if has_exp_pattern:
        score += 5
    else:
        feedback_parts.append("Specify experience level in JD body (e.g. '3-5 years of experience')")

    feedback = "; ".join(feedback_parts) if feedback_parts else "Experience requirements are explicit and specific"
    return score, feedback


def _score_responsibility_quality(jd_analysis: dict, jd_text: str) -> tuple:
    """Score responsibility quality (0-20)."""
    score = 0
    feedback_parts: List[str] = []

    responsibilities = jd_analysis.get("key_responsibilities", []) or []

    # Has responsibilities
    if responsibilities:
        score += 5
    else:
        feedback_parts.append("Add a responsibilities section to the JD")
        feedback = "; ".join(feedback_parts)
        return score, feedback

    # Count of responsibilities 4-8 optimal
    resp_count = len(responsibilities)
    if 4 <= resp_count <= 8:
        score += 5
    elif resp_count < 3:
        score += 1
        feedback_parts.append(f"Only {resp_count} responsibilities — aim for 4-8 specific duties")
    elif resp_count > 10:
        score += 2
        feedback_parts.append(f"{resp_count} responsibilities is excessive — consolidate to 4-8 key ones")
    else:
        score += 3

    # Responsibilities start with action verbs
    action_verb_count = 0
    for resp in responsibilities:
        first_word = resp.strip().split()[0].lower() if resp.strip() else ""
        if first_word in ACTION_VERBS:
            action_verb_count += 1
    if action_verb_count >= len(responsibilities) * 0.5:
        score += 5
    elif action_verb_count > 0:
        score += 3
        feedback_parts.append("Start more responsibilities with strong action verbs (e.g. 'Design', 'Build', 'Lead')")
    else:
        score += 0
        feedback_parts.append("Start responsibilities with action verbs (e.g. 'Design', 'Implement', 'Lead')")

    # Penalize generic phrases (or reward their absence)
    generic_hits = 0
    for phrase in GENERIC_PHRASES:
        generic_hits += sum(1 for r in responsibilities if phrase in r.lower())
    jd_text_lower = jd_text.lower()
    generic_hits += sum(1 for p in GENERIC_PHRASES if p in jd_text_lower)
    if generic_hits == 0:
        score += 5  # No generic fluff — full credit
    else:
        penalty = min(generic_hits * 3, 5)  # cap penalty at 5
        score = max(0, score - penalty)
        feedback_parts.append("Remove vague phrases like 'various duties', 'as needed', 'other tasks'")

    feedback = "; ".join(feedback_parts) if feedback_parts else "Responsibilities are well-articulated with action verbs"
    return score, feedback


def _score_domain_coherence(jd_analysis: dict) -> tuple:
    """Score domain coherence (0-20)."""
    score = 0
    feedback_parts: List[str] = []

    job_function = jd_analysis.get("job_function", "other")
    required = [s.lower() for s in (jd_analysis.get("required_skills", []) or [])]

    taxonomy = JOB_FUNCTION_SKILL_TAXONOMY.get(job_function)

    if not taxonomy or not required:
        # No taxonomy or no skills — give partial credit
        score = 10 if not required else 5
        if not taxonomy:
            feedback_parts.append(f"Job function '{job_function}' not in taxonomy — domain coherence cannot be fully assessed")
        if not required:
            feedback_parts.append("No required skills to evaluate against domain")
        feedback = "; ".join(feedback_parts)
        return score, feedback

    core_skills = {s.lower() for s in taxonomy.get("core_skills", [])}
    adjacent_skills = {s.lower() for s in taxonomy.get("adjacent_skills", [])}
    irrelevant_skills = {s.lower() for s in taxonomy.get("irrelevant_skills", [])}

    # What % of required skills are in core or adjacent?
    matched = sum(1 for s in required if s in core_skills or s in adjacent_skills)
    match_pct = matched / len(required) if required else 0

    if match_pct >= 0.80:
        score = 20
    elif match_pct >= 0.60:
        score = 15
    elif match_pct >= 0.40:
        score = 10
        feedback_parts.append("Some required skills don't align with the detected job function — verify relevance")
    else:
        score = 5
        feedback_parts.append("Most required skills don't match the detected job function — review skill classifications")

    # Penalize irrelevant skills
    irrelevant_hits = sum(1 for s in required if s in irrelevant_skills)
    if irrelevant_hits > 0:
        penalty = irrelevant_hits * 3
        score = max(0, score - penalty)
        feedback_parts.append(f"{irrelevant_hits} required skill(s) are typically irrelevant for this job function")

    feedback = "; ".join(feedback_parts) if feedback_parts else "Required skills strongly align with the detected job function"
    return score, feedback


def _score_completeness(jd_text: str) -> tuple:
    """Score completeness (0-20)."""
    score = 0
    feedback_parts: List[str] = []
    jd_lower = jd_text.lower()

    # Responsibilities section
    if re.search(r"responsibilit|what you'?ll do|role involves|you will be|what you'll be doing", jd_lower):
        score += 4
    else:
        feedback_parts.append("Add a clear responsibilities section")

    # Requirements section
    if re.search(r"requirement|qualificat|what we need|must have|you need|you should have", jd_lower):
        score += 4
    else:
        feedback_parts.append("Add a clear requirements/qualifications section")

    # Nice-to-have section
    if re.search(r"nice to have|nice-to-have|preferred|bonus|plus|desirable|would be great", jd_lower):
        score += 4
    else:
        feedback_parts.append("Add a nice-to-have / preferred qualifications section")

    # Education mention
    if re.search(r"degree|bachelor|master|education|certification|diploma|b\.s\.|m\.s\.|ba |ma |bs |ms ", jd_lower):
        score += 4
    else:
        feedback_parts.append("Mention education or certification requirements")

    # Company/team context
    if re.search(r"about us|our team|we are|the company|who we are|about the company|our mission", jd_lower):
        score += 4
    else:
        feedback_parts.append("Add company or team context to attract better candidates")

    feedback = "; ".join(feedback_parts) if feedback_parts else "JD is well-structured with all key sections"
    return score, feedback


# ─── Grade helper ──────────────────────────────────────────────────────────────

def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 50:
        return "C"
    else:
        return "D"


# ─── Main entry point ─────────────────────────────────────────────────────────

def score_jd_quality(jd_text: str, jd_analysis: dict) -> dict:
    """Score a JD 0-100 across 5 dimensions.

    Args:
        jd_text: Raw JD text (used for section detection and pattern matching).
        jd_analysis: Parsed JD dict from the JD parser (must contain at least
            required_skills, nice_to_have_skills, key_responsibilities,
            required_years, role_title, job_function, seniority).

    Returns:
        Dict with overall_score, grade, dimensions, and improvement_tips.
    """
    sc_score, sc_feedback = _score_skill_clarity(jd_analysis)
    es_score, es_feedback = _score_experience_specificity(jd_analysis, jd_text)
    rq_score, rq_feedback = _score_responsibility_quality(jd_analysis, jd_text)
    dc_score, dc_feedback = _score_domain_coherence(jd_analysis)
    cp_score, cp_feedback = _score_completeness(jd_text)

    dimensions = {
        "skill_clarity": {"score": sc_score, "max": 20, "feedback": sc_feedback},
        "experience_specificity": {"score": es_score, "max": 20, "feedback": es_feedback},
        "responsibility_quality": {"score": rq_score, "max": 20, "feedback": rq_feedback},
        "domain_coherence": {"score": dc_score, "max": 20, "feedback": dc_feedback},
        "completeness": {"score": cp_score, "max": 20, "feedback": cp_feedback},
    }

    overall = sc_score + es_score + rq_score + dc_score + cp_score

    # Generate improvement tips from lowest-scoring dimensions
    sorted_dims = sorted(dimensions.items(), key=lambda x: x[1]["score"])
    improvement_tips: List[str] = []
    positive_phrases = {"well-structured", "well-articulated", "explicit and specific",
                        "strongly align", "are specific", "well-structured with all key sections"}
    for dim_name, dim_data in sorted_dims:
        if dim_data["score"] < dim_data["max"] and len(improvement_tips) < 4:
            # Extract the first actionable suggestion from feedback
            fb = dim_data["feedback"]
            # Skip if feedback is purely positive
            if any(p in fb.lower() for p in positive_phrases) and "; " not in fb:
                continue
            # Split on "; " and take the first part as a tip
            tip = fb.split("; ")[0] if "; " in fb else fb
            if tip and tip not in improvement_tips:
                improvement_tips.append(tip)

    return {
        "overall_score": overall,
        "grade": _grade(overall),
        "dimensions": dimensions,
        "improvement_tips": improvement_tips,
    }
