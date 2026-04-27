"""
LangGraph Multi-Agent Pipeline for Resume Analysis.

Architecture — 3 dependency stages, parallel within each stage:
  Stage 1 (parallel): jd_parser + resume_parser
      No dependencies — fire immediately from START.
  Stage 2 (parallel): skill_domain + edu_timeline
      Both wait for Stage 1 (both jd_parser AND resume_parser) to complete.
  Stage 3 (parallel): scorer_explainer + interview_qs
      Both wait for Stage 2 (both skill_domain AND edu_timeline) to complete.

Models:
  get_fast_llm()      → qwen3.5:4b  (extraction / matching / education / interview)
  get_reasoning_llm() → qwen3.5:4b  (scoring / explainability — needs deeper reasoning)

Design principles:
  - The LLM determines ALL intelligence: skill extraction, semantic matching,
    education relevance, domain fit, scoring, explainability, recommendation.
  - The backend only pre-computes objective gap math (months between dates)
    and passes it as structured data so the LLM doesn't parse raw date strings.
  - temperature=0.0 + format="json" for deterministic, schema-bound output.
  - Fallback per node: if any Ollama call fails, the pipeline returns safe
    typed-null defaults rather than crashing.
"""

import hashlib
import json
import os
import re
from datetime import datetime, date
from decimal import Decimal
from typing import TypedDict, Annotated, Any, Dict, List, Optional
import operator
import logging

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama

from app.backend.services.constants import (
    RECOMMENDATION_THRESHOLDS,
    SENIORITY_RANGES,
    DEFAULT_WEIGHTS,
)
from app.backend.services.risk_calculator import compute_risk_penalty
from app.backend.services.fit_scorer import compute_fit_score
from app.backend.services.skill_matcher import validate_skills_against_text


def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, adding ellipsis if truncated."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


# ─── Configuration ─────────────────────────────────────────────────────────────

OLLAMA_BASE_URL       = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_FAST_MODEL     = os.getenv("OLLAMA_FAST_MODEL", "gemma4:31b-cloud")
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:31b-cloud")


def _is_ollama_cloud(base_url: str) -> bool:
    """Check if the base URL points to Ollama Cloud (ollama.com)."""
    return "ollama.com" in base_url.lower()


def _get_ollama_headers(base_url: str) -> Dict[str, str]:
    """Build headers for Ollama API requests. Adds Authorization header for cloud."""
    headers = {}
    if _is_ollama_cloud(base_url):
        api_key = os.getenv("OLLAMA_API_KEY", "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    return headers

from app.backend.services.guardrail_service import (
    llm_invoke_with_retry,
    validate_jd_output,
    validate_resume_output,
    validate_scorer_output,
    check_cross_node_consistency,
    detect_prompt_injection,
    sanitize_for_injection,
    ensemble_vote_3x,
    vote_jd_parser,
    vote_scorer,
    hitl_gate_check,
    get_token_budget_manager,
    get_ab_test_tracker,
    emit_guardrail_event,
    estimate_tokens,
    ConsistencyReport,
    HITLFlag,
)

# DEFAULT_WEIGHTS is now imported from constants.py

# Nodes that emit SSE events when complete (3-step sequential pipeline)
STREAMABLE_NODES = {"jd_parser", "resume_analyser", "scorer"}


# ─── LLM singletons (created once, reused across all requests) ─────────────────
# Creating a new ChatOllama per call adds connection overhead and prevents Ollama
# from reusing its internal HTTP keep-alive sessions.

_fast_llm: Optional[ChatOllama] = None
_reasoning_llm: Optional[ChatOllama] = None

# In-memory JD cache: MD5(jd_text[:8000] + prompt_version) → parsed jd_analysis dict.
# For batch screening (same JD, many resumes) this skips the jd_parser LLM call
# entirely after the first request, saving ~3–8 seconds per candidate.
# Cache is invalidated automatically when the prompt changes (prompt_version hash).
_jd_cache: Dict[str, dict] = {}

_llm_request_timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "150")) + 30

# Guardrail Tier 2+4: Feature flags
_GUARDRAIL_ENSEMBLE_ENABLED = os.getenv("GUARDRAIL_ENSEMBLE_ENABLED", "false").lower() == "true"
_GUARDRAIL_INJECTION_CHECK = os.getenv("GUARDRAIL_INJECTION_CHECK", "true").lower() == "true"
_GUARDRAIL_TOKEN_BUDGET = os.getenv("GUARDRAIL_TOKEN_BUDGET", "true").lower() == "true"

logger = logging.getLogger(__name__)


def get_fast_llm(seed: Optional[int] = None) -> ChatOllama:
    """Fast model for jd_parser + resume_analyser. Singleton — never re-initialised."""
    global _fast_llm
    if _fast_llm is None and seed is None:
        _is_cloud = _is_ollama_cloud(OLLAMA_BASE_URL)
        # Cloud models need significantly more tokens for verbose output
        # Local: 600 tokens sufficient for combined schema
        # Cloud: 3000 tokens for very large models (480B+) that generate extremely verbose output
        _num_predict = 3000 if _is_cloud else 600
        _num_ctx = 12288 if _is_cloud else 3072

        _llm_kwargs = {
            "model": OLLAMA_FAST_MODEL,
            "base_url": OLLAMA_BASE_URL,
            "temperature": 0.0,
            "seed": seed if seed is not None else 42,
            "format": "json",
            "num_predict": _num_predict,
            "num_ctx": _num_ctx,
            "request_timeout": _llm_request_timeout,
        }

        # Add headers for Ollama Cloud authentication
        headers = _get_ollama_headers(OLLAMA_BASE_URL)
        if headers:
            _llm_kwargs["headers"] = headers

        # Keep model hot only for local Ollama
        if not _is_cloud:
            _llm_kwargs["keep_alive"] = -1

        _fast_llm = ChatOllama(**_llm_kwargs)
    return _fast_llm


def get_reasoning_llm(seed: Optional[int] = None) -> ChatOllama:
    """Reasoning model for combined scorer + interview questions. Singleton."""
    global _reasoning_llm
    if _reasoning_llm is None and seed is None:
        _is_cloud = _is_ollama_cloud(OLLAMA_BASE_URL)
        # Cloud models need significantly more tokens for verbose output
        # Local: 800 tokens sufficient for scorer + interview_questions
        # Cloud: 4000 tokens for very large models (480B+) that generate extremely verbose output
        _num_predict = 4000 if _is_cloud else 800
        _num_ctx = 8192 if _is_cloud else 2048

        _llm_kwargs = {
            "model": OLLAMA_REASONING_MODEL,
            "base_url": OLLAMA_BASE_URL,
            "temperature": 0.0,
            "seed": seed if seed is not None else 42,
            "format": "json",
            "num_predict": _num_predict,
            "num_ctx": _num_ctx,
            "request_timeout": _llm_request_timeout,
        }

        # Add headers for Ollama Cloud authentication
        headers = _get_ollama_headers(OLLAMA_BASE_URL)
        if headers:
            _llm_kwargs["headers"] = headers

        # Keep model hot only for local Ollama
        if not _is_cloud:
            _llm_kwargs["keep_alive"] = -1

        _reasoning_llm = ChatOllama(**_llm_kwargs)
    return _reasoning_llm


# ─── Pipeline state ─────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    # ── Inputs (set before graph runs) ──
    raw_jd_text:         str
    raw_resume_text:     str
    employment_timeline: list   # pre-computed by GapDetector (objective date math)
    scoring_weights:     dict

    # ── Node outputs (3-call sequential pipeline) ──
    jd_analysis:           dict   # from jd_parser (Step 1)
    candidate_profile:     dict   # from resume_analyser (Step 2)
    skill_analysis:        dict   # from resume_analyser (Step 2)
    edu_timeline_analysis: dict   # from resume_analyser (Step 2)
    final_scores:          dict   # from scorer (Step 3)
    interview_questions:   dict   # from scorer (Step 3)

    # ── Accumulates errors from all nodes ──
    errors: Annotated[list, operator.add]


# ─── JSON parsing helper ────────────────────────────────────────────────────────

def _parse_json(content: str, fallback: dict) -> dict:
    """Parse LLM JSON response; extract first JSON object on failure."""
    if not content:
        return fallback
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        m = re.search(r"\{.*\}", str(content), re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return fallback


def _sanitize_jd_output(data: dict, original_jd_text: str) -> dict:
    """Post-process and sanitize JD parser output to remove hallucinations."""
    fallback = {
        "role_title": "", "domain": "other", "seniority": "mid",
        "required_skills": [], "required_years": 0,
        "nice_to_have_skills": [], "key_responsibilities": [],
    }

    if not isinstance(data, dict):
        return fallback

    # Ensure all expected keys exist
    for key, default in fallback.items():
        if key not in data or data[key] is None:
            data[key] = default

    # Validate skills against original JD text (hallucination guard)
    data["required_skills"] = validate_skills_against_text(
        data.get("required_skills", []), original_jd_text
    )
    data["nice_to_have_skills"] = validate_skills_against_text(
        data.get("nice_to_have_skills", []), original_jd_text
    )

    # Normalize seniority
    valid_seniority = set(SENIORITY_RANGES.keys()) | {"principal"}
    if data.get("seniority") not in valid_seniority:
        years = data.get("required_years", 0)
        if years >= SENIORITY_RANGES["senior"][0]:
            data["seniority"] = "senior"
        elif years >= SENIORITY_RANGES["mid"][0]:
            data["seniority"] = "mid"
        else:
            data["seniority"] = "junior"

    # Normalize domain
    valid_domains = {
        "backend", "frontend", "fullstack", "data_science", "ml_ai",
        "devops", "embedded", "mobile", "design", "management", "other"
    }
    if data.get("domain") not in valid_domains:
        data["domain"] = "other"

    # Clamp required_years
    try:
        data["required_years"] = max(0, min(50, int(data.get("required_years", 0))))
    except (ValueError, TypeError):
        data["required_years"] = 0

    # Ensure key_responsibilities is a list of strings
    responsibilities = data.get("key_responsibilities", [])
    if isinstance(responsibilities, list):
        data["key_responsibilities"] = [
            str(r) for r in responsibilities if r is not None
        ]
    else:
        data["key_responsibilities"] = []

    return data


# ─── Stage 1: JD Parser ────────────────────────────────────────────────────────

_JD_PARSER_PROMPT = """\
You are a strict, literal job requirement extractor. Your job is to TRANSCRIBE, not interpret.

SYSTEM RULES:
1. ONLY extract information explicitly stated in the JD text.
2. Do NOT infer, guess, or assume skills not explicitly named.
3. Do NOT add programming languages or tools unless the JD explicitly lists them.
4. "Associate Director" is a SENIOR title — do NOT misread "Associate" as junior.
5. If no specific technical skills are listed, output an empty required_skills array.
6. Extract required_years from explicit statements (e.g., "5+ years" → 5, "minimum 3 years" → 3).
7. Output ONLY valid JSON. No markdown, no explanations, no comments.

FEW-SHOT EXAMPLES:

Correct extraction:
JD: "We need a Senior Python Engineer with 5+ years of experience in Django and AWS."
Output: {{"role_title": "Senior Python Engineer", "domain": "backend", "seniority": "senior", "required_skills": ["Python", "Django", "AWS"], "required_years": 5, "nice_to_have_skills": [], "key_responsibilities": []}}

Correct extraction (advisory role):
JD: "Associate Director – Technical Pre-Sales. 10+ years in enterprise SaaS. Strong communication skills required."
Output: {{"role_title": "Associate Director – Technical Pre-Sales", "domain": "management", "seniority": "senior", "required_skills": ["communication"], "required_years": 10, "nice_to_have_skills": [], "key_responsibilities": []}}

INCORRECT (Hallucination — do NOT do this):
JD: "Technical advisor for enterprise SaaS."
Output: {{"required_skills": ["golang", "kubernetes"]}} ← WRONG — these are NOT in the text

CURRENT JD:
{jd_text}

OUTPUT SCHEMA:
{{
  "role_title": "",
  "domain": "backend|frontend|fullstack|data_science|ml_ai|devops|embedded|mobile|design|management|other",
  "seniority": "junior|mid|senior|lead|principal",
  "required_skills": [],
  "required_years": 0,
  "nice_to_have_skills": [],
  "key_responsibilities": []
}}"""

# Guardrail: Phase 2 — cache versioning. Changing the prompt invalidates old cache entries.
_PROMPT_VERSION = hashlib.md5(_JD_PARSER_PROMPT.encode()).hexdigest()[:8]

# Guardrail: Phase 4 — circuit breaker for JD parser hallucinations.
_hallucination_counter: Dict[str, int] = {"count": 0, "last_reset": datetime.now().timestamp()}
_CIRCUIT_BREAKER_THRESHOLD = 5  # max hallucinations per hour before fallback to rules


async def jd_parser_node(state: PipelineState) -> dict:
    fallback = {
        "role_title": "", "domain": "other", "seniority": "mid",
        "required_skills": [], "required_years": 0,
        "nice_to_have_skills": [], "key_responsibilities": [],
    }
    raw_jd = state["raw_jd_text"]
    tenant_id = state.get("tenant_id")

    # Guardrail Tier 2: Prompt injection detection
    if _GUARDRAIL_INJECTION_CHECK:
        is_suspicious, confidence, patterns = detect_prompt_injection(raw_jd)
        if is_suspicious:
            emit_guardrail_event(
                "prompt_injection_blocked",
                tenant_id=tenant_id,
                metadata={"confidence": confidence, "patterns": patterns, "source": "jd_text"},
            )
            # Sanitize but continue processing
            raw_jd = sanitize_for_injection(raw_jd)

    # Guardrail: increased truncation to capture full requirements section
    jd_text = raw_jd[:8000]
    # Guardrail: Phase 2 — cache key includes prompt version for auto-invalidation
    cache_key = hashlib.md5(f"{jd_text}:{_PROMPT_VERSION}".encode()).hexdigest()
    if cache_key in _jd_cache:
        return {"jd_analysis": _jd_cache[cache_key]}

    # Guardrail Tier 4: Token budget check
    if _GUARDRAIL_TOKEN_BUDGET and tenant_id:
        budget_mgr = get_token_budget_manager()
        has_budget, budget_info = await budget_mgr.check_budget(tenant_id, estimate_tokens(jd_text + _JD_PARSER_PROMPT))
        if not has_budget:
            emit_guardrail_event("token_budget_exceeded", tenant_id=tenant_id, metadata=budget_info)
            return {"jd_analysis": fallback, "errors": [f"jd_parser: token budget exceeded for tenant {tenant_id}"]}

    # Guardrail: Phase 4 — circuit breaker: if hallucination rate is high, use rule-based fallback
    now = datetime.now().timestamp()
    if now - _hallucination_counter["last_reset"] > 3600:
        _hallucination_counter["count"] = 0
        _hallucination_counter["last_reset"] = now

    use_llm = _hallucination_counter["count"] < _CIRCUIT_BREAKER_THRESHOLD

    # Guardrail Tier 3: A/B test tracking
    ab_tracker = get_ab_test_tracker()
    variant_id = "jd_parser_v1"
    prompt_hash = hashlib.md5(_JD_PARSER_PROMPT.encode()).hexdigest()[:8]
    start_time = datetime.now().timestamp()

    try:
        if use_llm:
            prompt = _JD_PARSER_PROMPT.format(jd_text=jd_text)

            if _GUARDRAIL_ENSEMBLE_ENABLED:
                # Guardrail Tier 2: 3x voting ensemble
                result = await ensemble_vote_3x(
                    llm_factory=lambda s: get_fast_llm(seed=s),
                    prompt=prompt,
                    parse_fn=lambda content: _sanitize_jd_output(
                        _parse_json(content, fallback), raw_jd
                    ),
                    vote_fn=vote_jd_parser,
                )
            else:
                # Guardrail Tier 1: Retry with exponential backoff
                llm = get_fast_llm()
                resp = await llm_invoke_with_retry(llm.ainvoke, prompt)
                raw_result = _parse_json(resp.content, fallback)
                # Guardrail: sanitize output — remove hallucinated skills, normalize enums
                result = _sanitize_jd_output(raw_result, raw_jd)

                # Guardrail: Phase 4 — detect hallucination and increment circuit breaker counter
                raw_skills = raw_result.get("required_skills", []) if isinstance(raw_result, dict) else []
                validated_skills = result.get("required_skills", [])
                if len(raw_skills) > len(validated_skills):
                    _hallucination_counter["count"] += 1
                    emit_guardrail_event(
                        "hallucination_detected",
                        tenant_id=tenant_id,
                        metadata={"raw_count": len(raw_skills), "validated_count": len(validated_skills)},
                    )

            # Guardrail Tier 1: Strict schema validation
            validation = validate_jd_output(result)
            if not validation.is_valid:
                emit_guardrail_event(
                    "schema_validation_failed",
                    tenant_id=tenant_id,
                    metadata={"node": "jd_parser", "errors": validation.errors},
                )
            result = validation.data

            # Guardrail Tier 4: Record token consumption
            if _GUARDRAIL_TOKEN_BUDGET and tenant_id:
                await budget_mgr.consume_tokens(tenant_id, estimate_tokens(prompt) + estimate_tokens(json.dumps(result)))

            # Guardrail Tier 3: A/B test record
            latency_ms = (datetime.now().timestamp() - start_time) * 1000
            await ab_tracker.record(variant_id, prompt_hash, success=True, latency_ms=latency_ms)
        else:
            # Circuit breaker triggered — fallback to rule-based JD parser
            from app.backend.services.hybrid_pipeline import parse_jd_rules
            result = parse_jd_rules(raw_jd)
            # Normalize to match LLM output schema
            result = _sanitize_jd_output(result, raw_jd)
            emit_guardrail_event("circuit_breaker_triggered", tenant_id=tenant_id, metadata={"node": "jd_parser"})

        _jd_cache[cache_key] = result
        return {"jd_analysis": result}
    except Exception as exc:
        # Guardrail Tier 3: A/B test record failure
        latency_ms = (datetime.now().timestamp() - start_time) * 1000
        await ab_tracker.record(variant_id, prompt_hash, success=False, latency_ms=latency_ms)
        emit_guardrail_event("llm_fallback", tenant_id=tenant_id, metadata={"node": "jd_parser", "error": str(exc)})
        return {"jd_analysis": fallback, "errors": [f"jd_parser: {exc}"]}


# ─── Step 2: Combined Resume Analyser ─────────────────────────────────────────
# Replaces resume_parser + skill_domain + edu_timeline (3 calls → 1 call).
# On a CPU VPS, parallel calls share cores — sequential + combined is faster.

_RESUME_ANALYSER_PROMPT = """\
Parse the candidate resume and assess fit against job requirements in one pass.
Use canonical skill names (e.g. "Machine Learning" not "ML").
Output ONLY valid JSON. No markdown.

BIAS MITIGATION RULES:
1. Do NOT penalize candidates for employment gaps due to parenting, medical leave, or education.
2. Do NOT assume seniority from age or years alone — evaluate actual scope of work.
3. Score education based on RELEVANCE to the role, not prestige of institution.
4. matched_skills must ONLY include skills genuinely present in the resume from the REQUIRED SKILLS list.
5. missing_skills must ONLY include skills from the REQUIRED SKILLS list genuinely absent in the resume.
6. Do NOT invent skills that are not in either the resume or the required skills list.

JOB: role={role_title} domain={domain} seniority={seniority}
REQUIRED SKILLS: {required_skills}
RESUME:
{resume_text}
EMPLOYMENT TIMELINE: {timeline}

OUTPUT SCHEMA (all scores 0-100):
{{
  "name": null,
  "skills_identified": [],
  "education": {{"degree": null, "field": null, "institution": null, "gpa_or_distinction": null}},
  "career_summary": "",
  "total_effective_years": 0.0,
  "current_role": null,
  "current_company": null,
  "matched_skills": [],
  "missing_skills": [],
  "adjacent_skills": [],
  "skill_score": 0,
  "domain_fit_score": 0,
  "architecture_score": 0,
  "domain_fit_comment": "",
  "architecture_comment": "",
  "education_score": 0,
  "education_analysis": "",
  "field_alignment": "aligned|partially_aligned|unrelated",
  "timeline_score": 0,
  "timeline_analysis": "",
  "gap_interpretation": ""
}}

skill_score=% required skills matched semantically; domain_fit_score=domain alignment;
architecture_score=system design evidence; education_score=degree level AND field relevance to {domain};
timeline_score=career stability and upward progression."""


_RESUME_ANALYSER_CP_KEYS = {
    "name", "skills_identified", "education", "career_summary",
    "total_effective_years", "current_role", "current_company",
}
_RESUME_ANALYSER_SA_KEYS = {
    "matched_skills", "missing_skills", "adjacent_skills",
    "skill_score", "domain_fit_score", "architecture_score",
    "domain_fit_comment", "architecture_comment",
}
_RESUME_ANALYSER_ETA_KEYS = {
    "education_score", "education_analysis", "field_alignment",
    "timeline_score", "timeline_analysis", "gap_interpretation",
}


def _split_resume_analyser(data: dict, required_skills: list) -> dict:
    """Distribute the flat combined output into the three expected state sub-dicts."""
    cp  = {k: data.get(k) for k in _RESUME_ANALYSER_CP_KEYS}
    sa  = {k: data.get(k) for k in _RESUME_ANALYSER_SA_KEYS}
    eta = {k: data.get(k) for k in _RESUME_ANALYSER_ETA_KEYS}

    # Apply defaults — use explicit None checks so that keys present-but-null are fixed.
    if cp.get("total_effective_years") is None:
        cp["total_effective_years"] = 0.0
    if not cp.get("skills_identified"):
        cp["skills_identified"] = []
    if not cp.get("education"):
        cp["education"] = {}
    if not sa.get("matched_skills"):
        sa["matched_skills"] = []
    if not sa.get("missing_skills"):
        sa["missing_skills"] = required_skills[:8]
    if not sa.get("adjacent_skills"):
        sa["adjacent_skills"] = []
    if sa.get("skill_score") is None:
        sa["skill_score"] = 0
    if sa.get("domain_fit_score") is None:
        sa["domain_fit_score"] = 50
    if sa.get("architecture_score") is None:
        sa["architecture_score"] = 50
    sa.setdefault("domain_fit_comment", "")
    sa.setdefault("architecture_comment", "")
    if eta.get("education_score") is None:
        eta["education_score"] = 60
    if eta.get("timeline_score") is None:
        eta["timeline_score"] = 70
    eta.setdefault("field_alignment", "partially_aligned")
    eta.setdefault("education_analysis", "")
    eta.setdefault("timeline_analysis", "")
    eta.setdefault("gap_interpretation", "")
    return {"candidate_profile": cp, "skill_analysis": sa, "edu_timeline_analysis": eta}


async def resume_analyser_node(state: PipelineState) -> dict:
    jd             = state.get("jd_analysis", {})
    required_skills = jd.get("required_skills", [])
    _cp_fb = {
        "name": None, "skills_identified": [],
        "education": {"degree": None, "field": None, "institution": None, "gpa_or_distinction": None},
        "career_summary": "Unable to parse resume.",
        "total_effective_years": 0.0, "current_role": None, "current_company": None,
    }
    _sa_fb = {
        "matched_skills": [], "missing_skills": required_skills[:8],
        "adjacent_skills": [], "skill_score": 0,
        "domain_fit_score": 50, "architecture_score": 50,
        "domain_fit_comment": "Domain fit could not be assessed.",
        "architecture_comment": "Architecture skills could not be assessed.",
    }
    _eta_fb = {
        "education_score": 60, "education_analysis": "Education could not be assessed.",
        "field_alignment": "partially_aligned",
        "timeline_score": 70, "timeline_analysis": "Timeline could not be assessed.",
        "gap_interpretation": "No significant gap pattern detected.",
    }
    # Guardrail: Phase 3 — PII redaction to eliminate bias from names, emails, phones
    raw_resume = state["raw_resume_text"]
    try:
        from app.backend.services.pii_redaction_service import get_pii_service
        pii_service = get_pii_service()
        redaction_result = pii_service.redact_pii(raw_resume)
        resume_text = redaction_result.redacted_text
    except Exception:
        resume_text = raw_resume  # fallback to raw text if redaction fails

    tenant_id = state.get("tenant_id")

    try:
        prompt = _RESUME_ANALYSER_PROMPT.format(
            role_title=jd.get("role_title", ""),
            domain=jd.get("domain", "other"),
            seniority=jd.get("seniority", "mid"),
            required_skills=json.dumps(required_skills[:20], default=_json_default),
            # Guardrail: increased truncation to capture full resume context
            resume_text=resume_text[:8000],
            timeline=json.dumps(state.get("employment_timeline", [])[:10], default=_json_default),
        )

        # Guardrail Tier 1: Retry with exponential backoff
        llm = get_fast_llm()
        resp = await llm_invoke_with_retry(llm.ainvoke, prompt)
        data = _parse_json(resp.content, {**_cp_fb, **_sa_fb, **_eta_fb})

        # Guardrail Tier 1: Strict schema validation
        validation = validate_resume_output(data)
        if not validation.is_valid:
            emit_guardrail_event(
                "schema_validation_failed",
                tenant_id=tenant_id,
                metadata={"node": "resume_analyser", "errors": validation.errors},
            )
        data = validation.data

        # Guardrail Tier 4: Record token consumption
        if _GUARDRAIL_TOKEN_BUDGET and tenant_id:
            budget_mgr = get_token_budget_manager()
            await budget_mgr.consume_tokens(tenant_id, estimate_tokens(prompt) + estimate_tokens(json.dumps(data)))

        return _split_resume_analyser(data, required_skills)
    except Exception as exc:
        emit_guardrail_event("llm_fallback", tenant_id=tenant_id, metadata={"node": "resume_analyser", "error": str(exc)})
        return {
            "candidate_profile":     _cp_fb,
            "skill_analysis":        _sa_fb,
            "edu_timeline_analysis": _eta_fb,
            "errors": [f"resume_analyser: {exc}"],
        }


# ─── Step 3: Combined Scorer ───────────────────────────────────────────────────
# Replaces scorer_explainer + interview_qs (2 calls → 1 call).

_SCORER_PROMPT = """\
Score a candidate and generate a targeted interview kit tightly aligned with both the job description and the candidate's resume. Output ONLY valid JSON. No markdown.

ROLE CONTEXT:
Title: {role_title} | Domain: {domain} | Seniority: {seniority}
Key Responsibilities: {key_responsibilities}
Required Skills: {required_skills}
Nice-to-Have Skills: {nice_to_have_skills}

CANDIDATE CONTEXT:
Current Role: {current_role} at {current_company}
Career Summary: {career_summary}
Years Experience: {years_actual}y (role requires: {years_required}y)
Matched Skills: {matched_skills}
Missing Skills: {missing_skills}
Adjacent Skills: {adjacent_skills}
Architecture Assessment: {architecture_comment}
Domain Fit Assessment: {domain_fit_comment}
Timeline/Gap Assessment: {gap_interpretation}

SCORES & WEIGHTS:
skill={skill_score} domain_fit={domain_fit_score} arch={architecture_score} edu={education_score} timeline={timeline_score}
weights: skills={w_skills} exp={w_experience} arch={w_architecture} edu={w_education} tl={w_timeline} domain={w_domain} risk={w_risk}

Additional Context: {education_analysis} | {timeline_analysis}

OUTPUT SCHEMA:
{{
  "experience_score": 0,
  "risk_penalty": 0,
  "score_breakdown": {{"skill_match":0,"experience_match":0,"architecture":0,"education":0,"timeline":0,"domain_fit":0,"risk_penalty":0}},
  "fit_score": 0,
  "risk_level": "Low|Medium|High",
  "risk_signals": [{{"type":"gap|skill_gap|domain_mismatch|stability|education|overqualified","severity":"low|medium|high","description":""}}],
  "strengths": [],
  "weaknesses": [],
  "explainability": {{"skill_rationale":"","experience_rationale":"","education_rationale":"","timeline_rationale":"","overall_rationale":""}},
  "final_recommendation": "Shortlist|Consider|Reject",
  "recommendation_rationale": "",
  "interview_questions": {{
    "technical_questions": [],
    "behavioral_questions": [],
    "culture_fit_questions": []
  }}
}}

SCORING RULES:
experience_score: required=0→min(100,actual*10); actual>=required→min(100,70+(actual-required)*5); else→(actual/required)*70
risk_penalty: 0-100 based on missing critical skills, gaps, domain mismatch
fit_score=round(skill*{w_skills}+exp*{w_experience}+arch*{w_architecture}+edu*{w_education}+tl*{w_timeline}+domain*{w_domain}-risk*{w_risk}), clamp 0-100
risk_level: >=72→Low, >=45→Medium, else→High; recommendation: >=72→Shortlist, >=45→Consider, else→Reject

INTERVIEW KIT RULES — generate highly targeted, non-generic questions:
1. TECHNICAL QUESTIONS (5 questions):
   a) For EACH missing skill: Create a scenario-based question that ties the skill to a specific job responsibility from the Key Responsibilities list. Do NOT ask "Do you know X?" — instead ask how they would solve a real problem using that skill in this role.
   b) For 1-2 critical matched skills: Create a depth-probing question that tests expertise level. Reference their current role ({current_role}) vs. the role requirements.
   c) If architecture_comment mentions system design gaps or the role requires architecture decisions: Include a system design question relevant to the domain.
   d) Use the domain ({domain}) and seniority ({seniority}) to calibrate difficulty.

2. BEHAVIORAL QUESTIONS (3 questions, STAR format):
   a) Address the biggest risk signal from the gap/timeline assessment: {gap_interpretation}. If gaps exist, ask about the circumstance without being invasive.
   b) Target a seniority-specific challenge: for senior roles probe leadership/mentorship; for mid roles probe ownership; for junior roles probe learning agility.
   c) Probe the role transition: moving from {current_role} to {role_title} — what motivates this and what challenges do they anticipate?

3. CULTURE-FIT QUESTIONS (2 questions):
   a) Motivation for THIS specific role: Why this company/role given their career trajectory ({career_summary})?
   b) Work-style alignment: A question tied to the role context (e.g., fast-paced startup vs. structured enterprise, remote vs. on-site if implied by domain).

DO NOT generate generic questions like "Tell me about yourself", "What are your strengths?", or "Where do you see yourself in 5 years?". Every question MUST reference specific skills, role responsibilities, or candidate resume context provided above."""


async def scorer_node(state: PipelineState) -> dict:
    from app.backend.services.weight_mapper import convert_to_new_schema
    from app.backend.services.resume_calibration_service import (
        get_role_calibration,
        get_similar_analyses,
        format_calibration_context,
        format_similar_analyses_context
    )
    
    sa  = state.get("skill_analysis", {})
    eta = state.get("edu_timeline_analysis", {})
    cp  = state.get("candidate_profile", {})
    jd  = state.get("jd_analysis", {})
    
    # Convert incoming weights to new schema, then map to old internal keys
    new_weights = convert_to_new_schema(state.get("scoring_weights"))
    w = {
        "skills":       new_weights.get("core_competencies", 0.30),
        "experience":   new_weights.get("experience", 0.20),
        "architecture": new_weights.get("role_excellence", 0.15),
        "education":    new_weights.get("education", 0.10),
        "timeline":     new_weights.get("career_trajectory", 0.10),
        "domain":       new_weights.get("domain_fit", 0.10),
        "risk":         new_weights.get("risk", 0.15),
    }
    w = _normalize_weights(w)
    
    # Get calibration context for RAG learning (if db session and tenant_id available)
    calibration_context = ""
    similar_context = ""
    try:
        db_session = state.get("db_session")
        tenant_id = state.get("tenant_id")
        role_category = state.get("role_category", "general")
        jd_text = state.get("job_description", "")
        
        if db_session and tenant_id:
            # Get calibration data
            calibration = get_role_calibration(role_category, tenant_id, db_session)
            calibration_context = format_calibration_context(calibration)
            
            # Get similar analyses
            similar_analyses = get_similar_analyses(jd_text, role_category, tenant_id, db_session, limit=3)
            similar_context = format_similar_analyses_context(similar_analyses)
    except Exception as e:
        # Calibration is optional - don't fail if it errors
        logger.debug(f"Calibration context unavailable: {e}")

    missing_skills = sa.get("missing_skills", [])
    role_title = jd.get("role_title", "this role")
    domain = jd.get("domain", "the domain")
    seniority = jd.get("seniority", "mid")
    key_responsibilities = jd.get("key_responsibilities", [])
    current_role = cp.get("current_role") or "their current role"
    current_company = cp.get("current_company") or "their current company"
    career_summary = cp.get("career_summary", "")
    matched = sa.get("matched_skills", [])
    adjacent = sa.get("adjacent_skills", [])
    arch_comment = sa.get("architecture_comment", "")
    gap_interp = eta.get("gap_interpretation", "")

    # Context-aware fallback technical questions
    tech_qs = []
    for skill in missing_skills[:3]:
        resp = key_responsibilities[0] if key_responsibilities else "the role's core work"
        tech_qs.append(
            f"This role involves {resp}. Walk me through how you would approach a challenge requiring {skill} — what tools, patterns, or experience would you draw on?"
        )
    if not tech_qs:
        tech_qs = [f"Describe a complex technical problem you solved in {domain} that is relevant to {role_title}."]
    if matched:
        tech_qs.append(
            f"You have experience with {matched[0]}. Tell me about a time you had to push the limits of that technology — what was the hardest problem you solved with it?"
        )
    if adjacent:
        tech_qs.append(
            f"You have adjacent experience with {adjacent[0]}. How would you leverage that background to ramp up quickly on the core stack for {role_title}?"
        )
    if "architecture" in arch_comment.lower() or "system design" in arch_comment.lower() or "design" in arch_comment.lower():
        tech_qs.append(
            f"For {role_title}, we'd need to make architectural decisions in {domain}. Describe a system you designed or significantly improved — what trade-offs did you make?"
        )
    tech_qs = tech_qs[:5]
    if len(tech_qs) < 3:
        tech_qs.append(f"How do you stay current with developments in {domain}? Give a recent example of applying a new technique or tool.")

    # Context-aware fallback behavioral questions
    beh_qs = []
    if gap_interp and ("gap" in gap_interp.lower() or "unemployed" in gap_interp.lower() or "break" in gap_interp.lower()):
        beh_qs.append(
            "Your timeline shows a career transition period. Can you walk me through what drove that change and what you focused on during that time?"
        )
    else:
        beh_qs.append(
            f"You're currently at {current_company} as a {current_role}. What would make this {role_title} opportunity the right next step for you?"
        )
    beh_qs.extend([
        f"Tell me about a time you had to deliver results in {domain} under significant constraint — tight deadline, limited resources, or unclear requirements. What was your approach?",
        f"Describe a situation where you had to influence a decision or mentor someone in a {domain} context. What was the outcome?",
    ])

    # Context-aware fallback culture-fit questions
    cult_qs = [
        f"Given your background in {domain}, what type of work environment brings out your best performance — structured processes or autonomous ownership?",
        f"What specifically attracted you to {role_title}, and how does it align with the direction you see your career heading?",
    ]

    fallback_iq = {
        "technical_questions": tech_qs,
        "behavioral_questions": beh_qs,
        "culture_fit_questions": cult_qs,
    }
    fallback_scores = _compute_fallback_scores(sa, eta, cp, jd, w)

    tenant_id = state.get("tenant_id")

    try:
        # Build enhanced prompt with calibration context
        base_prompt = _SCORER_PROMPT.format(
            role_title=jd.get("role_title", ""),
            domain=jd.get("domain", "other"),
            seniority=jd.get("seniority", "mid"),
            key_responsibilities=json.dumps(jd.get("key_responsibilities", [])[:5], default=_json_default),
            required_skills=json.dumps(jd.get("required_skills", [])[:8], default=_json_default),
            nice_to_have_skills=json.dumps(jd.get("nice_to_have_skills", [])[:5], default=_json_default),
            current_role=cp.get("current_role") or "Unknown",
            current_company=cp.get("current_company") or "Unknown",
            career_summary=_truncate(cp.get("career_summary", ""), 300),
            skill_score=sa.get("skill_score", 0),
            domain_fit_score=sa.get("domain_fit_score", 50),
            architecture_score=sa.get("architecture_score", 50),
            education_score=eta.get("education_score", 60),
            timeline_score=eta.get("timeline_score", 70),
            years_actual=cp.get("total_effective_years", 0),
            years_required=jd.get("required_years", 0),
            matched_skills=json.dumps(sa.get("matched_skills", [])[:8], default=_json_default),
            missing_skills=json.dumps(missing_skills[:8], default=_json_default),
            adjacent_skills=json.dumps(sa.get("adjacent_skills", [])[:5], default=_json_default),
            architecture_comment=sa.get("architecture_comment", ""),
            domain_fit_comment=sa.get("domain_fit_comment", ""),
            education_analysis=eta.get("education_analysis", ""),
            timeline_analysis=eta.get("timeline_analysis", ""),
            gap_interpretation=eta.get("gap_interpretation", ""),
            w_skills=w["skills"], w_experience=w["experience"],
            w_architecture=w["architecture"], w_education=w["education"],
            w_timeline=w["timeline"], w_domain=w["domain"], w_risk=w["risk"],
        )

        # Inject calibration context if available
        if calibration_context or similar_context:
            enhanced_prompt = f"""{calibration_context}{similar_context}

Now analyze this candidate using similar reasoning and maintain consistency with past decisions.

{base_prompt}"""
            prompt = enhanced_prompt
        else:
            prompt = base_prompt

        if _GUARDRAIL_ENSEMBLE_ENABLED:
            # Guardrail Tier 2: 3x voting ensemble for critical scorer node
            result = await ensemble_vote_3x(
                llm_factory=lambda s: get_reasoning_llm(seed=s),
                prompt=prompt,
                parse_fn=lambda content: _parse_json(content, {**fallback_scores, "interview_questions": fallback_iq}),
                vote_fn=vote_scorer,
            )
            iq = result.pop("interview_questions", fallback_iq)
            if not isinstance(iq, dict):
                iq = fallback_iq
        else:
            # Guardrail Tier 1: Retry with exponential backoff
            llm = get_reasoning_llm()
            resp = await llm_invoke_with_retry(llm.ainvoke, prompt)
            result = _parse_json(resp.content, {**fallback_scores, "interview_questions": fallback_iq})

            # Extract interview_questions sub-dict from the combined output
            iq = result.pop("interview_questions", fallback_iq)
            if not isinstance(iq, dict):
                iq = fallback_iq

        # Guardrail Tier 1: Strict schema validation
        validation = validate_scorer_output(result)
        if not validation.is_valid:
            emit_guardrail_event(
                "schema_validation_failed",
                tenant_id=tenant_id,
                metadata={"node": "scorer", "errors": validation.errors},
            )
        result = validation.data

        # Sanitise fit_score and recommendation
        result["fit_score"] = max(0, min(100, int(result.get("fit_score", 50))))
        if result.get("final_recommendation") not in ("Shortlist", "Consider", "Reject"):
            fit = result["fit_score"]
            result["final_recommendation"] = (
                "Shortlist" if fit >= RECOMMENDATION_THRESHOLDS["shortlist"] else "Consider" if fit >= RECOMMENDATION_THRESHOLDS["consider"] else "Reject"
            )

        # Always override score_breakdown with actual agent-computed input scores.
        # LLMs frequently output the schema template literal (0) for these fields.
        sb = result.setdefault("score_breakdown", {})
        sb["skill_match"]      = sa.get("skill_score", 0)
        sb["architecture"]     = sa.get("architecture_score", 0)
        sb["domain_fit"]       = sa.get("domain_fit_score", 0)
        sb["education"]        = eta.get("education_score", 0)
        sb["timeline"]         = eta.get("timeline_score", 0)
        sb["experience_match"] = max(0, min(100, int(
            result.get("experience_score", sb.get("experience_match", 0))
        )))
        result["score_breakdown"] = sb

        # Guardrail Tier 4: Record token consumption
        if _GUARDRAIL_TOKEN_BUDGET and tenant_id:
            budget_mgr = get_token_budget_manager()
            await budget_mgr.consume_tokens(tenant_id, estimate_tokens(prompt) + estimate_tokens(json.dumps(result)))

        return {"final_scores": result, "interview_questions": iq}
    except Exception as exc:
        emit_guardrail_event("llm_fallback", tenant_id=tenant_id, metadata={"node": "scorer", "error": str(exc)})
        return {
            "final_scores":        fallback_scores,
            "interview_questions": fallback_iq,
            "errors": [f"scorer: {exc}"],
        }


# ─── Weight utilities ──────────────────────────────────────────────────────────

def _normalize_weights(w: Dict[str, float]) -> Dict[str, float]:
    """Normalize weights to sum to 1.0, keeping all keys from DEFAULT_WEIGHTS."""
    for key in DEFAULT_WEIGHTS:
        w.setdefault(key, DEFAULT_WEIGHTS[key])
    total = sum(w.values())
    if total > 0:
        return {k: round(v / total, 4) for k, v in w.items()}
    return dict(DEFAULT_WEIGHTS)


def _compute_fallback_scores(
    sa: dict, eta: dict, cp: dict, jd: dict, w: dict
) -> dict:
    """Pure-math fallback when scorer_explainer LLM call fails."""
    skill_score    = int(sa.get("skill_score", 0))
    domain_score   = int(sa.get("domain_fit_score", 50))
    arch_score     = int(sa.get("architecture_score", 50))
    edu_score      = int(eta.get("education_score", 60))
    timeline_score = int(eta.get("timeline_score", 70))

    actual   = float(cp.get("total_effective_years", 0))
    required = float(jd.get("required_years", 0))
    if required == 0:
        exp_score = min(100, int(actual * 10))
    elif actual >= required:
        exp_score = min(100, 70 + int((actual - required) * 5))
    else:
        exp_score = int((actual / required) * 70)

    risk_penalty = compute_risk_penalty([])

    scores = {
        "skill_score":    skill_score,
        "exp_score":      exp_score,
        "arch_score":     arch_score,
        "edu_score":      edu_score,
        "timeline_score": timeline_score,
        "domain_score":   domain_score,
    }
    fit_result = compute_fit_score(scores, w, risk_signals=[])
    fit = fit_result["fit_score"]
    rec = fit_result["final_recommendation"]

    return {
        "experience_score": exp_score,
        "risk_penalty":     risk_penalty,
        "score_breakdown":  fit_result["score_breakdown"],
        "fit_score":        fit,
        "risk_level":       fit_result["risk_level"],
        "risk_signals":     [],
        "strengths":        [],
        "weaknesses":       [],
        "explainability": {
            "overall_rationale": "Automated scoring unavailable — LLM analysis pending."
        },
        "final_recommendation":    rec,
        "recommendation_rationale": f"Computed score {fit}/100 — {rec}.",
    }


# ─── Graph construction (compiled once at module load) ─────────────────────────

def _build_pipeline():
    graph = StateGraph(PipelineState)

    # 3 sequential nodes — each uses full CPU cores rather than sharing across parallel calls.
    # On CPU inference parallel ≈ sequential for wall-clock time, but serial allows
    # each model invocation to use all available threads, reducing per-call latency.
    graph.add_node("jd_parser",       jd_parser_node)
    graph.add_node("resume_analyser", resume_analyser_node)  # replaces resume_parser+skill_domain+edu_timeline
    graph.add_node("scorer",          scorer_node)            # replaces scorer_explainer+interview_qs

    graph.add_edge(START,             "jd_parser")
    graph.add_edge("jd_parser",       "resume_analyser")
    graph.add_edge("resume_analyser", "scorer")
    graph.add_edge("scorer",          END)

    return graph.compile()


pipeline = _build_pipeline()


# ─── State builder & result assembler ─────────────────────────────────────────

def build_initial_state(
    resume_text:    str,
    job_description: str,
    gap_analysis:   dict,
    scoring_weights: Optional[Dict[str, float]] = None,
    tenant_id: Optional[int] = None,
) -> dict:
    return {
        "raw_jd_text":          job_description,
        "raw_resume_text":      resume_text,
        "employment_timeline":  gap_analysis.get("employment_timeline", []),
        "scoring_weights":      scoring_weights or DEFAULT_WEIGHTS,
        "tenant_id":            tenant_id,
        "jd_analysis":          {},
        "candidate_profile":    {},
        "skill_analysis":       {},
        "edu_timeline_analysis": {},
        "final_scores":         {},
        "interview_questions":  {},
        "errors":               [],
    }


def assemble_result(
    state:       dict,
    parsed_data: dict,
    gap_analysis: dict,
) -> dict:
    """
    Assemble the final result dict from completed pipeline state.
    Maintains full backward compatibility with existing AnalysisResponse schema
    while adding all new LangGraph-produced fields.

    Guardrail Tier 1: Cross-node consistency checks are applied here.
    Guardrail Tier 3: HITL flags are generated for low-confidence results.
    """
    fs  = state.get("final_scores", {})
    sa  = state.get("skill_analysis", {})
    eta = state.get("edu_timeline_analysis", {})
    iq  = state.get("interview_questions", {})
    cp  = state.get("candidate_profile", {})
    jd  = state.get("jd_analysis", {})
    tenant_id = state.get("tenant_id")

    # Guardrail Tier 1: Cross-node consistency check
    consistency_report = check_cross_node_consistency(jd, sa, fs)
    if not consistency_report.is_consistent:
        emit_guardrail_event(
            "inconsistency_fixed",
            tenant_id=tenant_id,
            metadata={"violations": consistency_report.violations, "fixes": consistency_report.fixes_applied},
        )

    # Guardrail Tier 3: HITL gate check
    hitl_flags = hitl_gate_check(
        jd_analysis=jd,
        skill_analysis=sa,
        final_scores=fs,
        consistency_report=consistency_report,
        raw_jd_text=state.get("raw_jd_text", ""),
    )
    if hitl_flags:
        emit_guardrail_event(
            "hitl_flag_generated",
            tenant_id=tenant_id,
            metadata={"flags": [{"type": f.flag_type, "severity": f.severity, "message": f.message} for f in hitl_flags]},
        )

    score_bd = fs.get("score_breakdown", {})
    # Map timeline → stability for backward compat (frontend still renders "Stability" bar)
    score_bd_compat = dict(score_bd)
    score_bd_compat.setdefault("stability", score_bd.get("timeline", 0))
    score_bd_compat.setdefault("skill_match", score_bd.get("skill_match", 0))
    score_bd_compat.setdefault("experience_match", score_bd.get("experience_match", 0))
    score_bd_compat.setdefault("education", score_bd.get("education", 0))

    return {
        # ── Backward-compatible core fields ──
        "fit_score":             fs.get("fit_score", 0),
        "job_role":              jd.get("role_title", ""),  # for ReportPage role display
        "strengths":             fs.get("strengths", []),
        "weaknesses":            fs.get("weaknesses", []),
        "employment_gaps":       gap_analysis.get("employment_gaps", []),
        "education_analysis":    eta.get("education_analysis", ""),
        "risk_signals":          fs.get("risk_signals", []),
        "final_recommendation":  fs.get("final_recommendation", "Consider"),
        "score_breakdown":       score_bd_compat,
        "matched_skills":        sa.get("matched_skills", []),
        "missing_skills":        sa.get("missing_skills", []),
        "risk_level":            fs.get("risk_level", "Medium"),
        "interview_questions":   iq,
        "required_skills_count": len(jd.get("required_skills", [])),
        "work_experience":       parsed_data.get("work_experience", []),
        "contact_info":          parsed_data.get("contact_info", {}),
        # ── New fields from LangGraph pipeline ──
        "jd_analysis":           jd,
        "candidate_profile":     cp,
        "skill_analysis":        sa,
        "edu_timeline_analysis": eta,
        "explainability":        fs.get("explainability", {}),
        "recommendation_rationale": fs.get("recommendation_rationale", ""),
        "adjacent_skills":       sa.get("adjacent_skills", []),
        "pipeline_errors":       state.get("errors", []),
        # ── Guardrail outputs ──
        "guardrail_consistency_report": {
            "is_consistent": consistency_report.is_consistent,
            "violations": consistency_report.violations,
            "fixes_applied": consistency_report.fixes_applied,
        },
        "guardrail_hitl_flags": [
            {"flag_type": f.flag_type, "severity": f.severity, "message": f.message, "metadata": f.metadata}
            for f in hitl_flags
        ],
    }


# ─── Public API (non-streaming, for batch + backward compat) ──────────────────

async def run_agent_pipeline(
    resume_text:     str,
    job_description: str,
    parsed_data:     dict,
    gap_analysis:    dict,
    scoring_weights: Optional[Dict[str, float]] = None,
    db_session:      Optional[Any] = None,
    tenant_id:       Optional[int] = None,
    role_category:   Optional[str] = None,
) -> dict:
    """
    Run the full pipeline and return the assembled result dict (non-streaming).
    
    Args:
        db_session: Database session for calibration (optional)
        tenant_id: Tenant ID for calibration (optional)
        role_category: Role category for calibration (optional)
    """
    state = build_initial_state(resume_text, job_description, gap_analysis, scoring_weights, tenant_id)

    # Add calibration context to state if available
    if db_session:
        state["db_session"] = db_session
    if role_category:
        state["role_category"] = role_category

    final_state = await pipeline.ainvoke(state)
    return assemble_result(final_state, parsed_data, gap_analysis)
