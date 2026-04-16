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

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama


def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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

DEFAULT_WEIGHTS: Dict[str, float] = {
    "skills":       0.30,
    "experience":   0.20,
    "architecture": 0.15,
    "education":    0.10,
    "timeline":     0.10,
    "domain":       0.10,
    "risk":         0.15,
}

# Nodes that emit SSE events when complete (3-step sequential pipeline)
STREAMABLE_NODES = {"jd_parser", "resume_analyser", "scorer"}


# ─── LLM singletons (created once, reused across all requests) ─────────────────
# Creating a new ChatOllama per call adds connection overhead and prevents Ollama
# from reusing its internal HTTP keep-alive sessions.

_fast_llm: Optional[ChatOllama] = None
_reasoning_llm: Optional[ChatOllama] = None

# In-memory JD cache: MD5(jd_text[:2000]) → parsed jd_analysis dict.
# For batch screening (same JD, many resumes) this skips the jd_parser LLM call
# entirely after the first request, saving ~3–8 seconds per candidate.
_jd_cache: Dict[str, dict] = {}


_llm_request_timeout = float(os.getenv("LLM_NARRATIVE_TIMEOUT", "150")) + 30


def get_fast_llm() -> ChatOllama:
    """Fast model for jd_parser + resume_analyser. Singleton — never re-initialised."""
    global _fast_llm
    if _fast_llm is None:
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


def get_reasoning_llm() -> ChatOllama:
    """Reasoning model for combined scorer + interview questions. Singleton."""
    global _reasoning_llm
    if _reasoning_llm is None:
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


# ─── Stage 1: JD Parser ────────────────────────────────────────────────────────

_JD_PARSER_PROMPT = """\
Extract job requirements. Output ONLY valid JSON. No markdown.

JOB DESCRIPTION:
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


async def jd_parser_node(state: PipelineState) -> dict:
    fallback = {
        "role_title": "", "domain": "other", "seniority": "mid",
        "required_skills": [], "required_years": 0,
        "nice_to_have_skills": [], "key_responsibilities": [],
    }
    jd_text = state["raw_jd_text"][:2000]
    cache_key = hashlib.md5(jd_text.encode()).hexdigest()
    if cache_key in _jd_cache:
        return {"jd_analysis": _jd_cache[cache_key]}
    try:
        llm    = get_fast_llm()
        prompt = _JD_PARSER_PROMPT.format(jd_text=jd_text)
        resp   = await llm.ainvoke(prompt)
        result = _parse_json(resp.content, fallback)
        _jd_cache[cache_key] = result
        return {"jd_analysis": result}
    except Exception as exc:
        return {"jd_analysis": fallback, "errors": [f"jd_parser: {exc}"]}


# ─── Step 2: Combined Resume Analyser ─────────────────────────────────────────
# Replaces resume_parser + skill_domain + edu_timeline (3 calls → 1 call).
# On a CPU VPS, parallel calls share cores — sequential + combined is faster.

_RESUME_ANALYSER_PROMPT = """\
Parse the candidate resume and assess fit against job requirements in one pass.
Use canonical skill names (e.g. "Machine Learning" not "ML").
Output ONLY valid JSON. No markdown.

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
    try:
        llm    = get_fast_llm()
        prompt = _RESUME_ANALYSER_PROMPT.format(
            role_title=jd.get("role_title", ""),
            domain=jd.get("domain", "other"),
            seniority=jd.get("seniority", "mid"),
            required_skills=json.dumps(required_skills[:20], default=_json_default),
            resume_text=state["raw_resume_text"][:3000],
            timeline=json.dumps(state.get("employment_timeline", [])[:10], default=_json_default),
        )
        resp = await llm.ainvoke(prompt)
        data = _parse_json(resp.content, {**_cp_fb, **_sa_fb, **_eta_fb})
        return _split_resume_analyser(data, required_skills)
    except Exception as exc:
        return {
            "candidate_profile":     _cp_fb,
            "skill_analysis":        _sa_fb,
            "edu_timeline_analysis": _eta_fb,
            "errors": [f"resume_analyser: {exc}"],
        }


# ─── Step 3: Combined Scorer ───────────────────────────────────────────────────
# Replaces scorer_explainer + interview_qs (2 calls → 1 call).

_SCORER_PROMPT = """\
Score a candidate and generate interview questions. Output ONLY valid JSON. No markdown.

INPUTS:
role={role_title} domain={domain}
skill={skill_score} domain_fit={domain_fit_score} arch={architecture_score} edu={education_score} timeline={timeline_score}
experience: {years_actual}y actual / {years_required}y required
matched: {matched_skills}
missing: {missing_skills}
context: {domain_fit_comment} | {education_analysis} | {timeline_analysis} | {gap_interpretation}
weights: skills={w_skills} exp={w_experience} arch={w_architecture} edu={w_education} tl={w_timeline} domain={w_domain} risk={w_risk}

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

RULES:
experience_score: required=0→min(100,actual*10); actual>=required→min(100,70+(actual-required)*5); else→(actual/required)*70
risk_penalty: 0-100 based on missing critical skills, gaps, domain mismatch
fit_score=round(skill*{w_skills}+exp*{w_experience}+arch*{w_architecture}+edu*{w_education}+tl*{w_timeline}+domain*{w_domain}-risk*{w_risk}), clamp 0-100
risk_level: >=72→Low, >=45→Medium, else→High; recommendation: >=72→Shortlist, >=45→Consider, else→Reject
interview: 5 technical (probe missing skills), 3 behavioral STAR (address gaps), 2 culture/motivation questions."""


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
    fallback_iq = {
        "technical_questions": (
            [f"Walk us through your experience with {s}?" for s in missing_skills[:3]]
            or ["Describe a challenging technical problem you solved recently."]
        ),
        "behavioral_questions": [
            "Tell me about a time you had to quickly learn a new technology.",
            "Describe handling a difficult stakeholder or team conflict.",
            "Walk me through a project where timelines slipped — how did you respond?",
        ],
        "culture_fit_questions": [
            "What motivates you most in your day-to-day work?",
            "How do you prefer to receive and act on feedback?",
        ],
    }
    fallback_scores = _compute_fallback_scores(sa, eta, cp, jd, w)

    try:
        llm    = get_reasoning_llm()
        
        # Build enhanced prompt with calibration context
        base_prompt = _SCORER_PROMPT.format(
            role_title=jd.get("role_title", ""),
            domain=jd.get("domain", "other"),
            skill_score=sa.get("skill_score", 0),
            domain_fit_score=sa.get("domain_fit_score", 50),
            architecture_score=sa.get("architecture_score", 50),
            education_score=eta.get("education_score", 60),
            timeline_score=eta.get("timeline_score", 70),
            years_actual=cp.get("total_effective_years", 0),
            years_required=jd.get("required_years", 0),
            matched_skills=json.dumps(sa.get("matched_skills", [])[:8], default=_json_default),
            missing_skills=json.dumps(missing_skills[:8], default=_json_default),
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
        resp   = await llm.ainvoke(prompt)
        result = _parse_json(resp.content, {**fallback_scores, "interview_questions": fallback_iq})

        # Extract interview_questions sub-dict from the combined output
        iq = result.pop("interview_questions", fallback_iq)
        if not isinstance(iq, dict):
            iq = fallback_iq

        # Sanitise fit_score and recommendation
        result["fit_score"] = max(0, min(100, int(result.get("fit_score", 50))))
        if result.get("final_recommendation") not in ("Shortlist", "Consider", "Reject"):
            fit = result["fit_score"]
            result["final_recommendation"] = (
                "Shortlist" if fit >= 72 else "Consider" if fit >= 45 else "Reject"
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
        return {"final_scores": result, "interview_questions": iq}
    except Exception as exc:
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

    risk_penalty = max(0, (100 - skill_score) // 3)
    fit = round(
        skill_score    * w.get("skills",       0.30) +
        exp_score      * w.get("experience",    0.20) +
        arch_score     * w.get("architecture",  0.15) +
        edu_score      * w.get("education",     0.10) +
        timeline_score * w.get("timeline",      0.10) +
        domain_score   * w.get("domain",        0.10) -
        risk_penalty   * w.get("risk",          0.15)
    )
    fit = max(0, min(100, int(fit)))
    rec = "Shortlist" if fit >= 72 else "Consider" if fit >= 45 else "Reject"

    return {
        "experience_score": exp_score,
        "risk_penalty":     risk_penalty,
        "score_breakdown": {
            "skill_match":       skill_score,
            "experience_match":  exp_score,
            "architecture":      arch_score,
            "education":         edu_score,
            "timeline":          timeline_score,
            "domain_fit":        domain_score,
            "risk_penalty":      risk_penalty,
        },
        "fit_score":    fit,
        "risk_level":   "Low" if fit >= 72 else "Medium" if fit >= 45 else "High",
        "risk_signals": [],
        "strengths":    [],
        "weaknesses":   [],
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
) -> dict:
    return {
        "raw_jd_text":          job_description,
        "raw_resume_text":      resume_text,
        "employment_timeline":  gap_analysis.get("employment_timeline", []),
        "scoring_weights":      scoring_weights or DEFAULT_WEIGHTS,
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
    """
    fs  = state.get("final_scores", {})
    sa  = state.get("skill_analysis", {})
    eta = state.get("edu_timeline_analysis", {})
    iq  = state.get("interview_questions", {})
    cp  = state.get("candidate_profile", {})
    jd  = state.get("jd_analysis", {})

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
    state = build_initial_state(resume_text, job_description, gap_analysis, scoring_weights)
    
    # Add calibration context to state if available
    if db_session:
        state["db_session"] = db_session
    if tenant_id:
        state["tenant_id"] = tenant_id
    if role_category:
        state["role_category"] = role_category
    
    final_state = await pipeline.ainvoke(state)
    return assemble_result(final_state, parsed_data, gap_analysis)
