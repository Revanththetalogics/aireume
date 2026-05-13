"""
Hybrid Analysis Pipeline — Python-first, single LLM call for narrative.

Architecture:
  Phase 1 (Python, ~1-2s): parse_jd_rules → parse_resume_rules → match_skills
                            → score_education/experience/domain → compute_fit_score
  Phase 2 (LLM, ~40s):     explain_with_llm (generates strengths, weaknesses,
                            rationale, interview questions)
  Fallback:                 if LLM times out, _build_fallback_narrative returns
                            deterministic text — result is ALWAYS returned.

Background Processing:
  The LLM narrative is generated as a background task and written to DB when complete.
  The immediate response includes Python scores with narrative_pending=True.
  Frontend polls GET /api/analysis/{id}/narrative to fetch the LLM narrative later.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from typing import AsyncGenerator, Dict, Any, List, Optional, Callable

from app.backend.services.metrics import LLM_CALL_DURATION, LLM_FALLBACK_TOTAL
from app.backend.services.llm_service import get_ollama_semaphore
from app.backend.services.constants import (
    RECOMMENDATION_THRESHOLDS,
    SENIORITY_RANGES,
    DOMAIN_KEYWORDS,
    DEGREE_SCORES,
    FIELD_RELEVANCE,
)
from app.backend.services.domain_service import detect_domain_from_jd, detect_domain_from_resume
from app.backend.services.eligibility_service import check_eligibility
from app.backend.services.fit_scorer import compute_fit_score, compute_deterministic_score, explain_decision
from app.backend.services.weight_mapper import convert_to_new_schema
from app.backend.services.skill_matcher import (
    skills_registry,
    _extract_skills_from_text,
    match_skills,
    match_skills_with_onet,
)

log = logging.getLogger("aria.hybrid")

# Track background tasks for graceful shutdown
_background_tasks: set = set()


def _compute_domain_similarity(jd_domain: dict, candidate_domain: dict) -> float:
    """Compute cosine similarity between JD and candidate domain score vectors.

    Falls back to binary name comparison when score vectors are unavailable.
    """
    jd_scores = jd_domain.get("scores", {})
    cand_scores = candidate_domain.get("scores", {})

    if not jd_scores or not cand_scores:
        # Fallback to binary if scores not available
        if jd_domain.get("domain", "unknown") == candidate_domain.get("domain", "unknown"):
            return jd_domain.get("confidence", 0)
        return 0.0

    # Get union of all domains
    all_domains = set(jd_scores.keys()) | set(cand_scores.keys())

    # Compute cosine similarity
    dot_product = sum(jd_scores.get(d, 0) * cand_scores.get(d, 0) for d in all_domains)
    jd_magnitude = sum(v ** 2 for v in jd_scores.values()) ** 0.5
    cand_magnitude = sum(v ** 2 for v in cand_scores.values()) ** 0.5

    if jd_magnitude == 0 or cand_magnitude == 0:
        return 0.0

    return round(dot_product / (jd_magnitude * cand_magnitude), 3)



def register_background_task(task: asyncio.Task) -> None:
    """Register a background task for tracking."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def shutdown_background_tasks(timeout: float = 5.0) -> None:
    """Cancel and await all background tasks. Call during app shutdown."""
    for task in list(_background_tasks):
        task.cancel()
    if _background_tasks:
        await asyncio.gather(*list(_background_tasks), return_exceptions=True)

# --- Prompt injection sanitization ---
_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"assistant\s*:", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"\[/INST\]", re.IGNORECASE),
]

_MAX_RESUME_LENGTH = 50_000   # ~50KB
_MAX_JD_LENGTH = 20_000       # ~20KB


def _sanitize_input(text: str, max_length: int, label: str = "content") -> str:
    """Sanitize user-provided text to prevent prompt injection."""
    if not text:
        return text
    # Truncate excessively long inputs
    if len(text) > max_length:
        text = text[:max_length]
    # Strip known injection patterns
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[FILTERED]", text)
    return text


def _wrap_user_content(resume_text: str, jd_text: str) -> tuple[str, str]:
    """Sanitize and wrap user content with clear delimiters."""
    resume_text = _sanitize_input(resume_text, _MAX_RESUME_LENGTH, "resume")
    jd_text = _sanitize_input(jd_text, _MAX_JD_LENGTH, "job_description")
    return resume_text, jd_text

# ─── LLM singleton ───────────────────────────────────────────────────────────
_REASONING_LLM = None


def reset_llm_singleton():
    """Force the LLM singleton to reinitialise on next call (e.g. after env change)."""
    global _REASONING_LLM
    _REASONING_LLM = None


def _is_ollama_cloud(base_url: str) -> bool:
    """Check if the base URL points to Ollama Cloud (ollama.com)."""
    return "ollama.com" in base_url.lower()


def _get_llm():
    global _REASONING_LLM
    if _REASONING_LLM is None:
        try:
            from langchain_ollama import ChatOllama
            _base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            _llm_timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "500"))
            _is_cloud = _is_ollama_cloud(_base_url)
            
            # Optional: Enforce cloud-only mode (uncomment to enable)
            # REQUIRE_CLOUD = os.getenv("OLLAMA_REQUIRE_CLOUD", "false").lower() == "true"
            # if REQUIRE_CLOUD and not _is_cloud:
            #     raise RuntimeError(f"OLLAMA_REQUIRE_CLOUD is set but OLLAMA_BASE_URL points to local instance: {_base_url}")

            # num_predict: Cloud models need significantly more tokens for verbose output
            # Local: 6000 tokens for 15 structured interview questions with candidate briefing
            # Cloud: 8000 tokens for very large models (480B+) that generate extremely verbose output
            _num_predict = 8000 if _is_cloud else 6000

            # Build kwargs for ChatOllama
            # NOTE: "format": "json" is intentionally omitted. Ollama's constrained JSON
            # decoding mode aborts generation on any non-JSON token, causing empty/partial
            # responses. We rely on prompt instructions + robust _parse_llm_json_response()
            # for JSON extraction instead.
            _llm_kwargs = {
                "model": os.getenv("OLLAMA_MODEL") or "gemma4:31b-cloud",
                "base_url": _base_url,
                "temperature": 0.1,
                "num_predict": _num_predict,
                # num_ctx: Cloud models need larger context for complex reasoning
                # 16384 for cloud to handle very large outputs, 8192 for local (15 structured questions)
                "num_ctx": 16384 if _is_cloud else 8192,
                # HTTP timeout must exceed LLM_NARRATIVE_TIMEOUT to let the
                # outer asyncio.wait_for control cancellation, not httpx.
                "request_timeout": _llm_timeout + 30,
            }

            # Add headers for Ollama Cloud authentication
            if _is_cloud:
                api_key = os.getenv("OLLAMA_API_KEY", "").strip()
                if api_key:
                    _llm_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
                    log.info("Using Ollama Cloud with API key authentication (num_predict=%s, num_ctx=%s)", _num_predict, _llm_kwargs["num_ctx"])
                else:
                    log.warning("Ollama Cloud detected but OLLAMA_API_KEY is not set!")
            else:
                # Keep model always hot in RAM (-1 = never unload) — only for local Ollama
                _llm_kwargs["keep_alive"] = -1

            log.info("Initializing LLM with config: num_predict=%s, num_ctx=%s, is_cloud=%s", _num_predict, _llm_kwargs["num_ctx"], _is_cloud)
            _REASONING_LLM = ChatOllama(**_llm_kwargs)
        except Exception as e:
            log.warning("LLM init failed: %s", e)
    return _REASONING_LLM


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 1: JD PARSER
# ═══════════════════════════════════════════════════════════════════════════════

YEARS_PATTERNS = [
    r'(\d+)\+\s*years?',
    r'minimum\s+(?:of\s+)?(\d+)\s*years?',
    r'at\s+least\s+(\d+)\s*years?',
    r'(\d+)\s*[-–]\s*\d+\s*years?',
    r'(\d+)\s+to\s+\d+\s*years?',
    r'(\d+)\s*years?\s+(?:of\s+)?experience',
    r'experience\s+(?:of\s+)?(\d+)\s*years?',
]

_NICE_TO_HAVE_RE = re.compile(
    r'(?:nice[\s\-]to[\s\-]have|preferred|bonus|plus|advantageous|desirable|'
    r'would be (?:a\s+)?(?:great|nice)|not required|optional|good to have)',
    re.IGNORECASE,
)

_TITLE_RE = re.compile(
    r'\b(?:senior|sr\.?|junior|jr\.?|lead|principal|staff|associate|mid[-\s]?level|'
    r'entry[\s\-]level)?\s*[\w/\.]+\s+'
    r'(?:engineer|developer|architect|analyst|scientist|manager|consultant|specialist|'
    r'designer|lead|director|officer|head|vp|president|intern|associate|researcher)',
    re.IGNORECASE,
)


def parse_jd_rules(jd_text: str) -> Dict[str, Any]:
    """Parse a job description purely with Python rules. Returns structured dict."""
    text_lower = jd_text.lower()

    # ── Role title ──────────────────────────────────────────────────────────
    role_title = ""
    lines = [l.strip() for l in jd_text.split("\n") if l.strip()]
    for line in lines[:8]:
        if re.search(r'[@|:/\(\)#\d]{2,}', line):
            continue
        if len(line.split()) > 10:
            continue
        if re.search(r'\b(?:engineer|developer|analyst|architect|manager|scientist|'
                     r'designer|consultant|specialist|lead|officer|director)\b', line, re.I):
            role_title = line.strip()
            break
    if not role_title:
        m = _TITLE_RE.search(jd_text[:500])
        if m:
            role_title = m.group(0).strip()

    # ── Years required ───────────────────────────────────────────────────────
    required_years = 0
    for pat in YEARS_PATTERNS:
        m = re.search(pat, text_lower)
        if m:
            try:
                required_years = int(m.group(1))
                break
            except (ValueError, IndexError):
                pass

    # ── Domain classification ────────────────────────────────────────────────
    domain_hits: Dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits:
            domain_hits[domain] = hits
    domain = max(domain_hits, key=domain_hits.get) if domain_hits else "other"

    # ── Seniority ────────────────────────────────────────────────────────────
    title_lower = role_title.lower()
    if any(w in title_lower for w in ("principal", "staff", "distinguished", "fellow")):
        seniority = "lead"
    elif any(w in title_lower for w in ("senior", "sr.", "sr ", "lead", "architect", "head of")):
        seniority = "senior"
    elif any(w in title_lower for w in ("junior", "jr.", "jr ", "associate", "graduate", "entry")):
        seniority = "junior"
    elif any(w in jd_text[:500].lower() for w in ("lead ", "staff ", "principal ")):
        seniority = "lead"
    elif required_years >= 8:
        seniority = "lead"
    elif required_years >= 5:
        seniority = "senior"
    elif required_years >= 2:
        seniority = "mid"
    elif required_years > 0:
        seniority = "junior"
    else:
        seniority = "mid"

    # ── Skill extraction (required vs nice-to-have split) ───────────────────
    nice_start = len(jd_text)
    m_nice = _NICE_TO_HAVE_RE.search(jd_text)
    if m_nice:
        nice_start = m_nice.start()

    required_text   = jd_text[:nice_start]
    nice_have_text  = jd_text[nice_start:]

    required_skills  = _extract_skills_from_text(required_text)
    nice_have_skills = _extract_skills_from_text(nice_have_text)
    # Remove overlap
    nice_have_skills = [s for s in nice_have_skills if s not in required_skills]

    # ── Key responsibilities (first 5 bullet lines starting with verbs) ─────
    resp_lines = []
    for line in lines:
        line_s = line.lstrip("-•*·▸▹►→ ").strip()
        if len(line_s) > 30 and re.match(r'^[A-Z][a-z]', line_s):
            resp_lines.append(line_s)
        if len(resp_lines) >= 6:
            break

    return {
        "role_title":        role_title or "Not specified",
        "domain":            domain,
        "seniority":         seniority,
        "required_skills":   required_skills,
        "required_years":    required_years,
        "nice_to_have_skills": nice_have_skills,
        "key_responsibilities": resp_lines,
    }


def _infer_total_years_from_resume_text(text: str) -> float:
    """
    When structured work_experience is empty or dates failed, recover years from prose
    (e.g. '8+ years of experience', 'over 5 years in embedded systems').
    """
    if not text:
        return 0.0
    snippet = text[:25000]
    best = 0.0
    patterns = [
        r"(?:over|more\s+than|at\s+least|>\s*|approximately|approx\.?)\s*(\d{1,2})\+?\s*(?:years?|yrs?\.?)",
        r"(\d{1,2})\+?\s*(?:years?|yrs?\.?)\s+(?:of\s+)?(?:professional\s+)?(?:relevant\s+)?(?:experience|exp\.?)\b",
        r"(?:experience|exp\.?)\s*[:\-–—]?\s*(?:of\s+)?(?:about|approx\.?)?\s*(\d{1,2})\+?\s*(?:years?|yrs?\.?)",
        r"\b(\d{1,2})\s*\+\s*years?\b",
        r"\b(\d{1,2})\s*-\s*years?\s+(?:of\s+)?experience\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, snippet, re.IGNORECASE):
            try:
                v = float(m.group(1))
                if 0.5 <= v <= 45:
                    best = max(best, v)
            except (ValueError, IndexError):
                pass
    return min(45.0, best)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 2: RESUME PROFILE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_resume_rules(parsed_data: Dict[str, Any], gap_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Build a structured candidate profile from parser output and gap analysis."""
    contact      = parsed_data.get("contact_info", {}) or {}
    work_exp     = parsed_data.get("work_experience", [])
    raw_text     = parsed_data.get("raw_text", "")

    # Skills — tiered confidence model
    parser_skills = [str(s).strip() for s in parsed_data.get("skills", []) if s]
    scanned_skills = _extract_skills_from_text(raw_text)

    # Tier 0: Structured parser output (HIGH confidence)
    structured = list(dict.fromkeys(parser_skills))

    # Tier 2: Text-scanned only (LOW confidence) -- exclude anything already in Tier 0
    structured_norm = {s.lower().strip() for s in structured}
    text_only = [s for s in scanned_skills if s.lower().strip() not in structured_norm]

    # skills_identified = ONLY structured by default
    # text_scanned_skills = tracked separately, validated during matching

    total_years = float(gap_analysis.get("total_years", 0.0) or 0.0)
    if total_years <= 0 and raw_text:
        inferred_y = _infer_total_years_from_resume_text(raw_text)
        if inferred_y > 0:
            total_years = inferred_y

    # Truncate current_role and current_company to 255 chars to prevent DB truncation errors
    _raw_role = work_exp[0].get("title", "") if work_exp else ""
    _raw_company = work_exp[0].get("company", "") if work_exp else ""
    if _raw_role and len(_raw_role) > 255:
        log.warning("Truncating current_role from %d to 255 chars", len(_raw_role))
        _raw_role = _raw_role[:255]
    if _raw_company and len(_raw_company) > 255:
        log.warning("Truncating current_company from %d to 255 chars", len(_raw_company))
        _raw_company = _raw_company[:255]
    current_role    = _raw_role
    current_company = _raw_company

    career_summary = _build_career_summary(current_role, current_company, total_years)

    return {
        "name":                  contact.get("name", ""),
        "email":                 contact.get("email", ""),
        "phone":                 contact.get("phone", ""),
        "structured_skills":     structured,       # Tier 0: parser output (HIGH confidence)
        "text_scanned_skills":   text_only,         # Tier 2: text-only (LOW confidence)
        "skills_identified":     structured,        # ONLY structured — key change
        "education":             parsed_data.get("education", []),
        "work_experience":       work_exp,
        "career_summary":        career_summary,
        "total_effective_years": total_years,
        "current_role":          current_role,
        "current_company":       current_company,
    }


def _build_career_summary(role: str, company: str, years: float) -> str:
    parts = []
    if role and company:
        parts.append(f"{role} at {company}")
    elif role:
        parts.append(role)
    if years:
        parts.append(f"{years} year{'s' if years != 1 else ''} total experience")
    return " — ".join(parts) if parts else "No career summary available"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 4: EDUCATION SCORING
# ═══════════════════════════════════════════════════════════════════════════════

# DEGREE_SCORES and FIELD_RELEVANCE are now imported from constants.py


def score_education_rules(candidate_profile: Dict[str, Any], jd_domain: str) -> int:
    """Return a 0-100 education score."""
    education = candidate_profile.get("education", [])
    if not education:
        return 60  # neutral default — no penalty for missing education data

    best_score = 0
    best_field = ""

    for edu in education:
        degree = str(edu.get("degree", "")).lower()
        field  = str(edu.get("field", "") or edu.get("degree", "")).lower()

        for key, pts in DEGREE_SCORES.items():
            if key in degree:
                if pts > best_score:
                    best_score = pts
                    best_field = field
                break

    if best_score == 0:
        return 60

    # Field relevance multiplier
    relevant_fields = FIELD_RELEVANCE.get(jd_domain, FIELD_RELEVANCE["other"])
    multiplier = 0.70
    for rf in relevant_fields:
        if rf in best_field:
            multiplier = 1.0
            break
        if any(word in best_field for word in rf.split()):
            multiplier = max(multiplier, 0.85)

    return round(best_score * multiplier)


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 5: EXPERIENCE & TIMELINE SCORING
# ═══════════════════════════════════════════════════════════════════════════════

def score_experience_rules(
    candidate_profile: Dict[str, Any],
    jd_analysis: Dict[str, Any],
    gap_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """Return experience_score, timeline_score, and a text timeline summary."""
    actual_years   = candidate_profile.get("total_effective_years", 0.0)
    required_years = jd_analysis.get("required_years", 0)

    # ── Fallback: if dates couldn't be parsed but work entries exist, estimate ─
    # Avoids showing 0% experience when the resume has jobs but ambiguous dates.
    if actual_years == 0.0:
        work_exp = candidate_profile.get("work_experience", [])
        if work_exp:
            # Conservative: 1.5 years per listed job role, capped at 15 years
            actual_years = float(min(15, len(work_exp) * 1.5))

    # ── Experience score ──────────────────────────────────────────────────────
    if required_years == 0:
        exp_score = min(100, int(actual_years * 10))
    elif actual_years >= required_years:
        exp_score = min(100, 70 + int((actual_years - required_years) * 5))
    else:
        exp_score = int((actual_years / required_years) * 70)
    exp_score = max(0, exp_score)

    # ── Timeline score (gap deductions) ──────────────────────────────────────
    t_score = 85
    employment_gaps = gap_analysis.get("employment_gaps", [])
    for gap in employment_gaps:
        severity = gap.get("severity", "negligible")
        if severity == "minor":     t_score -= 5
        elif severity == "moderate": t_score -= 12
        elif severity == "critical": t_score -= 22
    for _ in gap_analysis.get("short_stints", []):    t_score -= 5
    for _ in gap_analysis.get("overlapping_jobs", []): t_score -= 8
    t_score = max(10, min(100, t_score))

    # ── Timeline summary text ─────────────────────────────────────────────────
    if not employment_gaps:
        timeline_text = "Continuous employment — no significant gaps."
    else:
        n = len(employment_gaps)
        longest = max(g.get("duration_months", 0) for g in employment_gaps)
        severities = [g.get("severity", "") for g in employment_gaps]
        worst = (
            "critical" if "critical" in severities else
            "moderate" if "moderate" in severities else
            "minor"
        )
        timeline_text = (
            f"Career includes {n} gap{'s' if n > 1 else ''}: "
            f"{longest} month{'s' if longest > 1 else ''} longest. {worst.capitalize()} pattern."
        )

    return {
        "exp_score":       exp_score,
        "timeline_score":  t_score,
        "timeline_text":   timeline_text,
        "actual_years":    actual_years,
        "required_years":  required_years,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 6: DOMAIN & ARCHITECTURE SCORING
# ═══════════════════════════════════════════════════════════════════════════════

ARCHITECTURE_SIGNALS = [
    "designed", "architected", "led design", "technical lead", "system design",
    "microservices", "distributed system", "scalable", "high availability",
    "event-driven", "message queue", "kafka", "rabbitmq", "tech lead",
    "principal engineer", "staff engineer", "engineering manager", "mentored",
    "technical decision", "proof of concept", "rfc", "adr", "design review",
    "led team", "drove", "established", "built from scratch", "greenfield",
]


def domain_architecture_rules(
    raw_text: str,
    jd_domain: str,
    current_role: Optional[str],
) -> Dict[str, Any]:
    """Return domain_score and architecture_score."""
    text_lower = raw_text.lower()

    # ── Domain fit score ──────────────────────────────────────────────────────
    domain_keywords = DOMAIN_KEYWORDS.get(jd_domain, [])
    hits = sum(1 for kw in domain_keywords if kw in text_lower)

    if   hits >= 8: domain_score = 90
    elif hits >= 5: domain_score = 75
    elif hits >= 3: domain_score = 60
    elif hits >= 1: domain_score = 45
    else:           domain_score = 30

    # Bonus/penalty from current role title
    if current_role:
        role_lower = current_role.lower()
        if any(kw in role_lower for kw in domain_keywords[:5]):
            domain_score = min(100, domain_score + 10)
        elif not any(w in role_lower for w in ("engineer", "developer", "analyst", "architect")):
            domain_score = max(0, domain_score - 5)

    # ── Architecture score ────────────────────────────────────────────────────
    arch_hits = sum(1 for sig in ARCHITECTURE_SIGNALS if sig in text_lower)
    arch_score = min(100, 40 + arch_hits * 8)

    return {
        "domain_score":     domain_score,
        "arch_score":       arch_score,
        "domain_hits":      hits,
        "arch_hits":        arch_hits,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 7: FIT SCORE & RISK SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

# DOMAIN_KEYWORDS is now imported from constants.py


def _assess_quality(candidate_profile: Dict[str, Any]) -> str:
    """Assess how complete the parsed resume data is."""
    skills_count = len(candidate_profile.get("skills_identified", []))
    exp_years    = candidate_profile.get("total_effective_years", 0)
    has_edu      = bool(candidate_profile.get("education"))
    if skills_count == 0 and exp_years == 0:
        return "low"
    if skills_count < 3 or (exp_years == 0 and not has_edu):
        return "medium"
    return "high"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT 8: LLM NARRATIVE (single call)
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_first_balanced_json_object(text: str) -> str | None:
    """
    Return the substring of the first top-level `{ ... }` with balanced braces,
    respecting double-quoted strings (so `}` inside strings does not end the object).

    LLMs often emit broken JSON after the first object (extra `}`, truncated keys).
    Taking `find('{')`..`rfind('}')` includes that garbage and breaks `json.loads`.
    Stopping at the first balanced `}` yields a *partial* but usually valid object;
    missing keys are filled with defaults below.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _parse_llm_json_response(raw: str) -> dict | None:
    """Parse JSON from LLM output; tolerate thinking tags, fences, and malformed tails."""
    clean = re.sub(r"<redacted_thinking>.*?</redacted_thinking>", "", raw, flags=re.DOTALL).strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)
    clean = clean.strip()

    for candidate in (clean,):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            log.debug("Initial JSON parse failed at position %d: %s", e.pos if hasattr(e, 'pos') else -1, str(e)[:100])

    blob = _extract_first_balanced_json_object(clean)
    if blob:
        try:
            return json.loads(blob)
        except json.JSONDecodeError as e:
            log.debug("Balanced object parse failed at position %d: %s", e.pos if hasattr(e, 'pos') else -1, str(e)[:100])
            # Trailing commas are a common LLM mistake
            try:
                fixed = re.sub(r",\s*}", "}", blob)
                fixed = re.sub(r",\s*]", "]", fixed)
                parsed = json.loads(fixed)
                log.debug("Successfully parsed after fixing trailing commas")
                return parsed
            except json.JSONDecodeError as e2:
                log.debug("Parse failed even after comma fix at position %d: %s", e2.pos if hasattr(e2, 'pos') else -1, str(e2)[:100])
    else:
        log.debug("Could not extract balanced JSON object from response")
    return None


async def explain_with_llm(context: Dict[str, Any]) -> Dict[str, Any]:
    """Single LLM call to generate narrative. Raises on failure for caller to handle."""
    llm = _get_llm()
    if llm is None:
        raise RuntimeError("LLM not available")

    jd       = context.get("jd_analysis", {})
    profile  = context.get("candidate_profile", {})
    scores   = context.get("scores", {})
    skill_a  = context.get("skill_analysis", {})
    score_rationales = context.get("score_rationales", {})
    risk_summary     = context.get("risk_summary", {})

    # Cap career_summary to 300 chars — it's already extracted by Python,
    # we only need context, not the full text (saves ~100 input tokens).
    career_snippet = (profile.get("career_summary") or "")[:300]

    # Sanitize text fields that go into the LLM prompt
    role_title = _sanitize_input(jd.get("role_title") or jd.get("title", "Unknown Role"), 200, "role_title")
    candidate_name = _sanitize_input(profile.get("name") or "Unknown", 100, "name")
    current_role = _sanitize_input(profile.get("current_role") or "N/A", 100, "current_role")
    current_company = _sanitize_input(profile.get("current_company") or "N/A", 100, "current_company")
    career_snippet = _sanitize_input(career_snippet, 400, "career_snippet")

    # Extract domain and seniority
    domain = jd.get("domain", "General")
    seniority = jd.get("seniority", "Not specified")

    # Extract experience years
    years = profile.get("total_effective_years", 0)

    # Extract scores
    skill_score = scores.get("skill_score", 0)
    exp_score = scores.get("exp_score", 0)
    edu_score = scores.get("edu_score", 0)
    timeline_score = scores.get("timeline_score", 0)
    fit_score = scores.get("fit_score", 0)
    recommendation = scores.get("final_recommendation", "Pending")

    # Extract matched and missing skills
    matched = skill_a.get("matched_skills", [])
    missing = skill_a.get("missing_skills", [])

    # Extract seniority alignment from risk_summary
    seniority_alignment = risk_summary.get("seniority_alignment", "Not assessed")

    # Format risk flags
    risk_flags_list = risk_summary.get("risk_flags", [])
    if risk_flags_list:
        risk_flags = "; ".join(
            f"{rf.get('flag', 'Unknown')}: {rf.get('detail', '')} ({rf.get('severity', 'low')})"
            for rf in risk_flags_list
        )
    else:
        risk_flags = "None identified"

    # Format score rationales into compact string
    if score_rationales:
        rationales_parts = []
        for key in ["skill_rationale", "experience_rationale", "education_rationale", "timeline_rationale"]:
            val = score_rationales.get(key, "")
            if val:
                # Truncate each rationale to ~60 chars to keep prompt compact
                rationales_parts.append(f"{key.split('_')[0]}: {val[:60]}")
        score_rationales_summary = " | ".join(rationales_parts) if rationales_parts else "Not available"
    else:
        score_rationales_summary = "Not available"

    # Build the recruiter-focused prompt with explicit JSON instruction
    prompt = f"""IMPORTANT: You must respond with ONLY a valid JSON object. No explanation, no markdown, no code blocks. Start with {{ and end with }}.

You are ARIA, an AI recruitment analyst. Produce a JSON assessment explaining
WHY this candidate is/isn't suited for this role. Be specific — reference
actual skills, scores, and gaps. Write as if advising a hiring manager.

ROLE: {role_title} | {domain} | {seniority}
CANDIDATE: {candidate_name} | {years}y experience | {current_role}
SCORES: skill={skill_score} exp={exp_score} edu={edu_score} timeline={timeline_score} fit={fit_score} /100
RECOMMENDATION: {recommendation}
MATCHED SKILLS: {', '.join(matched[:12]) if matched else 'None'}
MISSING SKILLS: {', '.join(missing[:8]) if missing else 'None'}
SENIORITY FIT: {seniority_alignment}
RISK FLAGS: {risk_flags}
SCORE RATIONALES: {score_rationales_summary}
CAREER: {career_snippet}

Return ONLY valid JSON:
{{
  "candidate_profile_summary": "A 3-4 sentence recruiter-focused summary of this candidate. Describe their professional background, years of experience, key technical strengths, and how they fit (or don't fit) this specific role. Write in third person, professional tone. Example: 'John is a senior backend engineer with 8 years of experience in distributed systems and cloud infrastructure. He demonstrates strong proficiency in Python, Go, and AWS services. His experience aligns well with the Senior Software Engineer role, though he lacks frontend development exposure required for this position.'",
  "fit_summary": "2-3 sentence executive summary for hiring manager. Be decisive — say whether this candidate is worth interviewing and why.",
  "strengths": ["specific strength tied to role requirements. Reference actual skills and scores."],
  "concerns": ["specific concern tied to role gaps. Reference actual missing skills or risk flags."],
  "dealbreakers": ["If the candidate fails any MUST-HAVE requirement from the role, list it here with evidence. If no dealbreakers, return empty array."],
  "differentiators": ["What makes this candidate UNIQUE compared to a typical applicant — positive OR negative. Be specific. Examples: 'Only candidate with Fortune 500 SaaS experience' or 'Unusually short tenure in last 3 roles (avg 11 months)'"],
  "recommendation_rationale": "why this recommendation, referencing scores and dealbreakers if any",
  "hiring_decision": {{
    "verdict": "Shortlist|Reject|Consider",
    "confidence": 0.0-1.0,
    "key_factors": ["top 3 factors that drove this decision"],
    "action_items": ["what the hiring manager should do next: e.g., 'Schedule technical interview focusing on system design', 'Request portfolio of past pre-sales decks', 'Verify enterprise SaaS exposure with references'"]
  }},
  "explainability": {{
    "skill_rationale": "skill match quality explanation",
    "experience_rationale": "experience alignment explanation",
    "overall_rationale": "synthesis of all factors"
  }},
  "interview_questions": {{
    "candidate_briefing": {{
      "profile_snapshot": "2-3 sentence summary: who is this person, current role, domain, years of experience",
      "strengths_to_confirm": ["top matched skill/experience to validate"],
      "areas_to_probe": ["specific gap, risk signal, or concern to investigate"],
      "context_notes": ["Why Q1 targets missing skill X", "Why Q4 probes the employment gap"]
    }},
    "technical_questions": [
      {{"text": "scenario-based question", "what_to_listen_for": ["competence signal", "red flag"], "follow_ups": ["conditional follow-up"], "scoring_criteria": {{"strong": "Provides specific, detailed example with measurable outcomes and evidence of hands-on depth", "adequate": "Shows general understanding and some relevant experience, but lacks specificity or measurable results", "weak": "Surface-level or theoretical answer only; unable to provide concrete examples or demonstrates no practical experience"}}}}
    ],
    "behavioral_questions": [
      {{"text": "STAR-format question", "what_to_listen_for": ["leadership/ownership signal"], "follow_ups": ["probe deeper"], "scoring_criteria": {{"strong": "Complete STAR response with specific situation, concrete actions, and quantified results showing ownership", "adequate": "Partial STAR structure with relevant experience but vague outcomes or limited personal accountability", "weak": "Generic or hypothetical answer with no real example, or unable to articulate specific actions taken"}}}}
    ],
    "culture_fit_questions": [
      {{"text": "motivation/alignment question", "what_to_listen_for": ["genuine interest signal"], "follow_ups": ["follow-up"], "scoring_criteria": {{"strong": "Demonstrates genuine, well-researched motivation with specific alignment to role/company; self-aware about fit", "adequate": "Shows general interest but lacks specificity about why this role/company; some alignment evident", "weak": "Generic motivation (salary, location); no evidence of research or genuine connection to the role"}}}}
    ],
    "experience_deep_dive_questions": [
      {{"text": "question probing specific past experience", "what_to_listen_for": ["concrete details", "measurable outcomes"], "follow_ups": ["probe for specifics"], "scoring_criteria": {{"strong": "Detailed walkthrough with clear scope, individual contribution, challenges overcome, and quantified business impact", "adequate": "Relevant experience described but vague on individual contribution or outcomes; mixes team and personal achievements", "weak": "Cannot articulate specific project details; relies on generalities or cannot distinguish personal contribution from team effort"}}}}
    ]
  }}
}}

NARRATIVE QUALITY RULES:
1. NEVER hallucinate skills not in MATCHED SKILLS or MISSING SKILLS lists.
2. NEVER invent candidate background details (company names, project names, degrees).
3. If you don't have enough information, say so explicitly rather than guessing.
4. Use the EXACT skill names from MATCHED/MISSING SKILLS — don't paraphrase.
5. dealbreakers must be based ONLY on MISSING SKILLS or RISK FLAGS, not speculation.
6. differentiators must be grounded in the actual candidate data provided.
7. hiring_decision.action_items must be SPECIFIC and ACTIONABLE — never generic like 'conduct interview'.

INTERVIEW KIT RULES — generate highly targeted, non-generic questions:
1. TECHNICAL QUESTIONS (5 questions):
   a) For EACH missing skill: Create a scenario-based question that EXPLICITLY names the missing skill and ties it to a specific job responsibility. Do NOT ask "Do you know X?" — instead use "Walk me through how you would..." or "Tell me about a time when you had to..." patterns that force the candidate to demonstrate hands-on depth, not just awareness.
   b) For 1-2 critical matched skills: Create depth-probing questions testing expertise level BEYOND awareness. Use "Tell me about a time you pushed the limits of [skill]..." format.
   c) If architecture gaps exist: Include a system design question relevant to the domain.
   d) Calibrate difficulty by domain and seniority level.
   For each question, include:
   - "what_to_listen_for": 2-3 bullet points describing what a strong answer demonstrates.
   - "follow_ups": 1-2 conditional follow-up questions.
   - "scoring_criteria": An object with "strong", "adequate", "weak" keys. Each value is a specific description for THIS question:
     * "strong": What a deep, evidence-backed answer with measurable outcomes sounds like for this specific skill/topic.
     * "adequate": What general understanding looks like — some relevant experience but lacks specifics or depth.
     * "weak": What a surface-level, theoretical-only answer looks like — no concrete examples or practical experience.

2. BEHAVIORAL QUESTIONS (4 questions, STAR format):
   a) Address the biggest risk signal from gap/timeline assessment.
   b) Target a seniority-specific challenge: senior→leadership/mentorship; mid→ownership; junior→learning agility.
   c) Probe the role transition motivation.
   d) Map behavioral questions to JD-stated soft skills. If the role implies "leadership", "team collaboration", "communication", or "cross-functional coordination", the behavioral question must DIRECTLY assess that specific skill — not a generic teamwork question.
   For each question, include "what_to_listen_for", "follow_ups", and "scoring_criteria" (strong/adequate/weak).

3. CULTURE-FIT QUESTIONS (3 questions):
   a) Motivation for THIS specific role given career trajectory.
   b) Work-style alignment tied to role context.
   c) Growth mindset and continuous learning approach.
   For each question, include "what_to_listen_for", "follow_ups", and "scoring_criteria" (strong/adequate/weak).

4. EXPERIENCE DEEP-DIVE QUESTIONS (3 questions):
   a) Ask about the most relevant past project — scope, individual contribution, challenges, measurable outcomes.
   b) Ask about working outside comfort zone or taking on responsibilities beyond job title.
   c) Ask how their approach to a key responsibility has evolved over their career.
   For each question, include "what_to_listen_for", "follow_ups", and "scoring_criteria" (strong/adequate/weak).

5. CANDIDATE BRIEFING (mandatory):
   Generate a "candidate_briefing" with: profile_snapshot (2-3 sentences), strengths_to_confirm (top 2-3), areas_to_probe (top 2-3), context_notes (why each notable question was generated).

6. SCORING GUIDANCE (mandatory for ALL questions):
   Every question MUST include a "scoring_criteria" object with three keys:
   - "strong": A concrete description of what a top-tier answer sounds like for THIS SPECIFIC question. Must reference the JD skill/competency being assessed and include examples of measurable outcomes or evidence depth.
   - "adequate": What a middling answer looks like — relevant but lacking specifics, depth, or evidence of hands-on experience.
   - "weak": What a poor answer looks like — theoretical only, no concrete examples, or demonstrates the candidate lacks practical experience with the assessed skill/competency.

DO NOT generate generic questions like "Tell me about yourself" or "What are your strengths?". Every question MUST reference specific skills, role responsibilities, or candidate context.

No markdown, no code fences."""

    import httpx  # For specific error handling
    
    from langchain_core.messages import HumanMessage
    messages = [HumanMessage(content=prompt)]
    
    # Retry configuration for 429 rate limit errors
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
    base_delay = 2.0
    
    # Wrap primary LLM call with httpx error handling and 429 retry logic
    raw = ""
    for attempt in range(max_retries + 1):
        try:
            response = await llm.ainvoke(messages)
            raw = response.content if hasattr(response, "content") else str(response)
            raw = raw.strip() if raw else ""
            break  # Success, exit retry loop
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code if e.response else 0
            if status_code == 429 and attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1.0)
                log.warning(f"LLM rate limited (429), retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                await asyncio.sleep(delay)
                continue
            # Non-retryable errors or retries exhausted
            if status_code == 401:
                raise RuntimeError("Ollama Cloud authentication failed (invalid API key)")
            elif status_code == 429:
                raise RuntimeError("Ollama Cloud rate limited — too many requests (retries exhausted)")
            elif status_code >= 500:
                raise RuntimeError(f"Ollama Cloud server error ({status_code})")
            else:
                raise RuntimeError(f"Ollama Cloud HTTP error ({status_code})")
        except httpx.ConnectError:
            _base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            raise RuntimeError(f"Cannot connect to Ollama at {_base_url}")
        except httpx.TimeoutException:
            raise RuntimeError("Ollama request timed out")
        except Exception as e:
            # Catch langchain ResponseError wrapping 429
            err_msg = str(e).lower()
            if ("429" in err_msg or "too many" in err_msg) and attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1.0)
                log.warning(f"LLM rate limited (ResponseError), retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                await asyncio.sleep(delay)
                continue
            raise  # Re-raise non-429 exceptions

    log.debug("LLM raw response (first 300 chars): %s", raw[:300] if raw else "<empty>")
    log.info("LLM response received: %d characters, %d tokens (approx)", len(raw) if raw else 0, len(raw.split()) if raw else 0)

    # Extract JSON from response (handles markdown code blocks and extra text)
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        raw = json_match.group(0)
        log.debug("Extracted JSON object: %d characters", len(raw))

    # Handle empty, whitespace-only, or ultra-short response - retry with higher temperature as fallback
    # Ultra-short responses (e.g. "{" from Ollama Cloud) are not valid JSON narratives
    # A valid narrative JSON is always 100+ chars; threshold of 20 catches degenerate outputs
    if not raw or len(str(raw).strip()) < 20:
        if raw and len(str(raw).strip()) < 20:
            log.warning(f"LLM response too short ({len(str(raw).strip())} chars), treating as empty for retry")
        else:
            log.warning("LLM returned empty response, retrying with higher temperature as fallback...")
        from langchain_ollama import ChatOllama
        _base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        _llm_timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "500"))
        _is_cloud_retry = _is_ollama_cloud(_base_url)

        # num_predict: Cloud models need significantly more tokens for verbose output
        _num_predict_retry = 8000 if _is_cloud_retry else 6000

        # Build kwargs for retry LLM - higher temperature as fallback for edge cases
        _retry_kwargs = {
            "model": os.getenv("OLLAMA_MODEL") or "gemma4:31b-cloud",
            "base_url": _base_url,
            "temperature": 0.3,
            "num_predict": _num_predict_retry,
            "num_ctx": 16384 if _is_cloud_retry else 8192,
            "request_timeout": _llm_timeout + 30,
        }

        # Add headers for Ollama Cloud authentication
        if _is_cloud_retry:
            api_key = os.getenv("OLLAMA_API_KEY", "").strip()
            if api_key:
                _retry_kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
        else:
            # Keep model always hot in RAM (-1 = never unload) — only for local Ollama
            _retry_kwargs["keep_alive"] = -1

        retry_llm = ChatOllama(**_retry_kwargs)
        
        # Wrap retry LLM call with httpx error handling and 429 retry logic
        raw = ""
        for attempt in range(max_retries + 1):
            try:
                retry_resp = await retry_llm.ainvoke(messages)
                raw = retry_resp.content.strip() if retry_resp and retry_resp.content else ""
                break  # Success, exit retry loop
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else 0
                if status_code == 429 and attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1.0)
                    log.warning(f"LLM rate limited (429), retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                # Non-retryable errors or retries exhausted
                if status_code == 401:
                    raise RuntimeError("Ollama Cloud authentication failed (invalid API key)")
                elif status_code == 429:
                    raise RuntimeError("Ollama Cloud rate limited — too many requests (retries exhausted)")
                elif status_code >= 500:
                    raise RuntimeError(f"Ollama Cloud server error ({status_code})")
                else:
                    raise RuntimeError(f"Ollama Cloud HTTP error ({status_code})")
            except httpx.ConnectError:
                raise RuntimeError(f"Cannot connect to Ollama at {_base_url}")
            except httpx.TimeoutException:
                raise RuntimeError("Ollama request timed out")
            except Exception as e:
                # Catch langchain ResponseError wrapping 429
                err_msg = str(e).lower()
                if ("429" in err_msg or "too many" in err_msg) and attempt < max_retries:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1.0)
                    log.warning(f"LLM rate limited (ResponseError), retry {attempt + 1}/{max_retries} after {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                raise  # Re-raise non-429 exceptions
        log.debug("Retry LLM raw response (first 300 chars): %s", raw[:300] if raw else "<empty>")

        # Extract JSON from retry response
        if raw:
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                raw = json_match.group(0)

    if not raw or len(str(raw).strip()) < 20:
        log.warning("LLM returned empty or too-short response after retry")
        raise ValueError("LLM returned empty response")

    data = _parse_llm_json_response(raw)
    if data is None:
        log.warning("LLM JSON extraction failed. Response length: %d chars. Raw (first 500 chars): %s", len(raw) if raw else 0, raw[:500] if raw else "<empty>")
        log.warning("LLM JSON extraction failed. Last 200 chars: %s", raw[-200:] if raw and len(raw) > 200 else raw)
        raise ValueError("LLM returned non-JSON response")

    # Handle both 'concerns' (new format) and 'weaknesses' (legacy format)
    concerns = _ensure_str_list(data.get("concernes", data.get("concerns", data.get("weaknesses", []))))
    weaknesses = _ensure_str_list(data.get("weaknesses", concerns))

    def _ensure_question_list(v) -> list:
        """Normalize question entries to dicts with text/what_to_listen_for/follow_ups/scoring_criteria."""
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str):
                result.append({"text": item, "what_to_listen_for": [], "follow_ups": []})
        return result

    iq = data.get("interview_questions", {})

    # Parse new narrative quality fields with safe defaults
    hiring_decision = data.get("hiring_decision", {})
    if not isinstance(hiring_decision, dict):
        hiring_decision = {}

    return {
        "ai_enhanced": True,  # Marks this as a real LLM-generated narrative
        "candidate_profile_summary": data.get("candidate_profile_summary") or None,
        "fit_summary":            str(data.get("fit_summary", "")),
        "strengths":              _ensure_str_list(data.get("strengths", [])),
        "concerns":               concerns,
        "weaknesses":             weaknesses,
        "dealbreakers":           _ensure_str_list(data.get("dealbreakers", [])),
        "differentiators":        _ensure_str_list(data.get("differentiators", [])),
        "recommendation_rationale": str(data.get("recommendation_rationale", "")),
        "hiring_decision": {
            "verdict": hiring_decision.get("verdict", ""),
            "confidence": hiring_decision.get("confidence", 0.0),
            "key_factors": _ensure_str_list(hiring_decision.get("key_factors", [])),
            "action_items": _ensure_str_list(hiring_decision.get("action_items", [])),
        },
        "explainability":         data.get("explainability", {}),
        "interview_questions": {
            "candidate_briefing": iq.get("candidate_briefing", {}),
            "technical_questions":   _ensure_question_list(iq.get("technical_questions", [])),
            "behavioral_questions":  _ensure_question_list(iq.get("behavioral_questions", [])),
            "culture_fit_questions": _ensure_question_list(iq.get("culture_fit_questions", [])),
            "experience_deep_dive_questions": _ensure_question_list(iq.get("experience_deep_dive_questions", [])),
        },
    }


def _ensure_str_list(v) -> List[str]:
    if not isinstance(v, list):
        return []
    return [item if isinstance(item, str) else str(item) for item in v]


def _build_fallback_narrative(python_result: Dict[str, Any], skill_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic narrative when LLM is unavailable or timed out."""
    matched  = skill_analysis.get("matched_skills", [])
    missing  = skill_analysis.get("missing_skills", [])
    score    = python_result.get("fit_score", 0)
    req      = skill_analysis.get("required_count", 0)
    actual_y = python_result.get("score_breakdown", {}).get("experience_match", 0)
    req_y    = python_result.get("_required_years", 0)
    recommendation = python_result.get("final_recommendation", "Pending")
    score_rationales = python_result.get("score_rationales", {})

    strengths = []
    if matched:
        strengths.append(f"Matches {len(matched)} required skills: {', '.join(matched[:4])}")
    if actual_y >= 70:
        strengths.append("Strong experience background")
    if not strengths:
        strengths.append("Profile submitted for review")

    concerns = []
    if missing:
        concerns.append(f"Missing key skills: {', '.join(missing[:4])}")
    if not concerns:
        concerns.append("Manual review recommended for full assessment")

    # Generate deterministic fit_summary based on scores and recommendation
    if score >= 80:
        fit_summary = f"Strong candidate with {score}/100 fit score. {len(matched)}/{req} skills matched. Recommended for {recommendation}."
    elif score >= 60:
        fit_summary = f"Viable candidate with {score}/100 fit score. {len(matched)}/{req} skills matched. Consider for interview."
    elif score >= 40:
        fit_summary = f"Mixed fit at {score}/100. Skills matched: {len(matched)}/{req}. Manual review recommended."
    else:
        fit_summary = f"Low fit score of {score}/100. Only {len(matched)}/{req} skills matched. Not recommended without significant training."

    # Use score_rationales for explainability if available, otherwise use defaults
    if score_rationales:
        explainability = {
            "skill_rationale":      score_rationales.get("skill_rationale", f"Matched {len(matched)} of {req} required skills."),
            "experience_rationale": score_rationales.get("experience_rationale", "Based on parsed employment timeline."),
            "education_rationale":  score_rationales.get("education_rationale", ""),
            "timeline_rationale":   score_rationales.get("timeline_rationale", ""),
            "domain_rationale":     score_rationales.get("domain_rationale", ""),
            "overall_rationale":    score_rationales.get("overall_rationale", f"Overall fit score: {score}/100."),
        }
    else:
        explainability = {
            "skill_rationale":      f"Matched {len(matched)} of {req} required skills.",
            "experience_rationale": "Based on parsed employment timeline.",
            "overall_rationale":    f"Overall fit score: {score}/100.",
        }

    tech_q = [
        {
            "text": "Describe a complex technical problem you solved that is relevant to this role.",
            "what_to_listen_for": [
                "Structured problem-solving approach",
                "Technical depth and relevance to the role",
                "Outcome and impact of the solution"
            ],
            "follow_ups": [
                "What alternatives did you consider?",
                "How did you measure the success of your solution?"
            ],
            "scoring_criteria": {
                "strong": "Provides detailed walkthrough of a specific technical problem with clear individual contribution and quantified business impact",
                "adequate": "Describes a relevant problem but vague on individual contribution or measurable outcomes",
                "weak": "Generic or theoretical answer; unable to describe a specific technical problem they solved"
            }
        },
        {
            "text": "Tell me about a time you had to learn a new technology quickly.",
            "what_to_listen_for": [
                "Learning strategy and resourcefulness",
                "Speed of ramp-up and practical application",
                "Self-awareness about knowledge gaps"
            ],
            "follow_ups": [
                "What resources did you rely on most?",
                "How long before you felt productive with the new technology?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example with concrete learning strategy, timeline to productivity, and measurable outcome of applying the new technology",
                "adequate": "Describes learning a new technology but lacks specifics on strategy or timeline to productivity",
                "weak": "Vague about learning process; no concrete example or evidence of rapid skill acquisition"
            }
        },
        {
            "text": "Walk me through how you approach debugging in a complex system.",
            "what_to_listen_for": [
                "Systematic debugging methodology",
                "Use of logging, monitoring, and observability tools",
                "Experience with distributed systems debugging"
            ],
            "follow_ups": [
                "Can you give a specific example of a particularly tricky bug?",
                "How do you prioritize which issues to investigate first?"
            ],
            "scoring_criteria": {
                "strong": "Describes a systematic debugging methodology with specific tools and a concrete example of diagnosing a complex issue",
                "adequate": "Shows general debugging approach but lacks specifics on tools or methodology for complex systems",
                "weak": "Only basic debugging experience; no systematic approach or evidence of handling complex system issues"
            }
        },
        {
            "text": "Give an example of how you balance technical excellence with practical constraints.",
            "what_to_listen_for": [
                "Pragmatic engineering judgment",
                "Understanding of business priorities vs technical debt",
                "Communication skills when negotiating trade-offs"
            ],
            "follow_ups": [
                "How did stakeholders react to your approach?",
                "Would you make the same trade-off again?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example with clear articulation of trade-offs, stakeholder communication, and measurable impact of the decision",
                "adequate": "Describes a relevant trade-off but lacks depth on business context or stakeholder communication",
                "weak": "Theoretical answer; no concrete example of balancing technical and business constraints"
            }
        },
        {
            "text": "How would you design a solution for a key responsibility of this role?",
            "what_to_listen_for": [
                "System design thinking relevant to the domain",
                "Consideration of scalability and edge cases",
                "Ability to articulate architectural decisions"
            ],
            "follow_ups": [
                "What trade-offs would you consider in this design?",
                "How would you handle failure scenarios?"
            ],
            "scoring_criteria": {
                "strong": "Presents a well-structured design with clear requirements, thoughtful trade-offs, and consideration of scale and failure modes",
                "adequate": "Describes a design approach but lacks depth on trade-offs, scalability, or failure handling",
                "weak": "Generic or theoretical design discussion; no evidence of hands-on system design experience"
            }
        },
    ]
    behavioral_q = [
        {
            "text": "Tell me about a time you led a difficult project. What was the outcome?",
            "what_to_listen_for": [
                "Clear STAR structure (Situation, Task, Action, Result)",
                "Evidence of ownership and accountability",
                "Specific outcomes and lessons learned"
            ],
            "follow_ups": [
                "What was the biggest obstacle and how did you overcome it?",
                "How did you keep the team aligned and motivated?"
            ],
            "scoring_criteria": {
                "strong": "Complete STAR response with specific project context, concrete leadership actions, and quantified outcomes showing ownership",
                "adequate": "Partial STAR structure with relevant leadership experience but vague outcomes or limited personal accountability",
                "weak": "Generic or hypothetical answer with no real example of leading a difficult project"
            }
        },
        {
            "text": "Describe a situation where you had to learn a new technology quickly.",
            "what_to_listen_for": [
                "Proactive learning mindset",
                "Resourcefulness in finding information",
                "Ability to apply new knowledge under pressure"
            ],
            "follow_ups": [
                "What was your biggest frustration during the learning process?",
                "How did you validate that you had learned enough to be effective?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example with concrete learning strategy, timeline, and evidence of effective application under pressure",
                "adequate": "Describes learning a new technology but lacks specifics on strategy or how they validated their knowledge",
                "weak": "Vague about the learning process; no concrete example of rapid skill acquisition under pressure"
            }
        },
        {
            "text": "Give an example of a time you resolved a conflict in a team.",
            "what_to_listen_for": [
                "Emotional intelligence and empathy",
                "Focus on finding common ground",
                "Positive resolution and relationship preservation"
            ],
            "follow_ups": [
                "What was your personal role in de-escalating the situation?",
                "What would you do differently if faced with a similar conflict?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example demonstrating empathy, active listening, and a measurable positive resolution that preserved relationships",
                "adequate": "Describes a conflict situation but resolution approach is vague or outcome is unclear",
                "weak": "No concrete example of conflict resolution; theoretical or deflective answer"
            }
        },
        {
            "text": "Describe a time when you had to collaborate with a cross-functional team to deliver a project.",
            "what_to_listen_for": [
                "Ability to communicate across disciplines",
                "Understanding of different team priorities and constraints",
                "Track record of delivering through influence rather than authority"
            ],
            "follow_ups": [
                "How did you handle differing priorities between teams?",
                "What was your approach to keeping everyone aligned?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example of cross-functional collaboration with clear communication approach, alignment strategy, and measurable project outcome",
                "adequate": "Describes cross-functional work but vague on how they handled differing priorities or communicated across disciplines",
                "weak": "No concrete example of cross-functional collaboration; answer is generic about teamwork"
            }
        },
    ]
    culture_q = [
        {
            "text": "What motivates you to apply for this role?",
            "what_to_listen_for": [
                "Genuine interest in the company and mission",
                "Alignment between personal goals and role opportunities",
                "Specific aspects of the role that excite them"
            ],
            "follow_ups": [
                "What would success look like for you in this role?",
                "What concerns do you have about this opportunity?"
            ],
            "scoring_criteria": {
                "strong": "Demonstrates genuine, well-researched motivation with specific alignment to role/company; self-aware about fit",
                "adequate": "Shows general interest but lacks specificity about why this role/company; some alignment evident",
                "weak": "Generic motivation (salary, location); no evidence of research or genuine connection to the role"
            }
        },
        {
            "text": "How do you keep up with new developments in your field?",
            "what_to_listen_for": [
                "Proactive learning habits",
                "Critical thinking about trends vs hype",
                "Practical application of new knowledge"
            ],
            "follow_ups": [
                "What's a recent trend you think is overhyped?",
                "Can you share a time you applied something new you learned?"
            ],
            "scoring_criteria": {
                "strong": "Describes specific learning habits with a concrete example of evaluating a trend and applying new knowledge with measurable impact",
                "adequate": "Shows general learning habits but lacks specifics on critical evaluation or practical application",
                "weak": "Vague about staying current; no evidence of proactive learning or critical thinking about trends"
            }
        },
        {
            "text": "Describe a time when you received critical feedback. How did you respond and what did you learn?",
            "what_to_listen_for": [
                "Growth mindset and self-awareness",
                "Ability to separate feedback from ego",
                "Concrete actions taken to improve"
            ],
            "follow_ups": [
                "How did that feedback change your approach going forward?",
                "Do you actively seek out feedback now?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example of receiving feedback, describing concrete actions taken to improve and measurable behavioral change",
                "adequate": "Describes receiving feedback but response or improvement actions are vague or generic",
                "weak": "Deflective or dismissive about feedback; no evidence of growth mindset or concrete improvement actions"
            }
        },
    ]

    candidate_briefing = {
        "profile_snapshot": "Candidate profile details not available — fallback interview kit generated.",
        "strengths_to_confirm": ["Review resume for key strengths before interview"],
        "areas_to_probe": ["Assess overall technical depth and role motivation"],
        "context_notes": ["Generic questions generated — LLM-enhanced analysis was not available"]
    }

    experience_deep_dive_q = [
        {
            "text": "Walk me through the most significant project you've worked on. What was your role, the challenges, and the outcome?",
            "what_to_listen_for": [
                "Concrete details about scope and personal contribution",
                "Measurable outcomes and results",
                "Self-awareness about what went well and what didn't"
            ],
            "follow_ups": [
                "What was the most difficult decision you had to make during that project?",
                "How did you measure success?"
            ],
            "scoring_criteria": {
                "strong": "Provides detailed walkthrough with clear scope, specific individual contribution, challenges faced, and quantified business outcomes",
                "adequate": "Describes a relevant project but vague on individual contribution or outcomes; mixes team and personal achievements",
                "weak": "Cannot articulate specific project details; relies on generalities or cannot distinguish personal contribution"
            }
        },
        {
            "text": "Describe a time you took on responsibilities beyond your job description. What drove you to do it?",
            "what_to_listen_for": [
                "Initiative and proactive mindset",
                "Ability to learn quickly in unfamiliar territory",
                "Impact of stepping up on the team or organization"
            ],
            "follow_ups": [
                "What did you learn from that experience?",
                "How did it shape your career direction?"
            ],
            "scoring_criteria": {
                "strong": "Provides specific example with clear description of the stretch, how they adapted, and measurable growth or impact resulting from it",
                "adequate": "Describes a stretch experience but vague on how they handled uncertainty or what they gained",
                "weak": "No concrete example of stepping outside comfort zone; theoretical answer only"
            }
        },
        {
            "text": "How has your professional approach changed from your first role to your current one?",
            "what_to_listen_for": [
                "Evidence of growth mindset and self-reflection",
                "Specific examples of evolved thinking or methodology",
                "Maturity in handling ambiguity and complexity"
            ],
            "follow_ups": [
                "What was the single biggest lesson in your career so far?",
                "What advice would you give your earlier self?"
            ],
            "scoring_criteria": {
                "strong": "Demonstrates clear evolution with specific before/after examples, reflecting deep professional maturity and adaptation",
                "adequate": "Shows some evolution but examples are vague or lack specificity about what changed and why",
                "weak": "Cannot articulate how their approach has evolved; answer suggests stagnation or lack of self-reflection"
            }
        },
    ]

    # Build fallback candidate_profile_summary from deterministic data
    cp = python_result.get("candidate_profile", {})
    jd_a = python_result.get("jd_analysis", {})
    sk_a = python_result.get("skill_analysis", {})
    sc = python_result.get("scores", {})

    _fallback_name = cp.get("name", "This candidate")
    _fallback_years = cp.get("total_effective_years", 0) or 0
    _fallback_domain = jd_a.get("domain", "their field")
    _fallback_matched = len(sk_a.get("matched_skills", []))
    _fallback_total = len(jd_a.get("required_skills", []))
    _fallback_rec = sc.get("final_recommendation", "Review")
    _fallback_role = jd_a.get("role_title", "this role")

    fallback_summary = (
        f"{_fallback_name} has {_fallback_years:.1f} years of experience in {_fallback_domain}. "
        f"Matched {_fallback_matched} of {_fallback_total} required skills. "
        f"Recommendation: {_fallback_rec} for {_fallback_role}."
    )

    # Return with both 'concerns' (new) and 'weaknesses' (backward compat)
    return {
        "ai_enhanced": False,  # Marks this as a fallback narrative, not LLM-generated
        "candidate_profile_summary": fallback_summary,
        "fit_summary": fit_summary,
        "strengths":   strengths,
        "concerns":    concerns,
        "weaknesses":  concerns,  # Backward compatibility alias
        "dealbreakers": concerns,  # Fallback: concerns become dealbreakers
        "differentiators": strengths,  # Fallback: strengths become differentiators
        "recommendation_rationale": (
            f"Candidate scored {score}/100. {len(matched)}/{req} required skills matched. "
            f"Automated narrative unavailable — manual review recommended."
        ),
        "hiring_decision": {
            "verdict": recommendation,
            "confidence": 0.5,
            "key_factors": [
                f"Fit score: {score}/100",
                f"Skills: {len(matched)}/{req} matched",
                f"Experience: {actual_y}/100",
            ],
            "action_items": ["Review full resume manually", "Verify missing skills in interview"],
        },
        "explainability": explainability,
        "interview_questions": {
            "candidate_briefing": candidate_briefing,
            "technical_questions":   tech_q,
            "behavioral_questions":  behavioral_q,
            "culture_fit_questions": culture_q,
            "experience_deep_dive_questions": experience_deep_dive_q,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SCORE RATIONALES & METADATA BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_score_rationales(
    all_scores: Dict[str, Any],
    profile: Dict[str, Any],
    jd: Dict[str, Any],
    skill_a: Dict[str, Any],
    exp_r: Dict[str, Any],
    edu_s: int,
    dom_r: Dict[str, Any],
    gap_analysis: Dict[str, Any],
) -> Dict[str, str]:
    """Build human-readable rationale for each score dimension."""
    matched = skill_a.get("matched_skills", [])
    missing = skill_a.get("missing_skills", [])
    req_count = skill_a.get("required_count", 0)
    skill_score = skill_a.get("skill_score", 0)

    # Skill rationale
    if matched and missing:
        skill_rat = (f"Matched {len(matched)}/{req_count} required skills "
                     f"({', '.join(matched[:5])}). "
                     f"Missing: {', '.join(missing[:5])}. Score: {skill_score}/100.")
    elif matched:
        skill_rat = (f"All {len(matched)}/{req_count} required skills matched "
                     f"({', '.join(matched[:5])}). Score: {skill_score}/100.")
    elif missing:
        skill_rat = (f"None of {req_count} required skills matched. "
                     f"Missing: {', '.join(missing[:5])}. Score: {skill_score}/100.")
    else:
        skill_rat = f"No required skills specified in job description. Score: {skill_score}/100."

    # Experience rationale
    actual_y = exp_r.get("actual_years", 0)
    req_y = exp_r.get("required_years", 0)
    exp_score = exp_r.get("exp_score", 0)
    seniority = jd.get("seniority", "unknown")
    if req_y > 0 and actual_y < req_y * 0.6:
        exp_qualifier = "Significantly underqualified"
    elif req_y > 0 and actual_y < req_y:
        exp_qualifier = "Slightly below requirement"
    elif req_y > 0 and actual_y > req_y * 2:
        exp_qualifier = "Overqualified"
    elif req_y > 0:
        exp_qualifier = "Meets requirement"
    else:
        exp_qualifier = "Experience level noted"
    exp_rat = (f"{actual_y:.1f}y experience vs {req_y}y+ expected for {seniority} role. "
               f"{exp_qualifier}. Score: {exp_score}/100.")

    # Education rationale
    education = profile.get("education", [])
    if education:
        best_edu = education[0]  # first is typically highest
        degree = best_edu.get("degree", "Unknown degree")
        field = best_edu.get("field", "")
        domain = jd.get("domain", "general")
        edu_rat = (f"{degree}{(' in ' + field) if field else ''} — "
                   f"{'relevant' if edu_s >= 65 else 'partially relevant' if edu_s >= 45 else 'limited relevance'} "
                   f"for {domain} domain. Score: {edu_s}/100.")
    else:
        edu_rat = f"No education data found in resume. Default score: {edu_s}/100."

    # Timeline rationale
    timeline_score = exp_r.get("timeline_score", 85)
    gaps = gap_analysis.get("employment_gaps", [])
    stints = gap_analysis.get("short_stints", [])
    critical_gaps = [g for g in gaps if g.get("severity") == "critical"]
    parts = []
    if critical_gaps:
        parts.append(f"{len(critical_gaps)} critical gap(s) (12+ months)")
    elif gaps:
        parts.append(f"{len(gaps)} employment gap(s)")
    else:
        parts.append("No employment gaps")
    if stints:
        parts.append(f"{len(stints)} short stint(s) (<6 months)")
    timeline_rat = f"{'. '.join(parts)}. Score: {timeline_score}/100."

    # Domain rationale
    domain_score = dom_r.get("domain_score", 50)
    arch_score = dom_r.get("arch_score", 50)
    domain = jd.get("domain", "general")
    current_role = profile.get("current_role", "Unknown")
    domain_rat = (f"Domain fit for {domain}: {domain_score}/100. "
                  f"Architecture alignment: {arch_score}/100. "
                  f"Current role: {current_role}.")

    # Overall rationale
    fit_score = all_scores.get("fit_score", 0)
    recommendation = all_scores.get("final_recommendation", "Pending")
    # Build a concise overall explanation
    top_strength = "strong skill match" if skill_score >= 70 else "adequate skills" if skill_score >= 40 else "weak skill match"
    top_concern = ""
    if exp_score < 40:
        top_concern = "insufficient experience for seniority level"
    elif len(missing) > len(matched):
        top_concern = "more required skills missing than matched"
    elif critical_gaps:
        top_concern = "critical employment gap(s)"
    elif domain_score < 40:
        top_concern = "domain mismatch"

    overall_rat = f"Fit score: {fit_score}/100 — {recommendation}. "
    if top_concern:
        overall_rat += f"Key strength: {top_strength}. Key concern: {top_concern}."
    else:
        overall_rat += f"Key strength: {top_strength}. No critical concerns identified."

    return {
        "skill_rationale": skill_rat,
        "experience_rationale": exp_rat,
        "education_rationale": edu_rat,
        "timeline_rationale": timeline_rat,
        "domain_rationale": domain_rat,
        "overall_rationale": overall_rat,
    }


def _build_risk_summary(
    risk_signals: List[Dict[str, Any]],
    gap_analysis: Dict[str, Any],
    exp_r: Dict[str, Any],
    profile: Dict[str, Any],
    jd: Dict[str, Any],
) -> Dict[str, Any]:
    """Build structured risk and alignment summary."""
    # Risk flags — convert existing risk_signals to user-friendly format
    risk_flags = []
    for rs in risk_signals:
        risk_flags.append({
            "flag": rs.get("type", "unknown").replace("_", " ").title(),
            "detail": rs.get("description", ""),
            "severity": rs.get("severity", "low"),
        })

    # Seniority alignment
    actual_y = exp_r.get("actual_years", 0)
    seniority = jd.get("seniority", "unknown")
    seniority_ranges = SENIORITY_RANGES
    lo, hi = seniority_ranges.get(seniority.lower(), (0, 100))
    if actual_y < lo:
        seniority_alignment = f"Underqualified — {actual_y:.1f}y experience, {seniority} typically requires {lo}-{hi}y"
    elif actual_y > hi:
        seniority_alignment = f"Overqualified — {actual_y:.1f}y experience, {seniority} typically requires {lo}-{hi}y"
    else:
        seniority_alignment = f"Aligned — {actual_y:.1f}y experience fits {seniority} range ({lo}-{hi}y)"

    # Career trajectory — look at work experience progression
    work_exp = profile.get("work_experience", [])
    if len(work_exp) >= 2:
        # Simple heuristic: compare first and last role titles for progression keywords
        first_title = str(work_exp[-1].get("title", "")).lower() if work_exp else ""
        last_title = str(work_exp[0].get("title", "")).lower() if work_exp else ""
        senior_keywords = {"senior", "lead", "principal", "staff", "head", "director", "manager", "architect", "vp", "chief"}
        junior_keywords = {"intern", "trainee", "junior", "associate", "entry"}
        last_is_senior = any(k in last_title for k in senior_keywords)
        first_is_junior = any(k in first_title for k in junior_keywords)
        if last_is_senior and first_is_junior:
            trajectory = f"Strong upward — progressed from '{work_exp[-1].get('title', 'N/A')}' to '{work_exp[0].get('title', 'N/A')}'"
        elif last_is_senior or (len(work_exp) >= 3):
            trajectory = f"Upward — current role: '{work_exp[0].get('title', 'N/A')}' across {len(work_exp)} positions"
        else:
            trajectory = f"Early career — {len(work_exp)} position(s), current: '{work_exp[0].get('title', 'N/A')}'"
    elif len(work_exp) == 1:
        trajectory = f"Single role — '{work_exp[0].get('title', 'N/A')}'"
    else:
        trajectory = "No work experience data available"

    # Stability assessment
    gaps = gap_analysis.get("employment_gaps", [])
    stints = gap_analysis.get("short_stints", [])
    critical_gaps = sum(1 for g in gaps if g.get("severity") == "critical")
    if critical_gaps:
        stability = f"Unstable — {critical_gaps} critical gap(s) (12+ months)"
    elif len(stints) >= 3:
        stability = f"Concerning — {len(stints)} short stints (<6 months), potential job-hopping pattern"
    elif len(stints) >= 1 or len(gaps) >= 1:
        stability = f"Moderate — {len(gaps)} gap(s), {len(stints)} short stint(s)"
    else:
        stability = "Stable — no gaps or short stints detected"

    return {
        "risk_flags": risk_flags,
        "seniority_alignment": seniority_alignment,
        "career_trajectory": trajectory,
        "stability_assessment": stability,
    }


def _compute_skill_depth(
    raw_text: str,
    matched_skills: List[str],
    missing_skills: List[str],
) -> Dict[str, int]:
    """Count how many times each skill appears in the resume text."""
    text_lower = raw_text.lower()
    depth = {}
    for skill in matched_skills:
        # Count occurrences (case-insensitive)
        count = text_lower.count(skill.lower())
        if count > 0:
            depth[skill] = count
    # Also note missing skills with 0
    for skill in missing_skills:
        depth[skill] = 0
    return depth


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATORS
# ═══════════════════════════════════════════════════════════════════════════════

def _run_python_phase(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict],
    jd_analysis: Optional[Dict],
) -> Dict[str, Any]:
    """Execute all deterministic Python components. Returns a rich result dict."""
    # Sanitize user-provided text to prevent prompt injection
    resume_text, job_description = _wrap_user_content(resume_text, job_description)

    jd       = jd_analysis or parse_jd_rules(job_description)
    profile  = parse_resume_rules(parsed_data, gap_analysis)
    skill_a  = match_skills_with_onet(
        profile.get("skills_identified", []),
        jd.get("required_skills", []),
        jd.get("nice_to_have_skills", []),
        job_title=jd.get("role_title"),
        structured_skills=profile.get("structured_skills", []),
        text_scanned_skills=profile.get("text_scanned_skills", []),
    )
    edu_s    = score_education_rules(profile, jd["domain"])
    exp_r    = score_experience_rules(profile, jd, gap_analysis)
    dom_r    = domain_architecture_rules(resume_text, jd["domain"], profile.get("current_role"))

    all_scores = {
        "skill_score":    skill_a["skill_score"],
        "exp_score":      exp_r["exp_score"],
        "arch_score":     dom_r["arch_score"],
        "edu_score":      edu_s,
        "timeline_score": exp_r["timeline_score"],
        "domain_score":   dom_r["domain_score"],
        "actual_years":   exp_r["actual_years"],
        "required_years": exp_r["required_years"],
        "matched_skills": skill_a["matched_skills"],
        "missing_skills": skill_a["missing_skills"],
        "required_count": skill_a["required_count"],
        "employment_gaps": gap_analysis.get("employment_gaps", []),
        "short_stints":    gap_analysis.get("short_stints", []),
        "fit_score": 0,
    }

    # Convert incoming weights to new schema, then map to internal 7-key schema
    # (mirrors agent_pipeline.py scorer_node — frontend may send legacy or new keys)
    log.info("Raw scoring_weights received: %s", scoring_weights)
    new_weights = convert_to_new_schema(scoring_weights)
    log.info("Converted to new schema: %s", new_weights)
    internal_weights = {
        "skills":       new_weights.get("core_competencies", 0.30),
        "experience":   new_weights.get("experience", 0.20),
        "architecture": new_weights.get("role_excellence", 0.15),
        "education":    new_weights.get("education", 0.10),
        "timeline":     new_weights.get("career_trajectory", 0.10),
        "domain":       new_weights.get("domain_fit", 0.10),
        "risk":         new_weights.get("risk", 0.15),
    }
    log.info("Internal weights for compute_fit_score: %s", internal_weights)

    fit_r = compute_fit_score(all_scores, internal_weights)
    log.info("compute_fit_score result: fit_score=%s", fit_r["fit_score"])

    # ── Deterministic engine (domain → eligibility → deterministic score) ─────
    jd_domain = {"domain": "unknown", "confidence": 0.0, "scores": {}}
    candidate_domain = {"domain": "unknown", "confidence": 0.0, "scores": {}}
    eligibility = None
    deterministic_score = fit_r["fit_score"]
    decision_explanation = {}
    deterministic_features = {}
    try:
        jd_domain = detect_domain_from_jd(job_description)
        candidate_domain = detect_domain_from_resume(
            skills=profile.get("skills_identified", []),
            resume_text=resume_text,
        )

        deterministic_features = {
            "core_skill_match": skill_a.get("core_match_ratio", 0) if isinstance(skill_a, dict) else 0,
            "secondary_skill_match": skill_a.get("secondary_match_ratio", 0) if isinstance(skill_a, dict) else 0,
            "domain_match": _compute_domain_similarity(jd_domain, candidate_domain),
            "relevant_experience": min(profile.get("total_effective_years", 0) / max(jd.get("required_years", 1), 1), 1.0),
            "total_experience": profile.get("total_effective_years", 0),
        }

        eligibility = check_eligibility(
            jd_domain=jd_domain,
            candidate_domain=candidate_domain,
            core_skill_match=deterministic_features["core_skill_match"],
            relevant_experience=deterministic_features["relevant_experience"],
        )

        # Pass the new_weights (converted schema) to deterministic scorer
        # This ensures custom/AI weights are properly used
        log.info("Passing new_weights to compute_deterministic_score: %s", new_weights)
        deterministic_score = compute_deterministic_score(deterministic_features, eligibility, new_weights)
        log.info("compute_deterministic_score result: %s (was fit_score: %s)", deterministic_score, fit_r["fit_score"])
        decision_explanation = explain_decision(deterministic_features, eligibility)
    except Exception as e:
        log.warning("Deterministic engine failed, falling back to legacy fit_score: %s", e)
        import traceback
        log.debug("Deterministic engine traceback: %s", traceback.format_exc())

    log.info("Final score after deterministic engine: %s", deterministic_score)
    all_scores["fit_score"] = deterministic_score
    # Use the deterministic decision (which respects caps) when available,
    # otherwise fall back to the legacy recommendation.
    all_scores["final_recommendation"] = (
        decision_explanation.get("decision", fit_r["final_recommendation"])
        if decision_explanation else fit_r["final_recommendation"]
    )

    rationales = _build_score_rationales(all_scores, profile, jd, skill_a, exp_r, edu_s, dom_r, gap_analysis)
    risk_summary = _build_risk_summary(fit_r["risk_signals"], gap_analysis, exp_r, profile, jd)
    skill_depth = _compute_skill_depth(resume_text, skill_a["matched_skills"], skill_a["missing_skills"])

    quality = _assess_quality(profile)

    return {
        "jd_analysis":         jd,
        "candidate_profile":   profile,
        "skill_analysis":      skill_a,
        "edu_timeline_analysis": {
            "education_score":  edu_s,
            "timeline_text":    exp_r["timeline_text"],
            "employment_gaps":  gap_analysis.get("employment_gaps", []),
            "overlapping_jobs": gap_analysis.get("overlapping_jobs", []),
            "short_stints":     gap_analysis.get("short_stints", []),
        },
        # Top-level fields for AnalysisResponse schema
        "fit_score":            deterministic_score,
        "job_role":             jd["role_title"],
        "final_recommendation": all_scores["final_recommendation"],
        "risk_level":           fit_r["risk_level"],
        "risk_signals":         fit_r["risk_signals"],
        "score_breakdown":      fit_r["score_breakdown"],
        "matched_skills":       skill_a["matched_skills"],
        "missing_skills":       skill_a["missing_skills"],
        "adjacent_skills":      skill_a["adjacent_skills"],
        "required_skills_count": skill_a["required_count"],
        "work_experience":      parsed_data.get("work_experience", []),
        "contact_info":         parsed_data.get("contact_info", {}),
        "employment_gaps":      gap_analysis.get("employment_gaps", []),
        "education_analysis":   None,
        "analysis_quality":     quality,
        "narrative_pending":    False,
        "pipeline_errors":      [],
        "score_rationales":     rationales,
        "risk_summary":         risk_summary,
        "skill_depth":          skill_depth,
        # Deterministic engine outputs
        "deterministic_score":  deterministic_score,
        "decision_explanation": decision_explanation,
        "jd_domain":            jd_domain,
        "candidate_domain":     candidate_domain,
        "eligibility":          {
            "eligible": eligibility.eligible,
            "reason": eligibility.reason,
            "details": eligibility.details,
        } if eligibility else {"eligible": True, "reason": None, "details": {}},
        "deterministic_features": deterministic_features,
        # O*NET occupation-aware validation (optional — absent when DB not synced)
        "onet_occupation":     skill_a.get("onet_validation", {}).get("occupation_title", ""),
        "onet_soc_code":      skill_a.get("onet_validation", {}).get("soc_code", ""),
        "onet_match_ratio":   skill_a.get("onet_validation", {}).get("occupation_match_ratio", 0.0),
        "onet_hot_skills":    [
            s["skill"] for s in skill_a.get("onet_validation", {}).get("validated", [])
            if s.get("is_hot")
        ],
        # Internal — used by fallback
        "_required_years":      exp_r["required_years"],
        "_scores":              all_scores,
    }


def _merge_llm_into_result(python_result: Dict[str, Any], llm_result: Dict[str, Any]) -> Dict[str, Any]:
    """Merge LLM narrative into the Python result dict."""
    merged = dict(python_result)

    # Handle concerns/weaknesses for backward compatibility
    # If LLM returns concerns (new format), use it for both fields
    # If LLM returns weaknesses (old format), use it for both fields
    concerns = llm_result.get("concerns", [])
    weaknesses = llm_result.get("weaknesses", [])

    # Normalize: ensure both fields exist and are consistent
    if concerns and not weaknesses:
        # New format: concerns provided, weaknesses not
        final_concerns = concerns
        final_weaknesses = concerns
    elif weaknesses and not concerns:
        # Old format: weaknesses provided, concerns not
        final_concerns = weaknesses
        final_weaknesses = weaknesses
    elif concerns:
        # Both provided - prefer concerns for concerns, but ensure consistency
        final_concerns = concerns
        final_weaknesses = weaknesses if weaknesses else concerns
    else:
        # Neither provided - use empty lists
        final_concerns = []
        final_weaknesses = []

    merged.update({
        "ai_enhanced":            llm_result.get("ai_enhanced", False),  # True for LLM, False for fallback
        "candidate_profile_summary": llm_result.get("candidate_profile_summary"),
        "fit_summary":            llm_result.get("fit_summary", ""),
        "strengths":              llm_result.get("strengths", []),
        "concerns":               final_concerns,
        "weaknesses":             final_weaknesses,
        "recommendation_rationale": llm_result.get("recommendation_rationale", ""),
        "explainability":         llm_result.get("explainability", {}),
        "interview_questions":    llm_result.get("interview_questions"),
        "education_analysis":     llm_result.get("explainability", {}).get("skill_rationale"),
    })
    # Remove internal keys
    merged.pop("_required_years", None)
    merged.pop("_scores", None)
    return merged


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND LLM NARRATIVE TASK
# ═══════════════════════════════════════════════════════════════════════════════

async def _background_llm_narrative(
    screening_result_id: int,
    tenant_id: int,
    llm_context: Dict[str, Any],
    python_result: Dict[str, Any],
) -> None:
    """
    Background task that generates LLM narrative and writes to DB.
    
    This runs independently after the Python results are returned.
    Creates its own DB session to avoid sharing with request.
    """
    # Import here to avoid circular imports
    from app.backend.db.database import SessionLocal
    from app.backend.models.db_models import ScreeningResult, Candidate

    # Helper to write status to DB
    async def _write_status(status: str, error: Optional[str] = None) -> bool:
        """Write narrative_status and narrative_error to DB. Returns True on success."""
        try:
            db = SessionLocal()
            try:
                result = db.query(ScreeningResult).filter(
                    ScreeningResult.id == screening_result_id,
                    ScreeningResult.tenant_id == tenant_id,
                ).first()
                if result:
                    result.narrative_status = status
                    result.narrative_error = error
                    db.commit()
                    return True
            finally:
                db.close()
        except Exception as db_err:
            log.error("Failed to write status to DB: %s", str(db_err)[:200])
        return False

    # Helper to write narrative with retry
    async def _write_narrative_with_retry(
        narrative: Dict[str, Any],
        status: str,
        error: Optional[str] = None,
    ) -> bool:
        """Write narrative_json, status, and error to DB with one retry on failure.
        
        Also updates analysis_result with merged narrative data so the complete
        report is available when viewing from the Candidates page.
        """
        for attempt in range(2):
            try:
                db = SessionLocal()
                try:
                    result = db.query(ScreeningResult).filter(
                        ScreeningResult.id == screening_result_id,
                        ScreeningResult.tenant_id == tenant_id,
                    ).first()
                    if result:
                        # Update narrative fields
                        result.narrative_json = json.dumps(narrative, default=str)
                        result.narrative_status = status
                        result.narrative_error = error
                        
                        # Merge narrative into analysis_result for complete report persistence
                        # This ensures the Candidates page shows the full report, not "PENDING"
                        try:
                            current_analysis = json.loads(result.analysis_result or "{}")
                            # If analysis_result is empty or missing critical fields,
                            # use python_result as the base (available from outer scope)
                            if not current_analysis.get("fit_score") and python_result.get("fit_score") is not None:
                                log.warning(
                                    "analysis_result for screening_result_id=%s is empty/missing fit_score "
                                    "(%d keys). Using python_result as base for narrative merge.",
                                    screening_result_id, len(current_analysis),
                                )
                                base = {k: v for k, v in python_result.items() if not k.startswith("_")}
                                current_analysis = base
                            merged_analysis = _merge_llm_into_result(current_analysis, narrative)
                            result.analysis_result = json.dumps(merged_analysis, default=str)
                        except Exception as merge_err:
                            log.warning(
                                "Failed to merge narrative into analysis_result for screening_result_id=%s: %s",
                                screening_result_id,
                                str(merge_err)[:200],
                            )
                            # Continue even if merge fails - narrative_json is still saved
                        
                        db.commit()

                        # Cache candidate_profile_summary to Candidate.ai_professional_summary
                        summary = narrative.get("candidate_profile_summary")
                        if summary and result.candidate_id:
                            try:
                                candidate = db.query(Candidate).filter(
                                    Candidate.id == result.candidate_id
                                ).first()
                                if candidate:
                                    candidate.ai_professional_summary = summary
                                    db.commit()
                            except Exception as cache_err:
                                log.warning(
                                    "Failed to cache ai_professional_summary for candidate_id=%s: %s",
                                    result.candidate_id,
                                    str(cache_err)[:200],
                                )

                        log.info(
                            "Wrote narrative_json (status=%s) to screening_result_id=%s",
                            status,
                            screening_result_id,
                        )
                        return True
                    else:
                        log.warning(
                            "screening_result_id=%s not found for narrative write (tenant_id=%s)",
                            screening_result_id,
                            tenant_id,
                        )
                        return False
                finally:
                    db.close()
            except Exception as db_err:
                if attempt == 0:
                    log.warning(
                        "DB write failed for screening_result_id=%s, retrying in 2s: %s",
                        screening_result_id,
                        str(db_err)[:200],
                    )
                    await asyncio.sleep(2)
                else:
                    log.error(
                        "Failed to write narrative to DB for screening_result_id=%s after retry: %s",
                        screening_result_id,
                        str(db_err)[:200],
                    )
        return False

    # Track status and error for final write
    narrative_status = "pending"
    narrative_error: Optional[str] = None
    llm_result: Optional[Dict[str, Any]] = None
    _start_time: Optional[float] = None

    log.info(
        "Background LLM task started for screening_result_id=%s (timeout=%ss)",
        screening_result_id,
        os.getenv("LLM_NARRATIVE_TIMEOUT", "500"),
    )

    try:
        _bg_timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "500"))
        sem = get_ollama_semaphore()
        if sem.locked():
            log.info(
                "Waiting for Ollama slot for screening_result_id=%s (another request in progress)...",
                screening_result_id,
            )
        async with sem:
            log.info("Acquired Ollama slot for screening_result_id=%s", screening_result_id)
            # Write 'processing' status before starting LLM call
            await _write_status("processing")

            _start_time = time.monotonic()
            llm_result = await asyncio.wait_for(explain_with_llm(llm_context), timeout=_bg_timeout)
            elapsed = time.monotonic() - _start_time
            LLM_CALL_DURATION.observe(elapsed)
            log.info(
                "LLM call completed for screening_result_id=%s in %.1fs (response keys: %s)",
                screening_result_id,
                elapsed,
                list(llm_result.keys()) if isinstance(llm_result, dict) else "N/A",
            )

        # Success path
        narrative_status = "ready"
        narrative_error = None
        log.info(
            "Background LLM narrative succeeded for screening_result_id=%s",
            screening_result_id,
        )
    except asyncio.CancelledError:
        log.info("Background LLM task cancelled for screening_result_id=%s", screening_result_id)
        # Write failed status to DB before returning
        await _write_status("failed", "Analysis was cancelled")
        return
    except asyncio.TimeoutError:
        elapsed = (time.monotonic() - _start_time) if _start_time is not None else _bg_timeout
        log.warning(
            "Background LLM narrative timed out for screening_result_id=%s after %.0fs",
            screening_result_id,
            elapsed,
        )
        LLM_FALLBACK_TOTAL.inc()
        narrative_status = "failed"
        narrative_error = "AI analysis timed out. Showing standard analysis."
        llm_result = _build_fallback_narrative(python_result, python_result["skill_analysis"])
    except Exception as e:
        log.warning(
            "Background LLM narrative failed for screening_result_id=%s: %s: %s",
            screening_result_id,
            type(e).__name__,
            str(e)[:200],
        )
        LLM_FALLBACK_TOTAL.inc()
        narrative_status = "failed"
        narrative_error = str(e)[:200]
        llm_result = _build_fallback_narrative(python_result, python_result["skill_analysis"])

    # Write final result to DB with retry
    if llm_result:
        write_ok = await _write_narrative_with_retry(llm_result, narrative_status, narrative_error)
        if not write_ok:
            log.error(
                "Critical: failed to persist narrative for screening_result_id=%s. "
                "Attempting status-only write.",
                screening_result_id,
            )
            await _write_status(narrative_status, narrative_error)


async def run_hybrid_pipeline(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict] = None,
    jd_analysis: Optional[Dict] = None,
    screening_result_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Non-streaming version. Returns Python scoring results immediately.
    
    If screening_result_id and tenant_id are provided, spawns a background
    task to generate LLM narrative and write to DB. The immediate result
    includes narrative_pending=True and a fallback narrative.
    
    If screening_result_id is None, falls back to synchronous LLM call
    (for backward compatibility with batch and existing tests).
    """
    python_result = _run_python_phase(
        resume_text, job_description, parsed_data, gap_analysis, scoring_weights, jd_analysis
    )

    llm_context = {
        "jd_analysis":       python_result["jd_analysis"],
        "candidate_profile": python_result["candidate_profile"],
        "skill_analysis":    python_result["skill_analysis"],
        "scores": {
            **python_result["_scores"],
            "fit_score":            python_result["fit_score"],
            "final_recommendation": python_result["final_recommendation"],
        },
        # Enriched Python data from Task 17
        "score_rationales":  python_result.get("score_rationales", {}),
        "risk_summary":      python_result.get("risk_summary", {}),
        "skill_depth":       python_result.get("skill_depth", {}),
    }

    # If screening_result_id provided, spawn background task and return immediately
    if screening_result_id is not None and tenant_id is not None:
        fallback = _build_fallback_narrative(python_result, python_result["skill_analysis"])
        python_result["narrative_pending"] = True
        
        # Spawn background LLM task
        task = asyncio.create_task(
            _background_llm_narrative(
                screening_result_id=screening_result_id,
                tenant_id=tenant_id,
                llm_context=llm_context,
                python_result=python_result,
            )
        )
        register_background_task(task)
        
        return _merge_llm_into_result(python_result, fallback)

    # Legacy synchronous mode (for batch processing and tests without DB persistence)
    _LLM_TIMEOUT = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "500"))

    try:
        sem = get_ollama_semaphore()
        if sem.locked():
            log.info("Waiting for Ollama slot (another request in progress)...")
        async with sem:
            start = time.monotonic()
            llm_result = await asyncio.wait_for(explain_with_llm(llm_context), timeout=_LLM_TIMEOUT)
            LLM_CALL_DURATION.observe(time.monotonic() - start)
        log.info("LLM narrative succeeded for fit_score=%s", python_result.get("fit_score"))
    except asyncio.TimeoutError:
        log.warning(
            "LLM explain timed out after %.0fs — using fallback narrative. "
            "Model may still be loading. Consider increasing LLM_NARRATIVE_TIMEOUT env var.",
            _LLM_TIMEOUT,
        )
        LLM_FALLBACK_TOTAL.inc()
        llm_result = _build_fallback_narrative(python_result, python_result["skill_analysis"])
        python_result["narrative_pending"] = True
    except Exception as e:
        log.warning(
            "LLM explain failed (%s: %s) — using fallback narrative (OLLAMA_BASE_URL=%s OLLAMA_MODEL=%s)",
            type(e).__name__,
            str(e)[:200],
            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            os.getenv("OLLAMA_MODEL") or "gemma4:31b-cloud",
        )
        LLM_FALLBACK_TOTAL.inc()
        llm_result = _build_fallback_narrative(python_result, python_result["skill_analysis"])
        python_result["narrative_pending"] = True

    return _merge_llm_into_result(python_result, llm_result)


async def astream_hybrid_pipeline(
    resume_text: str,
    job_description: str,
    parsed_data: Dict[str, Any],
    gap_analysis: Dict[str, Any],
    scoring_weights: Optional[Dict] = None,
    jd_analysis: Optional[Dict] = None,
    screening_result_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    SSE streaming version.

    If screening_result_id and tenant_id are provided:
      - Yields Python results immediately with narrative_pending=True
      - Spawns background LLM task that writes to DB
      - Frontend polls GET /api/analysis/{id}/narrative for the LLM narrative
    
    If screening_result_id is None (legacy mode):
      - Yields:
        {"stage": "parsing",  "result": {all Python scores}}  — within 2s
        {"stage": "scoring",  "result": {LLM narrative}}       — after ~40s
        {"stage": "complete", "result": {full merged result}}
    """
    # Phase 1 — Python (instant)
    python_result = _run_python_phase(
        resume_text, job_description, parsed_data, gap_analysis, scoring_weights, jd_analysis
    )

    llm_context = {
        "jd_analysis":       python_result["jd_analysis"],
        "candidate_profile": python_result["candidate_profile"],
        "skill_analysis":    python_result["skill_analysis"],
        "scores": {
            **python_result["_scores"],
            "fit_score":            python_result["fit_score"],
            "final_recommendation": python_result["final_recommendation"],
        },
        # Enriched Python data from Task 17
        "score_rationales":  python_result.get("score_rationales", {}),
        "risk_summary":      python_result.get("risk_summary", {}),
        "skill_depth":       python_result.get("skill_depth", {}),
    }

    # If screening_result_id provided, spawn background task and return immediately
    if screening_result_id is not None and tenant_id is not None:
        fallback = _build_fallback_narrative(python_result, python_result["skill_analysis"])
        python_result["narrative_pending"] = True
        final = _merge_llm_into_result(python_result, fallback)
        
        # Strip internal keys for the SSE payload
        parsing_payload = {k: v for k, v in python_result.items()
                           if not k.startswith("_")}
        
        # Yield parsing stage with Python results
        yield {"stage": "parsing", "result": parsing_payload}
        
        # Spawn background LLM task
        task = asyncio.create_task(
            _background_llm_narrative(
                screening_result_id=screening_result_id,
                tenant_id=tenant_id,
                llm_context=llm_context,
                python_result=python_result,
            )
        )
        register_background_task(task)
        
        # Yield complete with fallback narrative and analysis_id for polling
        final["analysis_id"] = screening_result_id
        yield {"stage": "complete", "result": final}
        return

    # Legacy synchronous streaming mode (for backward compatibility)
    # Strip internal keys for the SSE payload
    parsing_payload = {k: v for k, v in python_result.items()
                       if not k.startswith("_")}
    yield {"stage": "parsing", "result": parsing_payload}

    # Phase 2 — LLM with heartbeat pings to keep Cloudflare/Nginx alive
    llm_queue: asyncio.Queue = asyncio.Queue()

    _LLM_TIMEOUT_STREAM = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "500"))

    async def _llm_task():
        try:
            sem = get_ollama_semaphore()
            if sem.locked():
                log.info("Waiting for Ollama slot (another request in progress)...")
            async with sem:
                start = time.monotonic()
                result = await asyncio.wait_for(explain_with_llm(llm_context), timeout=_LLM_TIMEOUT_STREAM)
                LLM_CALL_DURATION.observe(time.monotonic() - start)
            log.info("LLM stream narrative succeeded")
            await llm_queue.put(("ok", result))
        except asyncio.TimeoutError:
            log.warning(
                "LLM stream timed out after %.0fs — using fallback. "
                "Increase LLM_NARRATIVE_TIMEOUT if model is still loading.",
                _LLM_TIMEOUT_STREAM,
            )
            LLM_FALLBACK_TOTAL.inc()
            fallback = _build_fallback_narrative(python_result, python_result["skill_analysis"])
            python_result["narrative_pending"] = True
            await llm_queue.put(("fallback", fallback))
        except Exception as e:
            log.warning(
                "LLM stream failed (%s: %s) — using fallback (OLLAMA_BASE_URL=%s OLLAMA_MODEL=%s)",
                type(e).__name__,
                str(e)[:200],
                os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                os.getenv("OLLAMA_MODEL") or "gemma4:31b-cloud",
            )
            LLM_FALLBACK_TOTAL.inc()
            fallback = _build_fallback_narrative(python_result, python_result["skill_analysis"])
            python_result["narrative_pending"] = True
            await llm_queue.put(("fallback", fallback))

    task = asyncio.create_task(_llm_task())
    llm_result = None
    try:
        while True:
            try:
                status, llm_result = await asyncio.wait_for(llm_queue.get(), timeout=5.0)
                break
            except asyncio.TimeoutError:
                yield ": ping\n\n"  # SSE comment — keeps connection alive during LLM wait
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    yield {"stage": "scoring", "result": llm_result or {}}

    final = _merge_llm_into_result(python_result, llm_result or {})
    yield {"stage": "complete", "result": final}
