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


# ─── LLM factories ─────────────────────────────────────────────────────────────

def get_fast_llm() -> ChatOllama:
    """Fast 3b model for extraction, matching, education, interview agents."""
    return ChatOllama(
        model=OLLAMA_FAST_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        format="json",
    )


def get_reasoning_llm() -> ChatOllama:
    """Full model for scorer_explainer — needs multi-step reasoning depth."""
    return ChatOllama(
        model=OLLAMA_REASONING_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        format="json",
    )


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
You are a job description analyst. Extract structured requirements from the job description below.
Output ONLY valid JSON matching the exact schema. No markdown, no commentary.

JOB DESCRIPTION:
{jd_text}

OUTPUT SCHEMA:
{{
  "role_title": "extracted job title",
  "domain": "backend|frontend|fullstack|data_science|ml_ai|devops|embedded|mobile|design|management|other",
  "seniority": "junior|mid|senior|lead|principal",
  "required_skills": ["skill1", "skill2"],
  "required_years": 0,
  "nice_to_have_skills": ["skill1"],
  "key_responsibilities": ["responsibility1"]
}}"""


async def jd_parser_node(state: PipelineState) -> dict:
    fallback = {
        "role_title": "Not specified", "domain": "other", "seniority": "mid",
        "required_skills": [], "required_years": 0,
        "nice_to_have_skills": [], "key_responsibilities": [],
    }
    try:
        llm    = get_fast_llm()
        prompt = _JD_PARSER_PROMPT.format(jd_text=state["raw_jd_text"][:3000])
        resp   = await llm.ainvoke(prompt)
        return {"jd_analysis": _parse_json(resp.content, fallback)}
    except Exception as exc:
        return {"jd_analysis": fallback, "errors": [f"jd_parser: {exc}"]}


# ─── Stage 1: Resume Parser ────────────────────────────────────────────────────

_RESUME_PARSER_PROMPT = """\
You are a resume analyst. Extract structured candidate information from the resume below.
Use semantic understanding — recognize skill aliases and implied technologies (e.g. "ML" → "Machine Learning").
Output ONLY valid JSON matching the exact schema. No markdown, no commentary.

RESUME:
{resume_text}

OUTPUT SCHEMA:
{{
  "name": "candidate name or null",
  "skills_identified": ["all skills found — canonical names, e.g. Machine Learning not ML"],
  "education": {{
    "degree": "highest degree or null",
    "field": "field of study or null",
    "institution": "university or college name or null",
    "gpa_or_distinction": "GPA value or distinction mention or null"
  }},
  "career_summary": "2-sentence summary of career trajectory",
  "total_effective_years": 0.0,
  "current_role": "most recent job title or null",
  "current_company": "most recent company or null"
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
        prompt = _RESUME_PARSER_PROMPT.format(resume_text=state["raw_resume_text"][:4000])
        resp   = await llm.ainvoke(prompt)
        return {"candidate_profile": _parse_json(resp.content, fallback)}
    except Exception as exc:
        return {"candidate_profile": fallback, "errors": [f"resume_parser: {exc}"]}


# ─── Stage 2: Skill & Domain Analyzer ─────────────────────────────────────────

_SKILL_DOMAIN_PROMPT = """\
You are a technical skill evaluator. Compare the candidate's skills against the job requirements.
Use semantic matching — recognize aliases, synonyms, and adjacent technologies.
Output ONLY valid JSON matching the exact schema. No markdown.

REQUIRED SKILLS (from JD): {required_skills}
CANDIDATE SKILLS (from resume): {candidate_skills}
JD DOMAIN: {domain}
SENIORITY LEVEL: {seniority}

OUTPUT SCHEMA (all scores are integers 0–100):
{{
  "matched_skills": ["skills found in both JD and resume — semantic match allowed"],
  "missing_skills": ["JD-required skills absent from candidate"],
  "adjacent_skills": ["candidate skills not required but relevant to the role"],
  "skill_score": 0,
  "domain_fit_score": 0,
  "architecture_score": 0,
  "domain_fit_comment": "1 sentence on domain alignment",
  "architecture_comment": "1 sentence on evidence of system design or senior patterns"
}}

SCORING RULES:
- skill_score: percentage of required skills that candidate has (0–100)
- domain_fit_score: how closely candidate's domain aligns with role domain (0–100)
- architecture_score: evidence of system design, distributed systems, architecture decisions (0–100)"""


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
You are an education and career continuity analyst.
Output ONLY valid JSON matching the exact schema. No markdown.

ROLE DOMAIN: {domain}
SENIORITY LEVEL: {seniority}
CANDIDATE EDUCATION: {education}
EMPLOYMENT TIMELINE: {timeline}

OUTPUT SCHEMA (scores are integers 0–100):
{{
  "education_score": 0,
  "education_analysis": "1 sentence on degree relevance to this specific role and domain",
  "field_alignment": "aligned|partially_aligned|unrelated",
  "timeline_score": 0,
  "timeline_analysis": "1 sentence on career continuity and progression pattern",
  "gap_interpretation": "1 sentence interpreting any gaps in the context of career narrative"
}}

SCORING RULES:
- education_score: based on degree LEVEL (PhD > Masters > Bachelor > other)
  AND field relevance to {domain}. A PhD in an unrelated field scores lower than a
  relevant Bachelor's. Score 0–100.
- timeline_score: based on career stability, progression, gap severity context,
  and tenure patterns. Longer tenures and upward progression score higher. Score 0–100."""


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
You are a senior hiring decision engine. Using the scoring inputs below, compute the final
candidate fit score and generate explainability rationale.
Output ONLY valid JSON matching the exact schema. No markdown.

SCORING INPUTS:
  Skill Score:        {skill_score}/100
  Domain Fit Score:   {domain_fit_score}/100
  Architecture Score: {architecture_score}/100
  Education Score:    {education_score}/100
  Timeline Score:     {timeline_score}/100
  Experience:         {years_actual}y actual vs {years_required}y required
  Matched Skills:     {matched_skills}
  Missing Skills:     {missing_skills}
  Domain Fit Comment: {domain_fit_comment}
  Education Analysis: {education_analysis}
  Timeline Analysis:  {timeline_analysis}
  Gap Interpretation: {gap_interpretation}

SCORING WEIGHTS (must be applied exactly as given):
  skills={w_skills}, experience={w_experience}, architecture={w_architecture},
  education={w_education}, timeline={w_timeline}, domain_fit={w_domain},
  risk_penalty={w_risk}

OUTPUT SCHEMA (all component scores are integers 0–100):
{{
  "experience_score": 0,
  "risk_penalty": 0,
  "score_breakdown": {{
    "skill_match": 0,
    "experience_match": 0,
    "architecture": 0,
    "education": 0,
    "timeline": 0,
    "domain_fit": 0,
    "risk_penalty": 0
  }},
  "fit_score": 0,
  "risk_level": "Low|Medium|High",
  "risk_signals": [
    {{
      "type": "gap|skill_gap|domain_mismatch|stability|education|overqualified",
      "severity": "low|medium|high",
      "description": "specific fact-based description"
    }}
  ],
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["gap 1", "gap 2", "gap 3"],
  "explainability": {{
    "skill_rationale": "why skill score is X/100",
    "experience_rationale": "why experience score is X/100",
    "education_rationale": "why education score is X/100",
    "timeline_rationale": "why timeline score is X/100",
    "overall_rationale": "1–2 sentence holistic hiring summary"
  }},
  "final_recommendation": "Shortlist|Consider|Reject",
  "recommendation_rationale": "1 sentence explaining the recommendation"
}}

CALCULATION RULES:
- experience_score: if required=0 → min(100, actual*10); if actual>=required → min(100, 70+(actual-required)*5); else → (actual/required)*70
- risk_penalty: 0–100 based on severity of missing critical skills, large gaps, domain mismatch
- score_breakdown uses the INPUT scores (do NOT recalculate skill/domain/edu/timeline from scratch)
- fit_score = round(skill_match*{w_skills} + experience_match*{w_experience} + architecture*{w_architecture} + education*{w_education} + timeline*{w_timeline} + domain_fit*{w_domain} - risk_penalty*{w_risk}), then clamp to 0–100
- risk_level: Low if fit_score>=72, Medium if >=45, else High
- Shortlist if fit_score>=72, Consider if fit_score>=45, else Reject"""


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
        return {"final_scores": result}
    except Exception as exc:
        return {"final_scores": fallback, "errors": [f"scorer_explainer: {exc}"]}


# ─── Stage 3: Interview Questions ─────────────────────────────────────────────

_INTERVIEW_QS_PROMPT = """\
You are an expert technical interviewer. Generate targeted interview questions for a candidate evaluation.
Output ONLY valid JSON matching the exact schema. No markdown.

ROLE: {role_title}
DOMAIN: {domain}
MISSING SKILLS (to probe): {missing_skills}
CAREER GAPS / CONTEXT: {gap_interpretation}

OUTPUT SCHEMA:
{{
  "technical_questions": [
    "5 specific technical questions targeting the missing skills and domain requirements"
  ],
  "behavioral_questions": [
    "3 behavioral STAR-format questions addressing career gaps or stability signals"
  ],
  "culture_fit_questions": [
    "2 culture and motivation questions relevant to the role and seniority"
  ]
}}"""


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
