"""Skill proficiency estimation service.

Moved from routes/analyze.py to allow reuse across the codebase.
"""

from __future__ import annotations


PROFICIENCY_CUE_MAP: dict[str, list[str]] = {
    "expert": [
        "expert in", "deep knowledge of", "mastery of",
        "extensive experience with", "8+ years", "10+ years",
        "expert-level", "deep expertise",
    ],
    "advanced": [
        "proficient in", "solid experience", "strong knowledge",
        "strong background", "5+ years", "6+ years", "7+ years",
        "proven track record with", "advanced knowledge",
        "hands-on experience",
    ],
    "intermediate": [
        "working knowledge of", "experience with", "good understanding",
        "2+ years", "3+ years", "4+ years", "comfortable with",
    ],
    "basic": [
        "basic understanding of", "exposure to", "awareness of",
        "familiarity with", "knowledge of", "1+ year",
        "some experience",
    ],
}

_PROFICIENCY_RANK = {"basic": 0, "intermediate": 1, "advanced": 2, "expert": 3}

_SENIORITY_DEFAULT_PROFICIENCY: dict[str, str] = {
    "junior": "basic",
    "mid": "intermediate",
    "senior": "advanced",
    "lead": "expert",
    "principal": "expert",
}


def estimate_skill_proficiency(
    skill: str,
    seniority: str,
    jd_text: str,
    is_nice_to_have: bool = False,
) -> str:
    """Estimate the expected proficiency level for a skill based on
    linguistic cues in the JD text and the role's seniority.

    Priority order:
      1. Cue-based detection (±150 chars around skill mention)
      2. Seniority-based default
      3. Nice-to-have cap (one level below seniority default)

    Returns one of: "basic", "intermediate", "advanced", "expert".
    """
    jd_lower = jd_text.lower()
    skill_lower = skill.lower()
    pos = jd_lower.find(skill_lower)

    # --- Step 1: Try cue-based detection around the skill mention ---
    if pos >= 0:
        ctx_start = max(0, pos - 150)
        ctx_end = min(len(jd_text), pos + len(skill_lower) + 150)
        context = jd_lower[ctx_start:ctx_end]

        for level in ("expert", "advanced", "intermediate", "basic"):
            if any(cue in context for cue in PROFICIENCY_CUE_MAP[level]):
                proficiency = level
                break
        else:
            proficiency = None
    else:
        proficiency = None

    # --- Step 2: Fall back to seniority-based default ---
    if proficiency is None:
        proficiency = _SENIORITY_DEFAULT_PROFICIENCY.get(seniority.lower(), "intermediate")

    # --- Step 3: Nice-to-have cap — one level below seniority default ---
    if is_nice_to_have:
        seniority_default = _SENIORITY_DEFAULT_PROFICIENCY.get(
            seniority.lower(), "intermediate"
        )
        cap_rank = max(_PROFICIENCY_RANK[seniority_default] - 1, 0)
        if _PROFICIENCY_RANK[proficiency] > cap_rank:
            proficiency = [k for k, v in _PROFICIENCY_RANK.items() if v == cap_rank][0]

    return proficiency
