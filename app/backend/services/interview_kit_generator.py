"""
Recruiter screen playbook generation (v2) with legacy question flattening.

Produces conversation threads anchored on hiring hypotheses — domain-agnostic
templates personalized with skills, gaps, and resume context.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.backend.services.interview_playbook_templates import (
    build_close_script,
    build_open_script,
    detect_role_family,
    ownership_thread_steps,
    risk_gap_thread_steps,
    ways_of_working_step,
    CLOSE_LOGISTICS,
)
from app.backend.services.profile_text_sanitizer import (
    contains_placeholder_text,
    is_actionable_responsibility,
    sanitize_candidate_profile,
    sanitize_jd_responsibilities,
    sanitize_profile_text,
    sanitize_skill_list,
)

MAX_QUESTION_LEN = 200
KIT_VERSION = 2

_DOMAIN_PATTERNS = {}  # kept for tests importing; detect moved to templates module


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


def _role_title_for_entry(entry: Dict[str, Any]) -> str:
    title = _short_label(entry.get("title") or entry.get("role") or "", 5)
    if contains_placeholder_text(title) or title.lower() in {"duration", "n/a", "unknown"}:
        return ""
    return title


def _company_for_entry(entry: Dict[str, Any], profile: Dict[str, Any]) -> str:
    company = _short_label(entry.get("company") or "", 4)
    if company and company not in ("N/A", "Unknown") and not contains_placeholder_text(company):
        return company
    company = (profile.get("current_company") or "").strip()
    if company and company not in ("N/A", "Unknown") and not contains_placeholder_text(company):
        return _short_label(company, 4)
    return ""


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
    follow = follow_ups or []
    normalized_follow = []
    for fu in follow:
        if isinstance(fu, str):
            normalized_follow.append(fu)
    return {
        "text": _clamp_question(text),
        "what_to_listen_for": listen[:4],
        "follow_ups": normalized_follow[:3],
        "scoring_criteria": {
            "strong": strong or "Specific example with personal contribution and outcome",
            "adequate": adequate or "Relevant but light on detail or personal role",
            "weak": weak or "Vague, theoretical, or cannot give a concrete example",
        },
    }


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


_TA_IRRELEVANT_SKILLS = frozenset({
    "machine learning", "deep learning", "kubernetes", "docker", "react", "angular",
    "java", "python", "tensorflow", "pytorch", "aws", "azure", "gcp", "sap",
    "blockchain", "cuda", "spark", "hadoop",
})


def _skill_relevant_to_role(skill: str, role_family: str) -> bool:
    if not _is_probeable_skill(skill):
        return False
    skill_lower = skill.lower().strip()
    if role_family == "talent_acquisition" and skill_lower in _TA_IRRELEVANT_SKILLS:
        return False
    if role_family == "finance" and skill_lower in {"kubernetes", "react", "docker", "tensorflow"}:
        return False
    return True


def _filter_missing_skills(missing: List[str], role_family: str) -> List[str]:
    return [s for s in missing if _skill_relevant_to_role(s, role_family)]


def _normalize_step(raw: Dict[str, Any]) -> Dict[str, Any]:
    follow = raw.get("follow_ups") or []
    if isinstance(follow, list):
        follow = [f for f in follow if isinstance(f, str)]
    else:
        follow = []
    return _question_item(
        raw.get("text", ""),
        listen=list(raw.get("what_to_listen_for") or []),
        follow_ups=follow,
        strong=(raw.get("scoring_criteria") or {}).get("strong", ""),
        adequate=(raw.get("scoring_criteria") or {}).get("adequate", ""),
        weak=(raw.get("scoring_criteria") or {}).get("weak", ""),
    )


def _build_hypotheses(
    *,
    matched: List[str],
    missing: List[str],
    role_title: str,
    role_family: str,
    years: float,
) -> List[Dict[str, Any]]:
    hypotheses: List[Dict[str, Any]] = []
    primary = matched[0] if matched else role_title or "core role requirements"
    hypotheses.append({
        "id": "H1",
        "label": f"Can they own {primary} work end-to-end, not just support?",
        "priority": "must_have",
        "why": "Core role fit",
    })
    if missing:
        hypotheses.append({
            "id": "H2",
            "label": f"Is {missing[0]} a real gap or hidden experience?",
            "priority": "risk",
            "why": "Top missing must-have from match report",
        })
    if years >= 5 or role_family in ("sap", "engineering", "finance"):
        hypotheses.append({
            "id": "H3",
            "label": "Can they operate client/stakeholder-facing under pressure?",
            "priority": "must_have",
            "why": "Seniority and judgment bar",
        })
    if len(matched) > 1:
        hypotheses.append({
            "id": "H4",
            "label": f"Is {matched[1]} depth real, not a resume keyword?",
            "priority": "nice_to_have",
            "why": "Validate secondary strength",
        })
    hypotheses.append({
        "id": "H5",
        "label": "Motivation, availability, and engagement model fit",
        "priority": "gate",
        "why": "Practical proceed/no-hire gate",
    })
    return hypotheses


def _build_briefing(
    profile: Dict[str, Any],
    matched: List[str],
    missing: List[str],
    role_family: str,
    screen_objective: str,
    *,
    hm_topics: Optional[List[Dict[str, str]]] = None,
    deal_breakers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    name = profile.get("name") or "Candidate"
    role = profile.get("current_role") or "professional"
    years = profile.get("total_effective_years") or 0
    strengths = [
        f"Confirm depth on {s} with a concrete example"
        for s in matched[:3]
    ] or ["Open with recent role scope before drilling into skills"]
    probes: List[str] = []
    for topic in (hm_topics or [])[:3]:
        q = (topic.get("question") or "").strip()
        if q:
            probes.append(f"HM focus: {q}")
    for db in (deal_breakers or [])[:2]:
        probes.append(f"Deal-breaker to verify: {db}")
    for s in missing[:3]:
        if len(probes) >= 4:
            break
        probes.append(f"Probe {s} — light on resume; ask for a concrete example")
    if not probes:
        probes = ["Validate core role fit in the ownership thread"]
    notes = [
        "Run threads in order; skip follow-ups when the candidate is already specific.",
        f"Screen objective: {screen_objective}",
    ]
    if role_family == "talent_acquisition":
        notes.append("Prioritize full-cycle examples and HM partnership stories.")
    return {
        "profile_snapshot": f"{name} — {role}, {years} years experience.",
        "strengths_to_confirm": strengths,
        "areas_to_probe": probes,
        "context_notes": notes,
    }


def _playbook_to_legacy(threads: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Flatten threads into legacy category lists for APIs and teleprompter."""
    technical: List[Dict[str, Any]] = []
    behavioral: List[Dict[str, Any]] = []
    experience: List[Dict[str, Any]] = []
    seen: set[str] = set()

    def _add(bucket: List[Dict[str, Any]], item: Dict[str, Any]) -> None:
        key = re.sub(r"\W+", "", item["text"].lower())[:80]
        if key in seen:
            return
        seen.add(key)
        bucket.append(item)

    for thread in threads:
        kind = thread.get("kind", "general")
        steps = thread.get("steps") or []
        for step in steps:
            if kind == "risk":
                _add(technical, step)
            elif kind == "ownership":
                _add(experience, step)
            elif kind == "judgment":
                _add(behavioral, step)
            elif kind == "technical":
                _add(technical, step)
            else:
                _add(experience, step)

    return {
        "technical_questions": technical[:5],
        "behavioral_questions": behavioral[:2],
        "culture_fit_questions": [],
        "experience_deep_dive_questions": experience[:3],
    }


def _hm_focus_thread_steps(topics: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    for topic in topics[:4]:
        q = (topic.get("question") or "").strip()
        if not q:
            continue
        rationale = (topic.get("rationale") or "").strip()
        listen = [rationale] if rationale else ["Specific example with personal contribution"]
        steps.append(_question_item(
            q if q.endswith("?") else f"{q}?",
            listen=listen,
            follow_ups=["What was your personal role in that?", "How recent was that work?"],
        ))
    return steps


def generate_targeted_interview_kit(
    *,
    profile: Optional[Dict[str, Any]] = None,
    jd_analysis: Optional[Dict[str, Any]] = None,
    skill_analysis: Optional[Dict[str, Any]] = None,
    parsed_data: Optional[Dict[str, Any]] = None,
    kit_inputs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a recruiter playbook with conversation threads (v2)."""
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
    role_family = detect_role_family(jd_analysis)
    missing = _filter_missing_skills(missing, role_family)

    role_title = _short_label(jd_analysis.get("role_title") or jd_analysis.get("title") or "", 8)
    role_context = profile.get("current_role") or role_title or "professional"
    years = float(profile.get("total_effective_years") or 0)
    domain_hint = _domain_hint(jd_analysis)
    primary_skill = matched[0] if matched else (required[0] if required else role_title)
    top_entry = work_entries[0] if work_entries else {}
    company = _company_for_entry(top_entry, profile)
    title = _role_title_for_entry(top_entry) or role_context

    ctx = {
        "name": (profile.get("name") or "there").split()[0],
        "role_title": role_title or "this role",
        "role_context": role_context,
        "company": company or "your last employer",
        "title": title or "your role",
        "skill": primary_skill or "this area",
        "context": domain_hint,
        "years": years,
    }

    risk_skill = missing[0] if missing else None
    screen_objective = (
        f"Validate fit for {role_title or 'role'} — confirm ownership on {primary_skill}"
        + (f", de-risk {risk_skill}" if risk_skill else "")
        + ", and decide proceed/hold/no."
    )

    hypotheses = _build_hypotheses(
        matched=matched,
        missing=missing,
        role_title=role_title,
        role_family=role_family,
        years=years,
    )

    kit_inputs = kit_inputs or {}
    hm_topics = kit_inputs.get("hm_screen_topics") or []
    deal_breakers = kit_inputs.get("deal_breakers") or []
    calibrated_must = kit_inputs.get("calibrated_must_haves") or []

    if calibrated_must and not missing:
        req_lower = {s.lower() for s in matched}
        missing = [s for s in calibrated_must if s.lower() not in req_lower][:5]

    threads: List[Dict[str, Any]] = []

    # Thread 0 — HM screen-focus (primary when defined)
    if hm_topics:
        hm_steps = [_normalize_step(s) for s in _hm_focus_thread_steps(hm_topics)]
        if hm_steps:
            threads.append({
                "id": "thread_hm_focus",
                "title": "HM screen focus",
                "kind": "judgment",
                "hypothesis_ids": ["H0"],
                "time_minutes": 8,
                "priority": "must_have",
                "steps": hm_steps,
            })

    # Thread 1 — ownership
    ownership_steps = [_normalize_step(s) for s in ownership_thread_steps(role_family, ctx)]
    threads.append({
        "id": "thread_ownership",
        "title": "Core role ownership",
        "kind": "ownership",
        "hypothesis_ids": ["H1"],
        "time_minutes": 6,
        "priority": "must_have",
        "steps": ownership_steps,
    })

    # Thread 2 — risk gap (if any)
    if risk_skill:
        risk_steps = [_normalize_step(s) for s in risk_gap_thread_steps(role_family, risk_skill, ctx)]
        threads.append({
            "id": "thread_risk",
            "title": f"Risk area — {risk_skill}",
            "kind": "risk",
            "hypothesis_ids": ["H2"],
            "time_minutes": 7,
            "priority": "risk",
            "steps": risk_steps,
        })

    # Thread 3 — judgment / ways of working
    judgment = _normalize_step(ways_of_working_step(role_family, ctx))
    threads.append({
        "id": "thread_judgment",
        "title": "Stakeholder judgment",
        "kind": "judgment",
        "hypothesis_ids": ["H3"],
        "time_minutes": 5,
        "priority": "must_have",
        "steps": [judgment],
    })

    legacy = _playbook_to_legacy(threads)
    briefing = _build_briefing(
        profile, matched, missing, role_family, screen_objective,
        hm_topics=hm_topics, deal_breakers=deal_breakers,
    )

    return {
        "kit_version": KIT_VERSION,
        "screen_objective": screen_objective,
        "candidate_briefing": briefing,
        "hypotheses": hypotheses,
        "open": {
            "script": "",
            "listen_for": [
                "Answers in projects and ownership, not only team names",
                "Asks clarifying questions about the role (senior signal)",
            ],
            "recruiter_owned": True,
        },
        "threads": threads,
        "close": {
            "script": build_close_script(role_family, ctx),
            "logistics": list(CLOSE_LOGISTICS),
        },
        "hm_debrief_template": {
            "fit_summary_prompt": (
                f"Summarize {profile.get('name') or 'candidate'}'s fit for {role_title} — "
                "strengths, gaps, and whether to proceed."
            ),
            "must_haves": [
                {"requirement": primary_skill or "Core role skill", "status": "pending"},
                *([{"requirement": risk_skill, "status": "pending"}] if risk_skill else []),
            ],
            "hm_focus_if_proceed": [
                f"Deep-dive {risk_skill} with a live scenario" if risk_skill else "Validate ownership on latest engagement",
                "Confirm seniority bar with hiring manager",
            ],
            "residual_risks": [f"Unverified: {risk_skill}"] if risk_skill else [],
        },
        "recruiter_signals": {
            "green": "Specific phases, tools, personal deliverables, incident stories",
            "yellow": "Team-level answers with some personal detail",
            "red": "Buzzwords only, no examples, bluffing on gap areas",
            "move_on_when": "Two strong specifics on a thread — advance to next thread",
            "dig_when": "One vague answer — use one targeted follow-up only",
        },
        **legacy,
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
    """Generate additional technical probes for deep interviews."""
    kit = generate_targeted_interview_kit(
        profile=profile,
        jd_analysis=jd_analysis,
        skill_analysis=skill_analysis,
        parsed_data=parsed_data,
    )
    existing = existing_texts or set()
    extras: List[Dict[str, Any]] = []
    for q in kit.get("technical_questions") or []:
        key = re.sub(r"\W+", "", q["text"].lower())[:80]
        if key not in existing and len(extras) < count:
            extras.append(q)
    return extras[:count]


def refresh_interview_questions_in_analysis(
    analysis: Dict[str, Any],
    parsed_data: Optional[Dict[str, Any]] = None,
    *,
    force: bool = False,
    kit_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Regenerate interview kit from stored analysis fields (rescore / report view)."""
    existing = analysis.get("interview_questions")
    status = (kit_status or analysis.get("interview_kit_status") or "").lower()
    if not force and status in ("ready", "fallback") and count_kit_questions(existing) > 0:
        return existing if isinstance(existing, dict) else {}

    profile = analysis.get("candidate_profile") or {}
    if parsed_data:
        if not profile.get("work_experience"):
            profile = {**profile, "work_experience": parsed_data.get("work_experience") or []}
        if not profile.get("name") and parsed_data.get("contact_info"):
            profile = {**profile, "name": parsed_data["contact_info"].get("name")}

    kit_inputs = analysis.get("kit_inputs") or {}
    if not kit_inputs and analysis.get("requisition_id") and analysis.get("tenant_id"):
        try:
            from app.backend.db.database import SessionLocal
            from app.backend.services.interview_kit_context import load_kit_inputs_for_requisition
            db = SessionLocal()
            try:
                kit_inputs = load_kit_inputs_for_requisition(
                    db, analysis["requisition_id"], analysis["tenant_id"],
                )
            finally:
                db.close()
        except Exception:
            kit_inputs = {}

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
        kit_inputs=kit_inputs,
    )
    analysis["interview_questions"] = kit
    return kit


def count_kit_questions(interview_questions: Optional[Dict[str, Any]]) -> int:
    """Count teleprompter steps across playbook threads and legacy categories."""
    if not interview_questions or not isinstance(interview_questions, dict):
        return 0
    total = 0
    threads = interview_questions.get("threads")
    if isinstance(threads, list):
        for thread in threads:
            steps = thread.get("steps") if isinstance(thread, dict) else None
            if isinstance(steps, list):
                total += len(steps)
        if total > 0:
            return total
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


def is_playbook_kit(kit: Optional[Dict[str, Any]]) -> bool:
    return bool(kit and kit.get("kit_version") == KIT_VERSION and kit.get("threads"))


# Backward-compat alias used in tests
_detect_role_family = detect_role_family
