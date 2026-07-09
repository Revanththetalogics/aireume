"""
Normalize resume/JD text fields before scoring, kit generation, and LLM prompts.

Strips PDF/RTF extraction artifacts (dangling braces), header-like JD lines,
and sentence-shaped pseudo-skills so downstream templates stay readable and
LLM tokens are not wasted on corrupted context.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_BRACE_RE = re.compile(r"[{}]+")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_PREFIX_RE = re.compile(
    r"^(?:job\s+description\s*[:/]\s*|jd\s*[:/]\s*|role\s*[:/]\s*|"
    r"position\s*[:/]\s*|title\s*[:/]\s*|about\s+(?:the\s+)?role\s*[:/]\s*)",
    re.IGNORECASE,
)

_HEADER_RESP_RE = re.compile(
    r"^(?:job\s+description|position\s+title|role\s+title|about\s+the\s+role)\b",
    re.IGNORECASE,
)

_SENTENCE_SKILL_RE = re.compile(
    r"\b\d{1,2}\s*[-–—]\s*\d{1,2}\s+years?\b"
    r"|\byears?\s+of\s+(?:relevant\s+)?experience\b"
    r"|\bexperience\s+in\b"
    r"|\bminimum\s+of\s+\d+\s+years?\b",
    re.IGNORECASE,
)

_ACTION_VERB_RE = re.compile(
    r"\b(?:manage|lead|develop|build|implement|drive|coordinate|support|ensure|"
    r"create|maintain|deliver|conduct|partner|collaborate|oversee|recruit|hire|"
    r"source|design|analyze|plan|execute|monitor|improve|establish|provide|"
    r"prepare|review|negotiate|advise|mentor|train|report|own|handle)\w*\b",
    re.IGNORECASE,
)

_TITLE_KEYWORDS = re.compile(
    r"\b(?:Engineer|Developer|Manager|Director|Analyst|Architect|"
    r"Designer|Consultant|Administrator|Specialist|Coordinator|"
    r"Lead|Senior|Junior|Principal|Staff|Intern|Associate|Officer|"
    r"Executive|Supervisor|Technician|Programmer|Scientist|Researcher|"
    r"Recruiter|Consultant)\b",
    re.IGNORECASE,
)

_COMPANY_KEYWORDS = re.compile(
    r"\b(?:Ltd\.?|Inc\.?|Corp\.?|LLC|LLP|Pvt\.?|Private|Limited|"
    r"Corporation|Company|Co\.?|Group|Solutions|Technologies|"
    r"Systems|Services|Software|Labs?|Laboratories|Industries|"
    r"Enterprises|Associates|Partners|International|Global)\b",
    re.IGNORECASE,
)

_COMPANY_SUFFIX_RE = re.compile(
    r"(?:Labs|Technologies|Tech|Solutions|Systems|Services|Software|Group|Corp|Inc|LLC|Ltd)\.?$",
    re.IGNORECASE,
)

_JOB_TITLE_ENDING_RE = re.compile(
    r"\b(?:specialist|consultant|director|coordinator|recruiter)\s*$",
    re.IGNORECASE,
)

_PLACEHOLDER_VALUES = {"", "n/a", "na", "unknown", "not specified", "none"}


def _looks_like_company(text: str) -> bool:
    clean = sanitize_profile_text(text)
    if not clean:
        return False
    return bool(_COMPANY_KEYWORDS.search(clean) or _COMPANY_SUFFIX_RE.search(clean))


def _looks_like_role_title(text: str) -> bool:
    clean = sanitize_profile_text(text)
    if not clean:
        return False
    return bool(_TITLE_KEYWORDS.search(clean))


def sanitize_profile_text(text: Optional[str], max_len: Optional[int] = None) -> str:
    """Strip braces, control chars, and common junk prefixes from a profile field."""
    if not text or not isinstance(text, str):
        return ""
    cleaned = _CONTROL_RE.sub(" ", text)
    cleaned = _BRACE_RE.sub(" ", cleaned)
    cleaned = " ".join(cleaned.split())
    cleaned = _PREFIX_RE.sub("", cleaned).strip()
    cleaned = cleaned.strip(" .,;:-–—|/")
    cleaned = " ".join(cleaned.split())
    if max_len and len(cleaned) > max_len:
        cut = cleaned[:max_len].rsplit(" ", 1)[0].strip()
        cleaned = cut or cleaned[:max_len].strip()
    return cleaned


def is_plausible_skill_name(skill: Optional[str]) -> bool:
    """Reject sentence-shaped or corrupted values masquerading as skills."""
    if not skill or not isinstance(skill, str):
        return False
    s = sanitize_profile_text(skill)
    if not s or s.lower() in _PLACEHOLDER_VALUES:
        return False
    if len(s) > 60 or len(s.split()) > 6:
        return False
    if _SENTENCE_SKILL_RE.search(s):
        return False
    if _JOB_TITLE_ENDING_RE.search(s) and len(s.split()) >= 2:
        return False
    if _BRACE_RE.search(skill):
        return False
    return True


def sanitize_skill_list(skills: Optional[List[Any]], max_items: Optional[int] = None) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for item in skills or []:
        raw = item.get("skill") if isinstance(item, dict) else str(item)
        clean = sanitize_profile_text(raw, 80)
        if not is_plausible_skill_name(clean):
            continue
        key = clean.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
        if max_items and len(out) >= max_items:
            break
    return out


def normalize_work_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Clean title/company and fix common parser mis-assignments."""
    if not isinstance(entry, dict):
        return entry
    out = dict(entry)
    title = sanitize_profile_text(str(out.get("title") or ""), 255)
    company = sanitize_profile_text(str(out.get("company") or ""), 255)
    role = sanitize_profile_text(str(out.get("role") or ""), 255)
    if role and not title:
        title = role

    title_is_company = not company and _looks_like_company(title)
    title_is_role = _looks_like_role_title(title)
    company_is_role = company and not _looks_like_company(company) and _looks_like_role_title(company)

    if title and not company and title_is_company and not title_is_role:
        company, title = title, ""
    elif title and company and title_is_company and company_is_role:
        title, company = company, title

    out["title"] = title
    out["company"] = company
    if "role" in out:
        out["role"] = title or role
    return out


def sanitize_work_experience(entries: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        normalized = normalize_work_entry(entry)
        if normalized.get("title") or normalized.get("company"):
            cleaned.append(normalized)
    return cleaned


def is_actionable_responsibility(text: Optional[str]) -> bool:
    """True when a JD line is a verb-led duty, not a title/header blob."""
    clean = sanitize_profile_text(text, 220)
    if not clean or len(clean) < 20:
        return False
    if _HEADER_RESP_RE.match(clean):
        return False
    if _PREFIX_RE.match(clean):
        return False
    if "/" in clean:
        first_segment = clean.split("/", 1)[0].strip()
        if not _ACTION_VERB_RE.search(first_segment):
            return False
    if not _ACTION_VERB_RE.search(clean) and len(clean.split()) <= 5:
        return False
    return True


def sanitize_jd_responsibilities(items: Optional[List[Any]], max_items: int = 6) -> List[str]:
    out: List[str] = []
    for item in items or []:
        clean = sanitize_profile_text(str(item), 220)
        if not is_actionable_responsibility(clean):
            continue
        if clean not in out:
            out.append(clean)
        if len(out) >= max_items:
            break
    return out


def sanitize_jd_analysis(jd: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(jd, dict):
        return {}
    out = dict(jd)
    out["role_title"] = sanitize_profile_text(str(out.get("role_title") or out.get("title") or ""), 200) or "Not specified"
    out["domain"] = sanitize_profile_text(str(out.get("domain") or ""), 100) or out.get("domain") or "other"
    out["required_skills"] = sanitize_skill_list(out.get("required_skills"))
    out["nice_to_have_skills"] = sanitize_skill_list(out.get("nice_to_have_skills"))
    out["key_responsibilities"] = sanitize_jd_responsibilities(out.get("key_responsibilities"))
    return out


def sanitize_parsed_resume_data(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Post-parse cleanup for resume parser output."""
    if not isinstance(data, dict):
        return {}
    out = dict(data)
    out["skills"] = sanitize_skill_list(out.get("skills"))
    out["work_experience"] = sanitize_work_experience(out.get("work_experience"))
    contact = dict(out.get("contact_info") or {})
    if contact.get("name"):
        contact["name"] = sanitize_profile_text(str(contact["name"]), 120)
    out["contact_info"] = contact
    if out.get("professional_summary"):
        out["professional_summary"] = sanitize_profile_text(str(out["professional_summary"]), 2000)
    return out


def sanitize_candidate_profile(profile: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize candidate profile fields used in kits, narratives, and voice."""
    if not isinstance(profile, dict):
        return {}
    out = dict(profile)
    out["name"] = sanitize_profile_text(str(out.get("name") or ""), 120)
    out["current_role"] = sanitize_profile_text(str(out.get("current_role") or ""), 255)
    out["current_company"] = sanitize_profile_text(str(out.get("current_company") or ""), 255)
    out["skills_identified"] = sanitize_skill_list(out.get("skills_identified"))
    out["structured_skills"] = sanitize_skill_list(out.get("structured_skills"))
    out["text_scanned_skills"] = sanitize_skill_list(out.get("text_scanned_skills"))
    out["work_experience"] = sanitize_work_experience(out.get("work_experience"))
    if out.get("career_summary"):
        out["career_summary"] = sanitize_profile_text(str(out["career_summary"]), 400)
    return out
