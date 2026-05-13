"""
Phase 2: Semantic Skill Matching with Context Validation

Enterprise-grade skill matching that goes beyond string matching to include:
1. Job function context validation
2. Skill hierarchy matching
3. Weighted scoring (70% required, 30% nice-to-have)
4. Soft skill awareness
"""

from typing import Dict, List, Tuple
from services.constants import (
    JOB_FUNCTION_SKILL_TAXONOMY,
    GENERIC_SOFT_SKILLS
)


def match_skills_enterprise(
    candidate_skills: List[str],
    jd_required_skills: List[str],
    jd_nice_to_have: List[str],
    job_function: str = "other"
) -> Dict:
    """
    Enterprise-grade skill matching with context validation.
    
    This function implements intelligent skill matching that considers:
    - Job function context (validates skills are relevant to the role)
    - Skill hierarchy (core vs adjacent vs irrelevant)
    - Soft skill handling (moved to nice-to-have by default)
    - Weighted scoring (70% required, 30% nice-to-have)
    
    Args:
        candidate_skills: Skills extracted from candidate resume
        jd_required_skills: Must-have skills from JD
        jd_nice_to_have: Nice-to-have skills from JD
        job_function: Job function identifier (e.g., "backend_engineering")
    
    Returns:
        Dict with detailed matching results:
        {
            "matched_required": List[str],  # Required skills candidate has
            "matched_nice_to_have": List[str],  # Nice-to-have skills candidate has
            "missing_required": List[str],  # Required skills candidate lacks
            "irrelevant_skills_filtered": List[str],  # Skills filtered as irrelevant
            "required_match_score": float,  # 0-100
            "nice_to_have_score": float,  # 0-100
            "weighted_skill_score": float,  # 0-100 (70% required + 30% nice)
            "match_quality": str,  # "excellent" | "good" | "fair" | "poor"
            "confidence": float  # 0-1
        }
    """
    # Normalize to lowercase for matching
    candidate_skills_lower = [s.lower().strip() for s in candidate_skills if s]
    jd_required_lower = [s.lower().strip() for s in jd_required_skills if s]
    jd_nice_lower = [s.lower().strip() for s in jd_nice_to_have if s]
    
    # Get job function taxonomy for context validation
    taxonomy = JOB_FUNCTION_SKILL_TAXONOMY.get(job_function, {})
    core_skills = [s.lower() for s in taxonomy.get("core_skills", [])]
    adjacent_skills = [s.lower() for s in taxonomy.get("adjacent_skills", [])]
    irrelevant_skills = [s.lower() for s in taxonomy.get("irrelevant_skills", [])]
    
    # Context validation: Filter out irrelevant skills from JD requirements
    validated_required = []
    filtered_irrelevant = []
    
    for skill in jd_required_lower:
        # Check if skill is irrelevant for this job function
        if any(irr in skill or skill in irr for irr in irrelevant_skills):
            filtered_irrelevant.append(skill)
            continue
        validated_required.append(skill)
    
    # If all skills were filtered, use original list (fallback)
    if not validated_required and jd_required_lower:
        validated_required = jd_required_lower
        filtered_irrelevant = []
    
    # Match required skills
    matched_required = []
    missing_required = []
    
    for req_skill in validated_required:
        # Direct match
        if any(req_skill in cand or cand in req_skill for cand in candidate_skills_lower):
            matched_required.append(req_skill)
        else:
            # Check for partial matches (e.g., "python" matches "python programming")
            partial_match = False
            for cand_skill in candidate_skills_lower:
                # Check if significant overlap (at least 70% character match)
                if _skill_similarity(req_skill, cand_skill) >= 0.70:
                    matched_required.append(req_skill)
                    partial_match = True
                    break
            
            if not partial_match:
                missing_required.append(req_skill)
    
    # Match nice-to-have skills
    matched_nice = []
    for nice_skill in jd_nice_lower:
        if any(nice_skill in cand or cand in nice_skill for cand in candidate_skills_lower):
            matched_nice.append(nice_skill)
        else:
            # Partial matching for nice-to-have too
            for cand_skill in candidate_skills_lower:
                if _skill_similarity(nice_skill, cand_skill) >= 0.70:
                    matched_nice.append(nice_skill)
                    break
    
    # Calculate scores
    total_required = len(validated_required)
    total_nice = len(jd_nice_lower)
    
    if total_required > 0:
        required_match_score = (len(matched_required) / total_required) * 100
    else:
        required_match_score = 100.0 if not jd_required_lower else 0.0
    
    if total_nice > 0:
        nice_to_have_score = (len(matched_nice) / total_nice) * 100
    else:
        nice_to_have_score = 50.0  # Neutral if no nice-to-have specified
    
    # Weighted score: 70% required + 30% nice-to-have
    weighted_skill_score = (0.70 * required_match_score) + (0.30 * nice_to_have_score)
    
    # Determine match quality
    if weighted_skill_score >= 85:
        match_quality = "excellent"
    elif weighted_skill_score >= 70:
        match_quality = "good"
    elif weighted_skill_score >= 50:
        match_quality = "fair"
    else:
        match_quality = "poor"
    
    # Confidence calculation
    confidence = _calculate_match_confidence(
        matched_required,
        missing_required,
        matched_nice,
        job_function,
        taxonomy
    )
    
    return {
        "matched_required": matched_required,
        "matched_nice_to_have": matched_nice,
        "missing_required": missing_required,
        "irrelevant_skills_filtered": filtered_irrelevant,
        "required_match_score": round(required_match_score, 2),
        "nice_to_have_score": round(nice_to_have_score, 2),
        "weighted_skill_score": round(weighted_skill_score, 2),
        "match_quality": match_quality,
        "confidence": round(confidence, 2),
        "total_required": total_required,
        "total_nice_to_have": total_nice,
    }


def _skill_similarity(skill1: str, skill2: str) -> float:
    """
    Calculate similarity between two skill names.
    
    Uses simple character-level similarity for now.
    Can be enhanced with embeddings in future.
    
    Examples:
    - "python" vs "python programming" → high similarity
    - "react" vs "react.js" → high similarity
    - "fastapi" vs "django" → low similarity
    """
    if not skill1 or not skill2:
        return 0.0
    
    # Exact match
    if skill1 == skill2:
        return 1.0
    
    # One contains the other (strong signal)
    if skill1 in skill2 or skill2 in skill1:
        shorter = min(len(skill1), len(skill2))
        longer = max(len(skill1), len(skill2))
        # Boost the score - if one contains another, it's likely related
        containment_ratio = shorter / longer
        # Return higher score for containment
        if containment_ratio > 0.6:
            return 0.85 + (containment_ratio * 0.15)
        elif containment_ratio > 0.3:
            return 0.70 + (containment_ratio * 0.15)
        else:
            return 0.50 + (containment_ratio * 0.20)
    
    # Character-level similarity (Jaccard similarity of character n-grams)
    n = 2  # Use bigrams
    ngrams1 = set([skill1[i:i+n] for i in range(len(skill1)-n+1)])
    ngrams2 = set([skill2[i:i+n] for i in range(len(skill2)-n+1)])
    
    if not ngrams1 or not ngrams2:
        return 0.0
    
    intersection = ngrams1 & ngrams2
    union = ngrams1 | ngrams2
    
    return len(intersection) / len(union) if union else 0.0


def _calculate_match_confidence(
    matched_required: List[str],
    missing_required: List[str],
    matched_nice: List[str],
    job_function: str,
    taxonomy: Dict
) -> float:
    """
    Calculate confidence in the match quality.
    
    Confidence is higher when:
    - Most required skills are matched
    - Matched skills are core skills (not adjacent)
    - Few missing critical skills
    """
    total_required = len(matched_required) + len(missing_required)
    
    if total_required == 0:
        return 0.5  # Neutral confidence if no requirements
    
    # Base confidence from match ratio
    match_ratio = len(matched_required) / total_required
    confidence = match_ratio
    
    # Boost confidence if matching core skills
    core_skills = [s.lower() for s in taxonomy.get("core_skills", [])]
    core_matched = sum(1 for s in matched_required if s in core_skills)
    
    if len(matched_required) > 0:
        core_ratio = core_matched / len(matched_required)
        confidence = (confidence * 0.7) + (core_ratio * 0.3)
    
    # Reduce confidence if many critical skills missing
    if len(missing_required) > total_required * 0.5:
        confidence *= 0.8
    
    return max(0.0, min(1.0, confidence))


def validate_skill_against_job_function(
    skill: str,
    job_function: str
) -> Dict:
    """
    Validate if a skill is relevant for a specific job function.
    
    Returns:
        {
            "skill": str,
            "job_function": str,
            "is_relevant": bool,
            "category": "core" | "adjacent" | "irrelevant" | "unknown",
            "confidence": float
        }
    """
    skill_lower = skill.lower().strip()
    taxonomy = JOB_FUNCTION_SKILL_TAXONOMY.get(job_function, {})
    
    core_skills = [s.lower() for s in taxonomy.get("core_skills", [])]
    adjacent_skills = [s.lower() for s in taxonomy.get("adjacent_skills", [])]
    irrelevant_skills = [s.lower() for s in taxonomy.get("irrelevant_skills", [])]
    
    # Check core skills
    if any(skill_lower in core or core in skill_lower for core in core_skills):
        return {
            "skill": skill,
            "job_function": job_function,
            "is_relevant": True,
            "category": "core",
            "confidence": 0.95
        }
    
    # Check adjacent skills
    if any(skill_lower in adj or adj in skill_lower for adj in adjacent_skills):
        return {
            "skill": skill,
            "job_function": job_function,
            "is_relevant": True,
            "category": "adjacent",
            "confidence": 0.75
        }
    
    # Check irrelevant skills
    if any(skill_lower in irr or irr in skill_lower for irr in irrelevant_skills):
        return {
            "skill": skill,
            "job_function": job_function,
            "is_relevant": False,
            "category": "irrelevant",
            "confidence": 0.90
        }
    
    # Unknown - neutral
    return {
        "skill": skill,
        "job_function": job_function,
        "is_relevant": True,  # Assume relevant if unknown
        "category": "unknown",
        "confidence": 0.50
    }
