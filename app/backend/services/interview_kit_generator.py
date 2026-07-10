"""
Deterministic, recruiter-friendly interview kit generation.

Produces 8–10 short, non-overlapping questions focused on must-have skills,
resume-grounded project depth, and gap probing for unlisted skills.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.backend.services.profile_text_sanitizer import (
    contains_placeholder_text,
    is_actionable_responsibility,
    sanitize_candidate_profile,
    sanitize_jd_responsibilities,
    sanitize_profile_text,
    sanitize_skill_list,
)

MAX_QUESTION_LEN = 160

_DOMAIN_PATTERNS: Dict[str, re.Pattern] = {
    "talent_acquisition": re.compile(
        r"talent acquisition|recruiter|recruiting|human resources|\bhr\b|hiring|onboarding|staffing",
        re.IGNORECASE,
    ),
    "sap": re.compile(r"\bsap\b|erp|s/?4\s*hana|\bmm\b|fico|idoc", re.IGNORECASE),
    "finance": re.compile(r"finance|financial analyst|accounting|fp&a|treasury", re.IGNORECASE),
    "engineering": re.compile(
        r"engineer|developer|software|backend|frontend|devops|data scien|architect",
        re.IGNORECASE,
    ),
}

_TA_IRRELEVANT_SKILLS = frozenset({
    "machine learning", "deep learning", "kubernetes", "docker", "react", "angular",
    "java", "python", "tensorflow", "pytorch", "aws", "azure", "gcp", "sap",
    "blockchain", "cuda", "spark", "hadoop",
})

_GAP_PROBE_TEMPLATES = (
    "The role calls for {skill} — how have you used that in {context}?",
    "I don't see much {skill} on your resume — any hands-on exposure?",
    "Walk me through your experience with {skill}, even from adjacent work.",
)


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


def _detect_role_family(jd_analysis: Dict[str, Any]) -> str:
    blob = " ".join(
        str(jd_analysis.get(key) or "")
        for key in ("role_title", "title", "domain")
    )
    for family, pattern in _DOMAIN_PATTERNS.items():
        if pattern.search(blob):
            return family
    return "general"


def _is_probeable_skill(skill: str) -> bool:
    clean = sanitize_profile_text(skill, 80)
    if not clean or len(clean) < 2:
        return False
    if contains_placeholder_text(clean):
        return False
    if len(clean.split()) > 5:
        return False
    if re.search(r"\b\d{1,2}\s*[-–—]\s*\d{1,2}\s+years?\b", clean, re.I):
        return False
    if re.search(r"\byears?\s+of\s+experience\b|\bexperience\s+in\b", clean, re.I):
        return False
    return True


def _skill_relevant_to_role(skill: str, jd_analysis: Dict[str, Any], role_family: str) -> bool:
    if not _is_probeable_skill(skill):
        return False
    skill_lower = skill.lower().strip()
    if role_family == "talent_acquisition" and skill_lower in _TA_IRRELEVANT_SKILLS:
        return False
    if role_family == "finance" and skill_lower in {"kubernetes", "react", "docker", "tensorflow"}:
        return False
    return True


def _filter_missing_skills(
    missing: List[str],
    jd_analysis: Dict[str, Any],
    role_family: str,
) -> List[str]:
    filtered: List[str] = []
    for skill in missing:
        if _skill_relevant_to_role(skill, jd_analysis, role_family):
            filtered.append(skill)
    return filtered


def _gap_probe_question(skill: str, context: str, variant: int = 0) -> Dict[str, Any]:
    template = _GAP_PROBE_TEMPLATES[variant % len(_GAP_PROBE_TEMPLATES)]
    text = template.format(skill=skill, context=context or "this role")
    return _question_item(
        text,
        listen=[
            f"Practical {skill} examples",
            "Related tools or transferable experience",
            "Honest depth beyond buzzwords",
        ],
        follow_ups=[f"Pick one example — what did you personally do with {skill}?"],
        strong=f"Clear hands-on {skill} example with context and outcome",
        weak=f"No exposure to {skill} and no credible adjacent experience",
    )


def _validate_skill_question(skill: str, company: Optional[str]) -> Dict[str, Any]:
    if company:
        text = f"At {company}, what did you personally own involving {skill}?"
    else:
        text = f"You mention {skill} — walk me through one project and your contribution."
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


def _experience_question(
    entry: Dict[str, Any],
    focus_skill: Optional[str] = None,
    role_family: str = "general",
) -> Dict[str, Any]:
    company = _short_label(entry.get("company") or "", 4) or "your last role"
    title = _role_title_for_entry(entry) or "your role"
    if role_family == "talent_acquisition":
        if focus_skill:
            text = f"At {company}, how did you use {focus_skill} across sourcing, screening, and offer?"
        else:
            text = f"At {company} as {title}, walk me through a tough hire from intake to close."
    elif role_family == "sap":
        if focus_skill:
            text = f"At {company}, what {focus_skill} work did you own — modules, config, or support?"
        else:
            text = f"At {company} as {title}, what SAP modules or integrations did you own?"
    elif role_family == "finance":
        if focus_skill:
            text = f"At {company}, how did you apply {focus_skill} in reporting or analysis day to day?"
        else:
            text = f"At {company} as {title}, what analyses or models did you own end to end?"
    elif focus_skill:
        text = f"At {company} as {title}, how did you apply {focus_skill} day to day?"
    else:
        text = f"At {company} as {title}, what was your core scope and biggest deliverable?"
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


def _behavioral_for_role(jd_analysis: Dict[str, Any], role_family: str = "general") -> List[Dict[str, Any]]:
    resp = sanitize_jd_responsibilities(jd_analysis.get("key_responsibilities") or [])
    role = _short_label(jd_analysis.get("role_title") or jd_analysis.get("title") or "", 4)

    for responsibility in resp[:3]:
        short_resp = _short_label(responsibility, 10)
        if short_resp and len(short_resp) > 10 and is_actionable_responsibility(short_resp):
            text = f"Tell me about a time you had to {short_resp.lower()} — what was at stake?"
            return [_question_item(
                text,
                listen=["Situation and action", "Trade-offs", "Result"],
                follow_ups=["What was your specific role versus the team's?"],
            )]

    if role_family == "talent_acquisition":
        text = "Tell me about a hiring manager who kept moving the goalposts — how did you handle it?"
    elif role_family == "sap":
        text = f"Describe a go-live or production issue you handled as a {role or 'consultant'}."
    elif role_family == "finance":
        text = "Tell me about a deadline-driven analysis where the data didn't cooperate — what did you do?"
    elif role:
        text = f"Describe a high-pressure situation in your {role} work — how did you prioritize?"
    else:
        text = "Describe a deadline slip on a project — what did you do to recover?"

    return [_question_item(
        text,
        listen=["Ownership", "Stakeholder handling", "Outcome"],
        follow_ups=["What would you do differently next time?"],
    )]


def _build_briefing(
    profile: Dict[str, Any],
    matched: List[str],
    missing: List[str],
    role_family: str = "general",
) -> Dict[str, Any]:
    name = profile.get("name") or "Candidate"
    role = profile.get("current_role") or "professional"
    years = profile.get("total_effective_years") or 0
    strengths = [
        f"Resume shows {s} — ask for a concrete example"
        for s in matched[:3]
    ] or ["Review strongest resume signals before the call"]
    probes = [
        f"JD needs {s} — light on resume, worth a direct question"
        for s in missing[:3]
    ] or ["Validate core role fit with one opening scope question"]
    notes = []
    if missing[:2]:
        notes.append(f"Probe gaps: {', '.join(missing[:2])}")
    if role_family == "talent_acquisition":
        notes.append("Focus on full-cycle hiring, stakeholder management, and offer closing.")
    return {
        "profile_snapshot": f"{name} — {role}, {years} years experience.",
        "strengths_to_confirm": strengths,
        "areas_to_probe": probes,
        "context_notes": notes or ["Keep the screen to 20–25 minutes; prioritize must-have gaps first."],
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
    role_family = _detect_role_family(jd_analysis)
    missing = _filter_missing_skills(missing, jd_analysis, role_family)

    tech_q: List[Dict[str, Any]] = []
    seen_texts: set[str] = set()

    def _add(category: List[Dict[str, Any]], item: Dict[str, Any]) -> None:
        key = re.sub(r"\W+", "", item["text"].lower())[:80]
        if key in seen_texts:
            return
        seen_texts.add(key)
        category.append(item)

    # Gap probes — up to 3 missing must-haves (varied phrasing)
    for idx, skill in enumerate(missing[:3]):
        _add(tech_q, _gap_probe_question(skill, domain_hint, variant=idx))

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
        _add(
            exp_q,
            _experience_question(
                entry,
                primary_skill if len(exp_q) == 0 else None,
                role_family=role_family,
            ),
        )
    if not exp_q and primary_skill:
        _add(exp_q, _question_item(
            f"Which project best shows your {primary_skill} work — what was your role?",
            listen=["Project context", "Personal contribution", "Outcome"],
        ))
    exp_q = exp_q[:3]

    behavioral_q = _behavioral_for_role(jd_analysis, role_family=role_family)

    return {
        "candidate_briefing": _build_briefing(profile, matched, missing, role_family=role_family),
        "technical_questions": tech_q,
        "behavioral_questions": behavioral_q,
        "culture_fit_questions": [],
        "experience_deep_dive_questions": exp_q,
    }


def generate_deep_technical_extras(
    *,
    profile: Optional[Dict[str, Any]] = None,
    jd_analysis: Optional[Dict[str, Any]] = None,
    skill_analysis: Optional[Dict[str, Any]] = None,
    parsed_data: Optional[Dict[str, Any]] = None,
    count: int = 3,
    existing_texts: Optional[set[str]] = None,
) -> List[Dict[str, Any]]:
    """Generate 2–4 additional technical probes for deep interviews."""
    profile = sanitize_candidate_profile(profile or {})
    skill_analysis = skill_analysis or {}
    existing = existing_texts or set()

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
    work_entries = _work_entries(profile, parsed_data)
    domain_hint = _domain_hint(jd_analysis or {})

    extras: List[Dict[str, Any]] = []
    seen = set(existing)

    def _add(item: Dict[str, Any]) -> None:
        key = re.sub(r"\W+", "", item["text"].lower())[:80]
        if key in seen or len(extras) >= count:
            return
        seen.add(key)
        extras.append(item)

    # Deeper probes on missing skills beyond the standard kit
    for skill in missing[3:6]:
        _add(_question_item(
            f"Walk me through a hands-on scenario where you applied {skill} under pressure.",
            listen=[f"Real {skill} usage", "Problem-solving steps", "Measurable outcome"],
            follow_ups=[f"What would you do differently next time with {skill}?"],
            strong=f"Detailed scenario with trade-offs and outcome",
            weak="Cannot describe practical {skill} usage",
        ))

    # Architecture / depth on matched skills
    for skill in matched[3:6]:
        company = _company_for_skill(skill, work_entries, profile)
        if company:
            text = f"At {company}, how did you design or scale the {skill} solution?"
        else:
            text = f"How would you architect a production system using {skill} for {domain_hint}?"
        _add(_question_item(
            text,
            listen=["Design decisions", "Trade-offs", "Scale or reliability"],
            follow_ups=[f"What failure modes did you plan for with {skill}?"],
            strong="Clear architecture with constraints and outcomes",
            weak="Only surface-level or theoretical answer",
        ))

    if len(extras) < 2 and matched:
        _add(_production_issue_question(matched[0]))

    return extras[:count]


def refresh_interview_questions_in_analysis(
    analysis: Dict[str, Any],
    parsed_data: Optional[Dict[str, Any]] = None,
    *,
    force: bool = False,
    kit_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Regenerate interview kit from stored analysis fields (rescore / report view).

    Preserves LLM-enriched kits when ``kit_status`` is ``ready`` unless ``force`` is True.
    """
    existing = analysis.get("interview_questions")
    status = (kit_status or analysis.get("interview_kit_status") or "").lower()
    if not force and status == "ready" and count_kit_questions(existing) > 0:
        return existing if isinstance(existing, dict) else {}

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


def count_kit_questions(interview_questions: Optional[Dict[str, Any]]) -> int:
    """Count total questions across standard kit categories."""
    if not interview_questions or not isinstance(interview_questions, dict):
        return 0
    total = 0
    for key in (
        "technical_questions",
        "behavioral_questions",
        "culture_fit_questions",
        "experience_deep_dive_questions",
    ):
        items = interview_questions.get(key)
        if isinstance(items, list):
            total += len(items)
    return total
