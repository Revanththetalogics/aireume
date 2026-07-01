"""Enhanced proficiency level detection service.

Analyzes resume text to estimate proficiency levels beyond simple
years-of-experience heuristics. Considers project complexity, team
size, role seniority indicators, and contextual signals.
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Proficiency levels (aligned with industry standards)
PROFICIENCY_LEVELS = ["beginner", "intermediate", "advanced", "expert"]

# Indicators of seniority/depth for each level
SENIORITY_INDICATORS = {
    "expert": [
        r'\barchitect(?:ed|ing)?\b', r'\bdesigned\b.*\bsystem\b',
        r'\bprincipal\b', r'\bstaff\b.*\bengineer\b',
        r'\btech lead\b', r'\btechnical lead\b',
        r'\bspearheaded\b', r'\bpioneered\b',
        r'\binvented\b', r'\bfounded\b.*\bteam\b',
        r'\bestablished\b.*\bpractice\b',
        r'\bauthor(?:ed)?\b.*\b(?:standard|guideline|framework)\b',
        r'\bpatent(?:ed)?\b',
        r'\bconference\b.*\bspeaker\b',
        r'\bkeynote\b',
        r'\bopen.?source\b.*\b(?:maintainer|contributor)\b',
        r'\breviewer\b.*\b(?:paper|patent|proposal)\b',
    ],
    "advanced": [
        r'\bsenior\b', r'\blead\b', r'\bmentored\b',
        r'\bmanaged\b.*\bteam\b', r'\bsupervised\b',
        r'\boptimized\b', r'\brefactored\b',
        r'\bscaled\b.*\b(?:system|infrastructure|application)\b',
        r'\bmigrated\b', r'\bupgraded\b',
        r'\bimplemented\b.*\b(?:end-to-end|production|enterprise)\b',
        r'\bowned\b.*\b(?:component|module|service)\b',
        r'\bdrove\b.*\b(?:initiative|effort|project)\b',
        r'\bestablished\b.*\b(?:process|standard)\b',
    ],
    "intermediate": [
        r'\bdeveloped\b', r'\bbuilt\b', r'\bcreated\b',
        r'\bcontributed\b', r'\bparticipated\b',
        r'\bworked\b.*\bon\b', r'\bassisted\b',
        r'\bcollaborated\b', r'\bsupported\b',
        r'\bintegrated\b', r'\bconfigured\b',
        r'\b(?:2|3|4|5)\s+years?\b',
    ],
    "beginner": [
        r'\bintern(?:ship)?\b', r'\bjunior\b',
        r'\btrainee\b', r'\bentry.level\b',
        r'\bstudent\b', r'\bcoursework\b',
        r'\bacademic\b.*\bproject\b',
        r'\bbootcamp\b', r'\blearning\b',
        r'\b(?:0|1)\s+years?\b', r'\bfamiliar\b.*\bwith\b',
    ],
}

# Team size indicators
TEAM_SIZE_PATTERNS = [
    (r'\b(\d+)\s*[-+]?\s*(?:member|person|people|engineer|developer)s?\s+team\b', "team_size"),
    (r'\bteam\s+of\s+(\d+)\b', "team_size"),
    (r'\bled\s+a\s+team\s+of\s+(\d+)\b', "team_size"),
    (r'\bmanaged\s+(\d+)\s+(?:engineer|developer|person|member)s?\b', "direct_reports"),
]

# Project complexity indicators
COMPLEXITY_INDICATORS = {
    "high": [
        r'\benterprise\b', r'\bglobal\b', r'\bmission.critical\b',
        r'\bhigh.traffic\b', r'\bmillions?\s+of\s+(?:users|request|record)s?\b',
        r'\bbillion\b', r'\bpetabyte\b', r'\bterabyte\b',
        r'\b(?:microservice|distributed)\s+(?:system|architecture)\b',
        r'\breal.time\b', r'\blow.latency\b', r'\bhigh.availability\b',
        r'\b99\.9\d+%\s+uptime\b', r'\bSLA\b',
    ],
    "medium": [
        r'\bproduction\b', r'\bscalable\b', r'\bmulti.tenant\b',
        r'\bAPI\b.*\bintegration\b', r'\bthird.party\b',
        r'\bcloud\b.*\b(?:migration|deployment)\b',
        r'\bCI/CD\b', r'\bautomated\b',
    ],
    "low": [
        r'\bprototype\b', r'\bproof.of.concept\b', r'\bPOC\b',
        r'\binternal\s+tool\b', r'\bscript\b',
        r'\bhomework\b', r'\bassignment\b',
    ],
}


def detect_proficiency(resume_text: str, skill_name: Optional[str] = None) -> Dict[str, Any]:
    """Detect proficiency level from resume text.

    Args:
        resume_text: Full resume text.
        skill_name: Optional specific skill to assess proficiency for.

    Returns:
        Dict with proficiency_level, confidence, evidence, team_size,
        project_complexity, and seniority_indicators.
    """
    if not resume_text:
        return {
            "proficiency_level": "beginner",
            "confidence": 0.0,
            "evidence": [],
            "team_size": None,
            "project_complexity": "unknown",
            "seniority_indicators": [],
        }

    text_lower = resume_text.lower()

    # If a specific skill is provided, look for context around it
    search_text = text_lower
    if skill_name:
        # Extract a window of text around each mention of the skill
        skill_lower = skill_name.lower()
        windows = []
        for match in re.finditer(re.escape(skill_lower), text_lower):
            start = max(0, match.start() - 200)
            end = min(len(text_lower), match.end() + 200)
            windows.append(text_lower[start:end])
        search_text = " ".join(windows) if windows else text_lower

    # Detect seniority indicators
    indicators_found = []
    level_scores = {"beginner": 0, "intermediate": 0, "advanced": 0, "expert": 0}

    for level, patterns in SENIORITY_INDICATORS.items():
        for pattern in patterns:
            matches = re.findall(pattern, search_text)
            if matches:
                level_scores[level] += len(matches)
                indicators_found.extend(matches[:3])  # Keep up to 3 examples

    # Determine proficiency level based on weighted scoring
    # Higher levels override lower ones
    if level_scores["expert"] >= 2:
        proficiency = "expert"
    elif level_scores["expert"] >= 1 and level_scores["advanced"] >= 1:
        proficiency = "expert"
    elif level_scores["advanced"] >= 2:
        proficiency = "advanced"
    elif level_scores["advanced"] >= 1 or level_scores["intermediate"] >= 3:
        proficiency = "advanced"
    elif level_scores["intermediate"] >= 1:
        proficiency = "intermediate"
    else:
        proficiency = "beginner"

    # Confidence based on number of indicators found
    total_indicators = sum(level_scores.values())
    confidence = min(1.0, total_indicators / 5.0)

    # Detect team size
    team_size = None
    for pattern, label in TEAM_SIZE_PATTERNS:
        match = re.search(pattern, search_text)
        if match:
            team_size = int(match.group(1))
            break

    # Detect project complexity
    complexity = "unknown"
    for level, patterns in COMPLEXITY_INDICATORS.items():
        for pattern in patterns:
            if re.search(pattern, search_text):
                complexity = level
                break
        if complexity != "unknown":
            break

    return {
        "proficiency_level": proficiency,
        "confidence": round(confidence, 2),
        "evidence": indicators_found[:5],
        "team_size": team_size,
        "project_complexity": complexity,
        "seniority_indicators": indicators_found[:5],
    }


def assess_skill_proficiency(resume_text: str, matched_skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assess proficiency for each matched skill.

    Args:
        resume_text: Full resume text.
        matched_skills: List of matched skill dicts from skill_matcher.

    Returns:
        Enhanced matched_skills with proficiency_level and confidence added.
    """
    enhanced = []
    for skill in matched_skills:
        skill_name = skill.get("skill") or skill.get("name", "")
        proficiency = detect_proficiency(resume_text, skill_name)
        enhanced.append({
            **skill,
            "proficiency_level": proficiency["proficiency_level"],
            "proficiency_confidence": proficiency["confidence"],
            "team_size": proficiency["team_size"],
            "project_complexity": proficiency["project_complexity"],
        })
    return enhanced
