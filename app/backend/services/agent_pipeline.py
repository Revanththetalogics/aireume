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
  get_fast_llm()      → llama3.2:3b  (extraction / matching / education / interview)
  get_reasoning_llm() → llama3       (scoring / explainability — needs deeper reasoning)

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
from typing import TypedDict, Annotated, Any, Dict, List, Optional
import operator

from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama


# ─── Configuration ─────────────────────────────────────────────────────────────

OLLAMA_BASE_URL       = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_FAST_MODEL     = os.getenv("OLLAMA_FAST_MODEL", "llama3.2:3b")
OLLAMA_REASONING_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

DEFAULT_WEIGHTS: Dict[str, float] = {
    "skills":       0.30,
    "experience":   0.20,
    "architecture": 0.15,
    "education":    0.10,
    "timeline":     0.10,
    "domain":       0.10,
    "risk":         0.15,
}

# Nodes that emit SSE events when complete
STREAMABLE_NODES = {
    "jd_parser", "resume_parser",
    "skill_domain", "edu_timeline",
    "scorer_explainer", "interview_qs",
}


# ─── LLM singletons (created once, reused across all requests) ─────────────────
# Creating a new ChatOllama per call adds connection overhead and prevents Ollama
# from reusing its internal HTTP keep-alive sessions.

_fast_llm: Optional[ChatOllama] = None
_reasoning_llm: Optional[ChatOllama] = None

# In-memory JD cache: MD5(jd_text[:2000]) → parsed jd_analysis dict.
# For batch screening (same JD, many resumes) this skips the jd_parser LLM call
# entirely after the first request, saving ~3–8 seconds per candidate.
_jd_cache: Dict[str, dict] = {}


def get_fast_llm() -> ChatOllama:
    """3b model for extraction/matching agents. Singleton — never re-initialised."""
    global _fast_llm
    if _fast_llm is None:
        _fast_llm = ChatOllama(
            model=OLLAMA_FAST_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            format="json",
            num_predict=400,   # cap output tokens — JSON schemas are bounded
            num_ctx=2048,      # sufficient for prompt + resume text
            keep_alive=-1,     # keep model hot in VRAM indefinitely
        )
    return _fast_llm


def get_reasoning_llm() -> ChatOllama:
    """Full model for scorer_explainer. Singleton — never re-initialised."""
    global _reasoning_llm
    if _reasoning_llm is None:
        _reasoning_llm = ChatOllama(
            model=OLLAMA_REASONING_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            format="json",
            num_predict=550,   # scorer output is larger but still bounded
            num_ctx=2048,      # scorer input is ~500 tokens (no raw text)
            keep_alive=-1,
        )
    return _reasoning_llm


# ─── Pipeline state ─────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    # ── Inputs (set before graph runs) ──
    raw_jd_text:         str
    raw_resume_text:     str
    employment_timeline: list   # pre-computed by GapDetector (objective date math)
    scoring_weights:     dict

    # ── Stage 1 outputs ──
    jd_analysis:         dict   # from jd_parser
    candidate_profile:   dict   # from resume_parser

    # ── Stage 2 outputs ──
    skill_analysis:      dict   # from skill_domain
    edu_timeline_analysis: dict # from edu_timeline

    # ── Stage 3 outputs ──
    final_scores:        dict   # from scorer_explainer
    interview_questions: dict   # from interview_qs

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


# ─── Stage 1: Resume Parser ────────────────────────────────────────────────────

_RESUME_PARSER_PROMPT = """\
Extract candidate info from the resume. Use canonical skill names (e.g. "Machine Learning" not "ML").
Output ONLY valid JSON. No markdown.

RESUME:
{resume_text}

OUTPUT SCHEMA:
{{
  "name": null,
  "skills_identified": [],
  "education": {{
    "degree": null,
    "field": null,
    "institution": null,
    "gpa_or_distinction": null
  }},
  "career_summary": "",
  "total_effective_years": 0.0,
  "current_role": null,
  "current_company": null
}}"""


async def resume_parser_node(state: PipelineState) -> dict:
    fallback = {
        "name": None, "skills_identified": [],
        "education": {"degree": None, "field": None, "institution": None, "gpa_or_distinction": None},
        "career_summary": "Unable to parse resume.",
        "total_effective_years": 0.0, "current_role": None, "current_company": None,
    }
    try:
        llm    = get_fast_llm()
        prompt = _RESUME_PARSER_PROMPT.format(resume_text=state["raw_resume_text"][:3000])
        resp   = await llm.ainvoke(prompt)
        return {"candidate_profile": _parse_json(resp.content, fallback)}
    except Exception as exc:
        return {"candidate_profile": fallback, "errors": [f"resume_parser: {exc}"]}


# ─── Stage 2: Skill & Domain Analyzer ─────────────────────────────────────────

_SKILL_DOMAIN_PROMPT = """\
Compare candidate skills to job requirements using semantic matching (aliases/synonyms count).
Output ONLY valid JSON. No markdown.

REQUIRED SKILLS: {required_skills}
CANDIDATE SKILLS: {candidate_skills}
DOMAIN: {domain}
SENIORITY: {seniority}

OUTPUT SCHEMA (scores 0–100):
{{
  "matched_skills": [],
  "missing_skills": [],
  "adjacent_skills": [],
  "skill_score": 0,
  "domain_fit_score": 0,
  "architecture_score": 0,
  "domain_fit_comment": "",
  "architecture_comment": ""
}}

skill_score=% of required skills found; domain_fit_score=domain alignment; architecture_score=system design evidence."""


async def skill_domain_node(state: PipelineState) -> dict:
    jd = state.get("jd_analysis", {})
    cp = state.get("candidate_profile", {})
    fallback = {
        "matched_skills": [], "missing_skills": jd.get("required_skills", [])[:8],
        "adjacent_skills": [], "skill_score": 0,
        "domain_fit_score": 50, "architecture_score": 50,
        "domain_fit_comment": "Domain fit could not be assessed.",
        "architecture_comment": "Architecture skills could not be assessed.",
    }
    try:
        llm    = get_fast_llm()
        prompt = _SKILL_DOMAIN_PROMPT.format(
            required_skills=json.dumps(jd.get("required_skills", [])[:20]),
            candidate_skills=json.dumps(cp.get("skills_identified", [])[:30]),
            domain=jd.get("domain", "other"),
            seniority=jd.get("seniority", "mid"),
        )
        resp = await llm.ainvoke(prompt)
        return {"skill_analysis": _parse_json(resp.content, fallback)}
    except Exception as exc:
        return {"skill_analysis": fallback, "errors": [f"skill_domain: {exc}"]}


# ─── Stage 2: Education & Timeline Analyzer ────────────────────────────────────

_EDU_TIMELINE_PROMPT = """\
Assess education relevance and career timeline. Output ONLY valid JSON. No markdown.

DOMAIN: {domain}  SENIORITY: {seniority}
EDUCATION: {education}
TIMELINE: {timeline}

OUTPUT SCHEMA (scores 0–100):
{{
  "education_score": 0,
  "education_analysis": "",
  "field_alignment": "aligned|partially_aligned|unrelated",
  "timeline_score": 0,
  "timeline_analysis": "",
  "gap_interpretation": ""
}}

education_score: degree level AND field relevance to {domain} (PhD>Masters>Bachelor>other; relevant field > unrelated).
timeline_score: career stability, tenure length, upward progression."""


async def edu_timeline_node(state: PipelineState) -> dict:
    jd       = state.get("jd_analysis", {})
    cp       = state.get("candidate_profile", {})
    timeline = state.get("employment_timeline", [])
    fallback = {
        "education_score": 60,
        "education_analysis": "Education details could not be fully assessed.",
        "field_alignment": "partially_aligned",
        "timeline_score": 70,
        "timeline_analysis": "Employment timeline could not be fully assessed.",
        "gap_interpretation": "No significant gap pattern detected.",
    }
    try:
        llm    = get_fast_llm()
        prompt = _EDU_TIMELINE_PROMPT.format(
            domain=jd.get("domain", "other"),
            seniority=jd.get("seniority", "mid"),
            education=json.dumps(cp.get("education", {})),
            timeline=json.dumps(timeline[:10]),
        )
        resp = await llm.ainvoke(prompt)
        return {"edu_timeline_analysis": _parse_json(resp.content, fallback)}
    except Exception as exc:
        return {"edu_timeline_analysis": fallback, "errors": [f"edu_timeline: {exc}"]}


# ─── Stage 3: Scorer & Explainer ──────────────────────────────────────────────

_SCORER_EXPLAINER_PROMPT = """\
Score a candidate for a role. Output ONLY valid JSON. No markdown.

INPUTS:
skill={skill_score} domain={domain_fit_score} arch={architecture_score} edu={education_score} timeline={timeline_score}
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
  "recommendation_rationale": ""
}}

RULES:
experience_score: required=0→min(100,actual*10); actual>=required→min(100,70+(actual-required)*5); else→(actual/required)*70
risk_penalty: 0-100 based on missing critical skills, gaps, domain mismatch
fit_score=round(skill*{w_skills}+exp*{w_experience}+arch*{w_architecture}+edu*{w_education}+tl*{w_timeline}+domain*{w_domain}-risk*{w_risk}), clamp 0-100
risk_level: >=72→Low, >=45→Medium, else→High; recommendation: >=72→Shortlist, >=45→Consider, else→Reject"""


async def scorer_explainer_node(state: PipelineState) -> dict:
    sa  = state.get("skill_analysis", {})
    eta = state.get("edu_timeline_analysis", {})
    cp  = state.get("candidate_profile", {})
    jd  = state.get("jd_analysis", {})
    w   = _normalize_weights({**DEFAULT_WEIGHTS, **(state.get("scoring_weights") or {})})

    fallback = _compute_fallback_scores(sa, eta, cp, jd, w)
    try:
        llm    = get_reasoning_llm()
        prompt = _SCORER_EXPLAINER_PROMPT.format(
            skill_score=sa.get("skill_score", 0),
            domain_fit_score=sa.get("domain_fit_score", 50),
            architecture_score=sa.get("architecture_score", 50),
            education_score=eta.get("education_score", 60),
            timeline_score=eta.get("timeline_score", 70),
            years_actual=cp.get("total_effective_years", 0),
            years_required=jd.get("required_years", 0),
            matched_skills=json.dumps(sa.get("matched_skills", [])[:8]),
            missing_skills=json.dumps(sa.get("missing_skills", [])[:8]),
            domain_fit_comment=sa.get("domain_fit_comment", ""),
            education_analysis=eta.get("education_analysis", ""),
            timeline_analysis=eta.get("timeline_analysis", ""),
            gap_interpretation=eta.get("gap_interpretation", ""),
            w_skills=w["skills"], w_experience=w["experience"],
            w_architecture=w["architecture"], w_education=w["education"],
            w_timeline=w["timeline"], w_domain=w["domain"], w_risk=w["risk"],
        )
        resp   = await llm.ainvoke(prompt)
        result = _parse_json(resp.content, fallback)

        # Sanitise fit_score and recommendation
        result["fit_score"] = max(0, min(100, int(result.get("fit_score", 50))))
        if result.get("final_recommendation") not in ("Shortlist", "Consider", "Reject"):
            fit = result["fit_score"]
            result["final_recommendation"] = (
                "Shortlist" if fit >= 72 else "Consider" if fit >= 45 else "Reject"
            )

        # Always override score_breakdown with the actual agent-computed input scores.
        # LLMs frequently output the schema template literal (0) for these fields due to
        # the input-to-output name mismatch (e.g. "skill_score" in → "skill_match" out).
        sb = result.setdefault("score_breakdown", {})
        sb["skill_match"]      = sa.get("skill_score", 0)
        sb["architecture"]     = sa.get("architecture_score", 0)
        sb["domain_fit"]       = sa.get("domain_fit_score", 0)
        sb["education"]        = eta.get("education_score", 0)
        sb["timeline"]         = eta.get("timeline_score", 0)
        # experience_match is LLM-computed (formula-based); keep it but sanitise
        sb["experience_match"] = max(0, min(100, int(
            result.get("experience_score", sb.get("experience_match", 0))
        )))
        result["score_breakdown"] = sb
        return {"final_scores": result}
    except Exception as exc:
        return {"final_scores": fallback, "errors": [f"scorer_explainer: {exc}"]}


# ─── Stage 3: Interview Questions ─────────────────────────────────────────────

_INTERVIEW_QS_PROMPT = """\
Generate interview questions. Output ONLY valid JSON. No markdown.

ROLE: {role_title}  DOMAIN: {domain}
MISSING SKILLS: {missing_skills}
GAPS/CONTEXT: {gap_interpretation}

OUTPUT SCHEMA:
{{
  "technical_questions": [],
  "behavioral_questions": [],
  "culture_fit_questions": []
}}

5 technical questions probing missing skills; 3 behavioral STAR questions on gaps; 2 culture/motivation questions."""


async def interview_qs_node(state: PipelineState) -> dict:
    sa  = state.get("skill_analysis", {})
    eta = state.get("edu_timeline_analysis", {})
    jd  = state.get("jd_analysis", {})
    missing = sa.get("missing_skills", [])
    fallback = {
        "technical_questions": (
            [f"Walk us through your experience with {s}?" for s in missing[:3]]
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
    try:
        llm    = get_fast_llm()
        prompt = _INTERVIEW_QS_PROMPT.format(
            role_title=jd.get("role_title", "the role"),
            domain=jd.get("domain", "other"),
            missing_skills=json.dumps(missing[:6]),
            gap_interpretation=eta.get("gap_interpretation", "No significant gaps."),
        )
        resp   = await llm.ainvoke(prompt)
        result = _parse_json(resp.content, fallback)
        return {"interview_questions": result}
    except Exception as exc:
        return {"interview_questions": fallback, "errors": [f"interview_qs: {exc}"]}


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

    graph.add_node("jd_parser",        jd_parser_node)
    graph.add_node("resume_parser",    resume_parser_node)
    graph.add_node("skill_domain",     skill_domain_node)
    graph.add_node("edu_timeline",     edu_timeline_node)
    graph.add_node("scorer_explainer", scorer_explainer_node)
    graph.add_node("interview_qs",     interview_qs_node)

    # Stage 1: parallel fan-out from START
    graph.add_edge(START, "jd_parser")
    graph.add_edge(START, "resume_parser")

    # Stage 2: fires only when BOTH Stage 1 nodes complete (LangGraph join)
    graph.add_edge("jd_parser",     "skill_domain")
    graph.add_edge("jd_parser",     "edu_timeline")
    graph.add_edge("resume_parser", "skill_domain")
    graph.add_edge("resume_parser", "edu_timeline")

    # Stage 3: fires only when BOTH Stage 2 nodes complete (LangGraph join)
    graph.add_edge("skill_domain",  "scorer_explainer")
    graph.add_edge("skill_domain",  "interview_qs")
    graph.add_edge("edu_timeline",  "scorer_explainer")
    graph.add_edge("edu_timeline",  "interview_qs")

    graph.add_edge("scorer_explainer", END)
    graph.add_edge("interview_qs",     END)

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
) -> dict:
    """Run the full pipeline and return the assembled result dict (non-streaming)."""
    state       = build_initial_state(resume_text, job_description, gap_analysis, scoring_weights)
    final_state = await pipeline.ainvoke(state)
    return assemble_result(final_state, parsed_data, gap_analysis)
