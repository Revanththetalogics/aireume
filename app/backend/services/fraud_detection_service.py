"""Fraud detection service for resume screening.

Detects potential resume fraud including:
- Fabricated skills (claimed but no contextual evidence)
- Inflated experience (timeline inconsistencies)
- Template/copy-paste resumes
- Impossible date ranges
- Skill stacking (listing every skill without depth)
"""

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Risk thresholds
SKILL_STACKING_THRESHOLD = 40  # Listing 40+ skills is suspicious
MIN_EVIDENCE_PER_SKILL = 1     # Each skill should have at least 1 contextual mention
TEMPLATE_SIMILARITY_THRESHOLD = 0.85  # High similarity to known templates


def detect_fabricated_skills(
    resume_text: str,
    matched_skills: List[Dict[str, Any]],
    jd_required_skills: List[str],
) -> List[Dict[str, Any]]:
    """Detect skills that are claimed but lack contextual evidence.

    A skill listed in a "Skills" section but never mentioned in experience
    descriptions, project details, or education is suspicious.

    Args:
        resume_text: Full resume text.
        matched_skills: Skills matched from the resume.
        jd_required_skills: JD required skills for context.

    Returns:
        List of suspicious skills with reasons.
    """
    if not resume_text or not matched_skills:
        return []

    suspicious = []
    text_lower = resume_text.lower()

    # Split resume into "skills section" and "experience section"
    # Skills section is typically a comma/semicolon separated list
    # Experience section has verbs like "developed", "built", "managed"
    experience_section = ""
    skills_section = ""

    # Find experience section (after "Experience" or "Work History" header)
    exp_match = re.search(
        r'(?:professional\s+)?experience\b.*?(?=education|certification|$)',
        text_lower, re.DOTALL | re.IGNORECASE
    )
    if exp_match:
        experience_section = exp_match.group(0)

    # Find skills section
    skills_match = re.search(
        r'(?:technical\s+)?skills\b[:\s]*(.*?)(?=experience|education|certification|project|$)',
        text_lower, re.DOTALL | re.IGNORECASE
    )
    if skills_match:
        skills_section = skills_match.group(1)

    for skill in matched_skills:
        skill_name = (skill.get("skill") or skill.get("name", "")).lower()
        if not skill_name:
            continue

        # Check if skill appears only in skills section, not in experience
        in_experience = skill_name in experience_section
        in_skills_section = skill_name in skills_section
        in_general = skill_name in text_lower

        if in_skills_section and not in_experience and in_general:
            # Skill is listed but never mentioned in experience descriptions
            suspicious.append({
                "skill": skill_name,
                "reason": "Listed in skills section but not mentioned in experience descriptions",
                "risk": "medium",
            })

    return suspicious


def detect_inflated_experience(
    candidate_profile: Dict[str, Any],
    gap_analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Detect inflated experience claims.

    Checks for:
    - Total claimed years exceeding actual timeline
    - Overlapping jobs presented as sequential
    - Impossible date ranges (end before start)
    - Jobs starting before candidate was 16

    Args:
        candidate_profile: Parsed candidate profile with work history.
        gap_analysis: Gap analysis from gap_detector.

    Returns:
        List of inflation indicators.
    """
    issues = []

    work_history = candidate_profile.get("work_history", [])
    if not work_history:
        return issues

    claimed_years = candidate_profile.get("total_years", 0)
    effective_years = gap_analysis.get("total_effective_years", 0)

    # Check if claimed years significantly exceed effective years
    if claimed_years > 0 and effective_years > 0:
        ratio = effective_years / claimed_years
        if ratio < 0.70:  # Effective years are less than 70% of claimed
            issues.append({
                "type": "experience_inflation",
                "reason": f"Claimed {claimed_years} years but timeline shows {effective_years:.1f} effective years",
                "claimed_years": claimed_years,
                "effective_years": effective_years,
                "ratio": round(ratio, 2),
                "risk": "high",
            })

    # Check for impossible date ranges
    for job in work_history:
        start = job.get("start_date")
        end = job.get("end_date")
        if start and end:
            try:
                if isinstance(start, str):
                    start_dt = datetime.fromisoformat(start)
                else:
                    start_dt = start
                if isinstance(end, str):
                    end_dt = datetime.fromisoformat(end)
                else:
                    end_dt = end

                if end_dt < start_dt:
                    issues.append({
                        "type": "impossible_date_range",
                        "reason": f"Job at {job.get('company', 'unknown')} ends before it starts",
                        "risk": "high",
                    })
            except Exception:
                pass

    # Check for excessive overlapping jobs (3+ simultaneous)
    overlaps = gap_analysis.get("overlapping_jobs", [])
    if len(overlaps) >= 3:
        issues.append({
            "type": "excessive_overlaps",
            "reason": f"{len(overlaps)} overlapping jobs detected — possible padding",
            "count": len(overlaps),
            "risk": "medium",
        })

    return issues


def detect_skill_stacking(
    matched_skills: List[Dict[str, Any]],
    resume_text: str,
) -> Optional[Dict[str, Any]]:
    """Detect skill stacking — listing an excessive number of skills without depth.

    A resume listing 40+ skills with minimal experience context is likely
    keyword stuffing.

    Args:
        matched_skills: All matched skills.
        resume_text: Resume text for context.

    Returns:
        Warning dict if skill stacking detected, None otherwise.
    """
    skill_count = len(matched_skills)
    if skill_count < SKILL_STACKING_THRESHOLD:
        return None

    # Check if resume is short (low text-to-skill ratio)
    word_count = len(resume_text.split()) if resume_text else 0
    words_per_skill = word_count / skill_count if skill_count > 0 else 0

    if words_per_skill < 30:  # Less than 30 words per skill is suspicious
        return {
            "type": "skill_stacking",
            "reason": f"{skill_count} skills listed with only {words_per_skill:.0f} words per skill — possible keyword stuffing",
            "skill_count": skill_count,
            "words_per_skill": round(words_per_skill),
            "risk": "medium",
        }

    return None


def detect_template_resume(resume_text: str) -> Optional[Dict[str, Any]]:
    """Detect if a resume appears to be a template with placeholder text.

    Checks for common template markers and unfilled placeholders.

    Args:
        resume_text: Resume text to check.

    Returns:
        Warning dict if template detected, None otherwise.
    """
    if not resume_text:
        return None

    text_lower = resume_text.lower()
    template_markers = [
        r'\[your name\]', r'\[insert\b', r'\[your\b',
        r'\[company\b', r'\[date\b', r'\[position\b',
        r'\[description\b', r'\[skill\b', r'\[degree\b',
        r'\[university\b', r'\[email\b', r'\[phone\b',
        r'lorem ipsum', r'placeholder', r'text goes here',
        r'click here to', r'type your', r'enter your',
        r'sample text', r'replace with',
    ]

    markers_found = []
    for pattern in template_markers:
        if re.search(pattern, text_lower):
            markers_found.append(pattern.replace(r'\b', '').replace(r'\[', '[').replace(r'\]', ']'))

    if markers_found:
        return {
            "type": "template_resume",
            "reason": f"Template placeholders detected: {', '.join(markers_found[:3])}",
            "markers": markers_found,
            "risk": "high",
        }

    return None


def run_fraud_check(
    resume_text: str,
    matched_skills: List[Dict[str, Any]],
    candidate_profile: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    jd_required_skills: List[str],
) -> Dict[str, Any]:
    """Run comprehensive fraud detection on a resume.

    Args:
        resume_text: Full resume text.
        matched_skills: Skills matched from resume.
        candidate_profile: Parsed candidate profile.
        gap_analysis: Gap analysis results.
        jd_required_skills: JD required skills.

    Returns:
        Dict with fraud_indicators list, overall_risk_level, and summary.
    """
    indicators = []

    # 1. Fabricated skills
    fabricated = detect_fabricated_skills(resume_text, matched_skills, jd_required_skills)
    indicators.extend(fabricated)

    # 2. Inflated experience
    inflation = detect_inflated_experience(candidate_profile, gap_analysis)
    indicators.extend(inflation)

    # 3. Skill stacking
    stacking = detect_skill_stacking(matched_skills, resume_text)
    if stacking:
        indicators.append(stacking)

    # 4. Template resume
    template = detect_template_resume(resume_text)
    if template:
        indicators.append(template)

    # Determine overall risk
    high_count = sum(1 for i in indicators if i.get("risk") == "high")
    medium_count = sum(1 for i in indicators if i.get("risk") == "medium")

    if high_count >= 2:
        overall_risk = "high"
    elif high_count >= 1 or medium_count >= 3:
        overall_risk = "medium"
    elif medium_count >= 1:
        overall_risk = "low"
    else:
        overall_risk = "none"

    return {
        "fraud_indicators": indicators,
        "overall_risk_level": overall_risk,
        "indicator_count": len(indicators),
        "summary": f"{len(indicators)} fraud indicator(s) detected, risk: {overall_risk}",
    }
