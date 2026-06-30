"""
JD Profile Service — domain-agnostic job description extraction.

Uses LLM to extract a structured profile (domain, skills, education fields,
role signals, experience range) from any JD, then merges it with the rule-based
parser so the downstream scorer works for tech and non-tech roles alike.
"""

import hashlib
import logging
from typing import Dict, Any, List, Optional

from app.backend.services.llm_service import extract_jd_profile_with_llm

log = logging.getLogger(__name__)

# In-memory cache for LLM JD profiles, keyed by JD hash.  This avoids repeated
# LLM calls when the same JD is analyzed multiple times in a single batch.
_LLM_JD_CACHE: Dict[str, Any] = {}


def _jd_hash(jd_text: str) -> str:
    return hashlib.md5(jd_text[:2000].encode()).hexdigest()


async def extract_jd_profile(jd_text: str) -> Dict[str, Any]:
    """Async LLM extraction of a domain-agnostic JD profile.

    Caches the result in memory per JD hash so batch processing reuses the same
    LLM profile without hitting the model multiple times.
    """
    h = _jd_hash(jd_text)
    cached = _LLM_JD_CACHE.get(h)
    if cached is not None:
        return cached
    result = await extract_jd_profile_with_llm(jd_text)
    _LLM_JD_CACHE[h] = result
    return result


_PLACEHOLDER_VALUES = {"", "not specified", "not mentioned", "unknown", "n/a", "na", "none", "null"}


def _is_meaningful(value: Optional[str]) -> bool:
    """Return True if a string value is meaningful (not empty/placeholder)."""
    if not value:
        return False
    return str(value).strip().lower() not in _PLACEHOLDER_VALUES


def merge_jd_profile(rules_jd: Dict[str, Any], llm_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Merge LLM-extracted fields into the rule-based JD analysis.

    The LLM profile is the authoritative source for domain, role signals, and
    education fields, but meaningful prebuilt values are preserved.  Rule-based
    parsing is kept as fallback for missing values.
    """
    merged = dict(rules_jd)

    if not llm_profile or llm_profile.get("_source") == "fallback":
        merged.setdefault("_profile_source", "rules")
        return merged

    # LLM overrides role title and domain when it provides a meaningful value
    merged["role_title"] = (
        llm_profile.get("role_title") if _is_meaningful(llm_profile.get("role_title"))
        else rules_jd.get("role_title", "Not specified")
    )
    merged["domain"] = llm_profile.get("domain") or rules_jd.get("domain", "other")
    merged["seniority"] = (
        llm_profile.get("seniority") if _is_meaningful(llm_profile.get("seniority"))
        else rules_jd.get("seniority", "mid")
    )

    # Experience range: prefer LLM min/max; keep rules-based required_years for compatibility
    merged["min_required_years"] = llm_profile.get("min_required_years", 0) or rules_jd.get("required_years", 0)
    merged["max_required_years"] = llm_profile.get("max_required_years", 0)
    if merged["max_required_years"] and merged["max_required_years"] < merged["min_required_years"]:
        merged["max_required_years"] = merged["min_required_years"]
    # For backward compatibility, set required_years to the min when rules didn't find it
    if not rules_jd.get("required_years"):
        merged["required_years"] = merged["min_required_years"]

    # Skills: merge, deduplicate, preserve LLM order
    llm_required = llm_profile.get("required_skills", [])
    rules_required = rules_jd.get("required_skills", [])
    merged["required_skills"] = _dedupe_skills(llm_required + [s for s in rules_required if s.lower() not in {r.lower() for r in llm_required}])

    llm_nice = llm_profile.get("nice_to_have_skills", [])
    rules_nice = rules_jd.get("nice_to_have_skills", [])
    # Remove any nice-to-have that is already in required
    merged["nice_to_have_skills"] = _dedupe_skills(
        [s for s in llm_nice if s.lower() not in {r.lower() for r in merged["required_skills"]}] +
        [s for s in rules_nice if s.lower() not in {r.lower() for r in merged["required_skills"]}]
    )

    # Domain-specific signals from the LLM
    merged["domain_keywords"] = llm_profile.get("domain_keywords", []) or merged.get("domain_keywords", [])
    merged["architecture_signals"] = llm_profile.get("architecture_signals", []) or merged.get("architecture_signals", [])
    merged["relevant_education_fields"] = llm_profile.get("relevant_education_fields", []) or merged.get("relevant_education_fields", [])

    merged["_profile_source"] = "merged"
    return merged


def _dedupe_skills(skills: List[str]) -> List[str]:
    """Deduplicate skills case-insensitively while preserving order."""
    seen = set()
    result = []
    for s in skills:
        norm = s.lower()
        if norm and norm not in seen:
            seen.add(norm)
            result.append(s)
    return result
