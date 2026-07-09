"""
Deterministic, recruiter-friendly interview kit generation.

Produces 8–10 short, non-overlapping questions focused on must-have skills,
resume-grounded project depth, and gap probing for unlisted skills.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.backend.services.profile_text_sanitizer import (
    is_actionable_responsibility,
    sanitize_candidate_profile,
    sanitize_jd_responsibilities,
    sanitize_profile_text,
    sanitize_skill_list,
)

MAX_QUESTION_LEN = 140


def _clamp_question(text: str, max_len: int = MAX_QUESTION_LEN) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_len:
        return text
    cut = text[: max_len - 1].rsplit(" ", 1)[0]
    return (cut or text[: max_len - 1]).rstrip(",—-") + "?"


def _short_label(text: str, max_words: int = 6) -> str:
    if not text or not isinstance(text, str):
        return ""
    clean = sanitize_profile_text(text)
    words = clean.split()
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return clean.rstrip(".,;:")


def _normalize_skill_list(items: list) -> List[str]:
    return sanitize_skill_list(items)


def _work_entries(profile: Dict[str, Any], parsed_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    entries = profile.get("work_experience") or []
    if not entries and parsed_data:
        entries = parsed_data.get("work_experience") or []
    return [e for e in entries if isinstance(e, dict)]


def _company_for_skill(skill: str, work_entries: List[Dict[str, Any]], profile: Dict[str, Any]) -> Optional[str]:
    skill_lower = skill.lower()
    for entry in work_entries[:4]:
        blob = " ".join(
            str(entry.get(k, "") or "")
            for k in ("company", "title", "description", "highlights", "responsibilities")
        ).lower()
        if skill_lower in blob:
            company = (entry.get("company") or "").strip()
            if company:
                return _short_label(company, 4)
    company = (profile.get("current_company") or "").strip()
    return _short_label(company, 4) if company and company not in ("N/A", "Unknown") else None


def _role_title_for_entry(entry: Dict[str, Any]) -> str:
    return _short_label(entry.get("title") or entry.get("role") or "", 5)


def _domain_hint(jd_analysis: Dict[str, Any]) -> str:
    domain = jd_analysis.get("domain") or jd_analysis.get("role_title") or ""
    short = _short_label(domain, 4)
    return short or "this role"


def _question_item(
    text: str,
    *,
    listen: List[str],
    follow_ups: Optional[List[str]] = None,
    strong: str = "",
    adequate: str = "",
    weak: str = "",
) -> Dict[str, Any]:
    return {
        "text": _clamp_question(text),
        "what_to_listen_for": listen[:3],
        "follow_ups": (follow_ups or [])[:2],
        "scoring_criteria": {
            "strong": strong or "Specific example with personal contribution and outcome",
            "adequate": adequate or "Relevant but light on detail or personal role",
            "weak": weak or "Vague, theoretical, or cannot give a concrete example",
        },
    }


def _gap_probe_question(skill: str, domain_hint: str) -> Dict[str, Any]:
    text = f"{skill} isn't on your resume — have you used it in {domain_hint}?"
    return _question_item(
        text,
        listen=[
            f"Honest exposure to {skill}",
            "Related tools or adjacent experience",
            "Depth beyond buzzwords",
        ],
        follow_ups=[f"What {skill} tasks have you done hands-on?"],
        strong=f"Clear hands-on {skill} example with context and outcome",
        weak=f"Denies {skill} exposure and shows no adjacent experience",
    )


def _validate_skill_question(skill: str, company: Optional[str]) -> Dict[str, Any]:
    if company:
        text = f"At {company}, what did you personally deliver with {skill}?"
    else:
        text = f"You list {skill} — walk me through one real project where you used it."
    return _question_item(
        text,
        listen=[
            f"Hands-on {skill} work",
            "Personal contribution vs team",
            "Outcome or business impact",
        ],
        follow_ups=[f"What was the hardest part of that {skill} work?"],
        strong=f"Detailed {skill} example with clear personal ownership",
        weak=f"Cannot substantiate {skill} beyond surface mention",
    )


def _experience_question(entry: Dict[str, Any], focus_skill: Optional[str] = None) -> Dict[str, Any]:
    company = _short_label(entry.get("company") or "", 4) or "your last role"
    title = _role_title_for_entry(entry) or "your role"
    if focus_skill:
        text = f"At {company} as {title}, how did you apply {focus_skill} day to day?"
    else:
        text = f"At {company} as {title}, what modules or integrations did you own?"
    return _question_item(
        text,
        listen=["Scope owned", "Tools/modules used", "Measurable outcome"],
        follow_ups=["What broke in production and how did you fix it?"],
        strong="Clear ownership, specific modules, and concrete outcome",
        weak="Vague team-level answer without personal contribution",
    )


def _production_issue_question(skill: str) -> Dict[str, Any]:
    text = f"What's the toughest live issue you've fixed involving {skill}?"
    return _question_item(
        text,
        listen=["Root-cause approach", "Steps taken under pressure", "Resolution impact"],
        follow_ups=["What would you do differently next time?"],
        strong="Structured troubleshooting story with clear resolution",
        weak="No real incident example or only theoretical answer",
    )


def _behavioral_for_role(jd_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    resp = sanitize_jd_responsibilities(jd_analysis.get("key_responsibilities") or [])
    short_resp = _short_label(resp[0], 8) if resp else ""
    role = _short_label(jd_analysis.get("role_title") or jd_analysis.get("title") or "", 4)

    questions: List[Dict[str, Any]] = []
    if short_resp and len(short_resp) > 10 and is_actionable_responsibility(short_resp):
        text = f"Tell me about a time you had to {short_resp.lower()} under pressure."
        questions.append(_question_item(
            text,
            listen=["Situation and action", "Trade-offs", "Result"],
            follow_ups=["What was your specific role?"],
        ))
    elif role:
        text = f"Describe a go-live or UAT issue you handled as a {role}."
        questions.append(_question_item(
            text,
            listen=["Problem clarity", "Stakeholder handling", "Resolution"],
            follow_ups=["Who did you coordinate with to fix it?"],
        ))
    else:
        questions.append(_question_item(
            "Describe a deadline slip on a project — what did you do to recover?",
            listen=["Ownership", "Prioritization", "Outcome"],
        ))
    return questions[:1]


def _build_briefing(
    profile: Dict[str, Any],
    matched: List[str],
    missing: List[str],
) -> Dict[str, Any]:
    name = profile.get("name") or "Candidate"
    role = profile.get("current_role") or "professional"
    years = profile.get("total_effective_years") or 0
    return {
        "profile_snapshot": f"{name} — {role}, {years} years experience.",
        "strengths_to_confirm": [f"Confirm {s}" for s in matched[:3]] or ["Review resume strengths"],
        "areas_to_probe": missing[:3] or ["Validate core role fit"],
        "context_notes": [f"Probe unlisted {s}" for s in missing[:2]],
    }


def generate_targeted_interview_kit(
    *,
    profile: Optional[Dict[str, Any]] = None,
    jd_analysis: Optional[Dict[str, Any]] = None,
    skill_analysis: Optional[Dict[str, Any]] = None,
    parsed_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build 8–10 short, skill-targeted interview questions.

    Technical + experience are prioritized; culture fit is omitted.
    """
    profile = sanitize_candidate_profile(profile or {})
    jd_analysis = dict(jd_analysis or {})
    jd_analysis["key_responsibilities"] = sanitize_jd_responsibilities(
        jd_analysis.get("key_responsibilities") or []
    )
    skill_analysis = skill_analysis or {}

    matched = _normalize_skill_list(
        skill_analysis.get("matched_required")
        or skill_analysis.get("matched_skills")
        or []
    )
    missing = _normalize_skill_list(
        skill_analysis.get("missing_required")
        or skill_analysis.get("missing_skills")
        or []
    )
    if not matched and not missing:
        matched = _normalize_skill_list(skill_analysis.get("matched_skills") or [])
        missing = _normalize_skill_list(skill_analysis.get("missing_skills") or [])

    required = _normalize_skill_list(jd_analysis.get("required_skills") or [])
    if not missing and required:
        matched_lower = {s.lower() for s in matched}
        missing = [s for s in required if s.lower() not in matched_lower]

    work_entries = _work_entries(profile, parsed_data)
    domain_hint = _domain_hint(jd_analysis)

    tech_q: List[Dict[str, Any]] = []
    seen_texts: set[str] = set()

    def _add(category: List[Dict[str, Any]], item: Dict[str, Any]) -> None:
        key = re.sub(r"\W+", "", item["text"].lower())[:80]
        if key in seen_texts:
            return
        seen_texts.add(key)
        category.append(item)

    # Gap probes — up to 3 missing must-haves
    for skill in missing[:3]:
        _add(tech_q, _gap_probe_question(skill, domain_hint))

    # Validate matched skills — up to 3, resume-personalized
    for skill in matched[:3]:
        company = _company_for_skill(skill, work_entries, profile)
        _add(tech_q, _validate_skill_question(skill, company))

    # One production-depth question on top matched skill (non-overlapping with validate)
    if matched:
        _add(tech_q, _production_issue_question(matched[0]))

    # Cap technical at 5
    tech_q = tech_q[:5]

    # Experience — 2–3 resume-anchored questions
    exp_q: List[Dict[str, Any]] = []
    primary_skill = matched[0] if matched else (required[0] if required else None)
    for entry in work_entries[:2]:
        _add(exp_q, _experience_question(entry, primary_skill if len(exp_q) == 0 else None))
    if not exp_q and primary_skill:
        _add(exp_q, _question_item(
            f"Which project best shows your {primary_skill} work — what was your role?",
            listen=["Project context", "Personal contribution", "Outcome"],
        ))
    exp_q = exp_q[:3]

    behavioral_q = _behavioral_for_role(jd_analysis)

    return {
        "candidate_briefing": _build_briefing(profile, matched, missing),
        "technical_questions": tech_q,
        "behavioral_questions": behavioral_q,
        "culture_fit_questions": [],
        "experience_deep_dive_questions": exp_q,
    }


def refresh_interview_questions_in_analysis(
    analysis: Dict[str, Any],
    parsed_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Regenerate interview kit from stored analysis fields (rescore / report view)."""
    profile = analysis.get("candidate_profile") or {}
    if parsed_data:
        if not profile.get("work_experience"):
            profile = {**profile, "work_experience": parsed_data.get("work_experience") or []}
        if not profile.get("name") and parsed_data.get("contact_info"):
            profile = {**profile, "name": parsed_data["contact_info"].get("name")}

    kit = generate_targeted_interview_kit(
        profile=profile,
        jd_analysis=analysis.get("jd_analysis") or {},
        skill_analysis=analysis.get("skill_analysis") or {
            "matched_skills": analysis.get("matched_skills") or [],
            "missing_skills": analysis.get("missing_skills") or [],
            "matched_required": analysis.get("matched_skills") or [],
            "missing_required": analysis.get("missing_skills") or [],
        },
        parsed_data=parsed_data,
    )
    analysis["interview_questions"] = kit
    return kit
