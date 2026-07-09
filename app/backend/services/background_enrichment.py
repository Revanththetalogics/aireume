"""
Background enrichment after narrative completes.

Phase 2a: Interview kit (screen questions JSON) — merged into report silently.
Phase 2b: Voice interview strategy — pre-built for Shortlist/Consider candidates.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, Optional

from app.backend.services.llm_service import get_ollama_semaphore

log = logging.getLogger("aria.enrichment")

DEFAULT_VOICE_STRATEGY_CONFIG = {"duration_minutes": 20, "question_count": 12}
INTERVIEW_KIT_TIMEOUT = float(os.getenv("LLM_INTERVIEW_KIT_TIMEOUT", os.getenv("LLM_NARRATIVE_TIMEOUT", "300")))
VOICE_STRATEGY_TIMEOUT = float(os.getenv("LLM_VOICE_STRATEGY_TIMEOUT", "180"))


def voice_strategy_config_hash(config: dict[str, Any] | None = None) -> str:
    cfg = config or DEFAULT_VOICE_STRATEGY_CONFIG
    normalized = {
        "duration_minutes": int(cfg.get("duration_minutes", 20)),
        "question_count": int(cfg.get("question_count", 12)),
    }
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()[:32]


def build_llm_prompt_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Shared prompt variables for narrative and interview-kit LLM calls."""
    from app.backend.services.hybrid_pipeline import _sanitize_input
    from app.backend.services.profile_text_sanitizer import (
        sanitize_jd_responsibilities,
        sanitize_profile_text,
        sanitize_skill_list,
    )

    jd = context.get("jd_analysis", {})
    profile = context.get("candidate_profile", {})
    scores = context.get("scores", {})
    skill_a = context.get("skill_analysis", {})
    score_rationales = context.get("score_rationales", {})
    risk_summary = context.get("risk_summary", {})

    career_snippet = _sanitize_input(
        sanitize_profile_text((profile.get("career_summary") or "")[:300]), 400, "career_snippet"
    )
    role_title = _sanitize_input(
        sanitize_profile_text(jd.get("role_title") or jd.get("title", "Unknown Role")), 200, "role_title"
    )
    candidate_name = _sanitize_input(sanitize_profile_text(profile.get("name") or "Unknown"), 100, "name")
    current_role = _sanitize_input(
        sanitize_profile_text(profile.get("current_role") or "N/A"), 100, "current_role"
    )
    current_company = _sanitize_input(
        sanitize_profile_text(profile.get("current_company") or "N/A"), 100, "current_company"
    )

    domain = jd.get("domain", "General")
    seniority = jd.get("seniority", "Not specified")
    years = profile.get("total_effective_years", 0)

    skill_score = scores.get("skill_score", 0)
    exp_score = scores.get("exp_score", 0)
    edu_score = scores.get("edu_score", 0)
    timeline_score = scores.get("timeline_score", 0)
    fit_score = scores.get("fit_score", 0)
    recommendation = scores.get("final_recommendation", "Pending")

    matched_must = sanitize_skill_list(skill_a.get("matched_required", []))
    missing_must = sanitize_skill_list(skill_a.get("missing_required", []))
    matched_nice = sanitize_skill_list(skill_a.get("matched_nice_to_have", []))
    missing_nice = sanitize_skill_list(skill_a.get("missing_nice_to_have", []))
    nice_match_pct = skill_a.get("nice_to_have_match_pct") or 0
    req_match_pct = skill_a.get("required_match_pct") or 0

    key_resp = sanitize_jd_responsibilities(jd.get("key_responsibilities", [])[:6])
    resp_text = "; ".join(key_resp) if key_resp else "Not specified"

    prof_analysis = skill_a.get("proficiency_analysis", {})
    prof_lines = [
        f"{sname}: req={pdata.get('required', '?')} cand={pdata.get('estimated_candidate', '?')}"
        for sname, pdata in list(prof_analysis.items())[:8]
    ]
    prof_text = "; ".join(prof_lines) if prof_lines else "Not assessed"

    education = profile.get("education", [])
    edu_parts = []
    for edu in (education if isinstance(education, list) else [])[:3]:
        deg = edu.get("degree", "") if isinstance(edu, dict) else ""
        fld = edu.get("field", "") if isinstance(edu, dict) else ""
        inst = edu.get("institution", "") if isinstance(edu, dict) else ""
        if deg or fld:
            part = f"{deg} {fld}".strip()
            if inst:
                part = f"{part} ({inst})"
            edu_parts.append(part)
        elif inst:
            edu_parts.append(inst)
    edu_text = "; ".join(edu_parts) if edu_parts else "Not available"

    seniority_alignment = risk_summary.get("seniority_alignment", "Not assessed")
    risk_flags_list = risk_summary.get("risk_flags", [])
    if risk_flags_list:
        risk_flags = "\n".join(
            f"  - {rf.get('flag', 'Unknown')}: {rf.get('detail', '')} (severity: {rf.get('severity', 'low')})"
            for rf in risk_flags_list[:6]
        )
    else:
        risk_flags = "  None identified"

    if score_rationales:
        rationales_parts = []
        for key in ["skill_rationale", "experience_rationale", "education_rationale", "timeline_rationale"]:
            val = score_rationales.get(key, "")
            if val:
                rationales_parts.append(f"{key.split('_')[0]}: {val}")
        score_rationales_summary = " | ".join(rationales_parts) if rationales_parts else "Not available"
    else:
        score_rationales_summary = "Not available"

    must_have_ctx_lines = []
    for sk in missing_must[:6]:
        best_resp = key_resp[0] if key_resp else "this role"
        prof_entry = prof_analysis.get(sk, {})
        cand_lvl = prof_entry.get("estimated_candidate", "not assessed") if prof_entry else "not assessed"
        must_have_ctx_lines.append(
            f"- {sk}: MISSING | Candidate level: {cand_lvl} | Needed for: \"{best_resp}\""
        )
    for sk in matched_must[:4]:
        prof_entry = prof_analysis.get(sk, {})
        req_lvl = prof_entry.get("required", "not specified") if prof_entry else "not specified"
        cand_lvl = prof_entry.get("estimated_candidate", "not assessed") if prof_entry else "not assessed"
        gap_note = " [PROFICIENCY GAP]" if prof_entry and prof_entry.get("match_factor", 1.0) < 1.0 else ""
        best_resp = key_resp[0] if key_resp else "this role"
        must_have_ctx_lines.append(
            f"- {sk}: Matched{gap_note} | Required: {req_lvl}, Candidate: {cand_lvl} | Needed for: \"{best_resp}\""
        )
    must_have_ctx = "\n".join(must_have_ctx_lines) if must_have_ctx_lines else "  No must-have skills data available"

    lang_ctx = context.get("language_context", {})
    lang_instruction = lang_ctx.get("llm_instruction", "")
    lang_prefix = f"\n{lang_instruction}\n" if lang_instruction else ""

    return {
        "role_title": role_title,
        "domain": domain,
        "seniority": seniority,
        "candidate_name": candidate_name,
        "years": years,
        "current_role": current_role,
        "current_company": current_company,
        "career_snippet": career_snippet,
        "skill_score": skill_score,
        "exp_score": exp_score,
        "edu_score": edu_score,
        "timeline_score": timeline_score,
        "fit_score": fit_score,
        "recommendation": recommendation,
        "matched_must": matched_must,
        "missing_must": missing_must,
        "matched_nice": matched_nice,
        "missing_nice": missing_nice,
        "nice_match_pct": nice_match_pct,
        "req_match_pct": req_match_pct,
        "resp_text": resp_text,
        "prof_text": prof_text,
        "edu_text": edu_text,
        "seniority_alignment": seniority_alignment,
        "risk_flags": risk_flags,
        "score_rationales_summary": score_rationales_summary,
        "must_have_ctx": must_have_ctx,
        "lang_prefix": lang_prefix,
    }


def _build_interview_kit_prompt(ctx: Dict[str, Any]) -> str:
    return f"""IMPORTANT: Respond with ONLY a valid JSON object. No markdown, no code blocks.{ctx["lang_prefix"]}

ROLE: {ctx["role_title"]} | {ctx["domain"]} | {ctx["seniority"]}
CANDIDATE: {ctx["candidate_name"]} | {ctx["years"]}y experience | {ctx["current_role"]} at {ctx["current_company"]}
SCORES: skill={ctx["skill_score"]} exp={ctx["exp_score"]} fit={ctx["fit_score"]} /100
RECOMMENDATION: {ctx["recommendation"]}
MATCHED MUST-HAVE: {', '.join(ctx["matched_must"][:10]) if ctx["matched_must"] else 'None'}
MISSING MUST-HAVE: {', '.join(ctx["missing_must"][:6]) if ctx["missing_must"] else 'None'}
KEY RESPONSIBILITIES: {ctx["resp_text"]}
PROFICIENCY GAPS: {ctx["prof_text"]}
RISK FLAGS:
{ctx["risk_flags"]}

MUST-HAVE SKILLS CONTEXT:
{ctx["must_have_ctx"]}

Generate a targeted interview kit. Return ONLY this JSON:
{{
  "interview_questions": {{
    "candidate_briefing": {{
      "profile_snapshot": "2-3 sentence summary",
      "strengths_to_confirm": ["skill 1", "skill 2"],
      "areas_to_probe": ["gap with severity"],
      "context_notes": ["why question targets gap X"]
    }},
    "technical_questions": [
      {{"text": "scenario question", "what_to_listen_for": ["signal"], "follow_ups": ["follow-up"], "scoring_criteria": {{"strong": "...", "adequate": "...", "weak": "..."}}}}
    ],
    "behavioral_questions": [
      {{"text": "STAR question", "what_to_listen_for": ["signal"], "follow_ups": ["follow-up"], "scoring_criteria": {{"strong": "...", "adequate": "...", "weak": "..."}}}}
    ],
    "culture_fit_questions": [
      {{"text": "motivation question", "what_to_listen_for": ["signal"], "follow_ups": ["follow-up"], "scoring_criteria": {{"strong": "...", "adequate": "...", "weak": "..."}}}}
    ],
    "experience_deep_dive_questions": [
      {{"text": "project deep-dive", "what_to_listen_for": ["signal"], "follow_ups": ["follow-up"], "scoring_criteria": {{"strong": "...", "adequate": "...", "weak": "..."}}}}
    ]
  }}
}}

RULES:
- 8-10 total questions. Prioritize technical and experience; skip culture_fit (return empty array).
- Keep every question under 140 characters — recruiters ask them live on a call.
- No overlapping templates (do not repeat "tell me about a project" across categories).
- Technical: gap-probe missing must-haves ("X isn't on resume — have you used it?") AND validate matched skills with resume context (company/role).
- Experience: anchor to candidate's companies/roles from resume — modules owned, integrations, production issues.
- Behavioral: max 1 short question tied to a JD responsibility, not generic leadership/conflict.
- Every question must reference specific skills, gaps, or resume context.
- No generic questions like "Tell me about yourself".
- Keep scoring_criteria concise (one sentence per level)."""


async def _invoke_llm_prompt(prompt: str, *, num_predict: int) -> str:
    from app.backend.services.hybrid_pipeline import _bind_num_predict, _get_llm
    from langchain_core.messages import HumanMessage

    llm = _get_llm()
    if llm is None:
        raise RuntimeError("LLM not available")

    bound = _bind_num_predict(llm, num_predict)

    response = await bound.ainvoke([HumanMessage(content=prompt)])
    raw = response.content if hasattr(response, "content") else str(response)
    return (raw or "").strip()


def _normalize_interview_kit(data: dict) -> dict:
    def _ensure_question_list(v) -> list:
        if not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str):
                result.append({"text": item, "what_to_listen_for": [], "follow_ups": []})
        return result

    iq = data.get("interview_questions", data)
    if not isinstance(iq, dict):
        iq = {}

    return {
        "candidate_briefing": iq.get("candidate_briefing", {}),
        "technical_questions": _ensure_question_list(iq.get("technical_questions", [])),
        "behavioral_questions": _ensure_question_list(iq.get("behavioral_questions", [])),
        "culture_fit_questions": _ensure_question_list(iq.get("culture_fit_questions", [])),
        "experience_deep_dive_questions": _ensure_question_list(iq.get("experience_deep_dive_questions", [])),
    }


async def generate_interview_kit_with_llm(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate interview kit JSON only (separate from narrative)."""
    from app.backend.services.hybrid_pipeline import _parse_llm_json_response, _is_ollama_cloud
    from app.backend.services.llm_service import use_gemini_for_analysis

    ctx = build_llm_prompt_context(context)
    prompt = _build_interview_kit_prompt(ctx)
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if use_gemini_for_analysis():
        num_predict = 2500
    else:
        num_predict = 2500 if not _is_ollama_cloud(base_url) else 4000

    raw = await _invoke_llm_prompt(prompt, num_predict=num_predict)
    if not raw or len(raw) < 20:
        raise ValueError("Interview kit LLM returned empty response")

    parsed = _parse_llm_json_response(raw)
    if parsed is None:
        raise ValueError("Interview kit LLM returned non-JSON response")

    return _normalize_interview_kit(parsed)


def _update_screening_fields(
    screening_result_id: int,
    tenant_id: int,
    **fields: Any,
) -> bool:
    from app.backend.db.database import SessionLocal
    from app.backend.models.db_models import ScreeningResult

    try:
        db = SessionLocal()
        try:
            result = db.query(ScreeningResult).filter(
                ScreeningResult.id == screening_result_id,
                ScreeningResult.tenant_id == tenant_id,
            ).first()
            if not result:
                return False
            for key, value in fields.items():
                setattr(result, key, value)
            db.commit()
            return True
        finally:
            db.close()
    except Exception as err:
        log.warning(
            "Failed to update screening_result_id=%s fields %s: %s",
            screening_result_id,
            list(fields.keys()),
            str(err)[:200],
        )
        return False


def _merge_interview_kit(
    screening_result_id: int,
    tenant_id: int,
    interview_questions: dict,
    kit_status: str,
) -> bool:
    from app.backend.db.database import SessionLocal
    from app.backend.models.db_models import ScreeningResult
    from app.backend.services.hybrid_pipeline import _merge_llm_into_result

    try:
        db = SessionLocal()
        try:
            result = db.query(ScreeningResult).filter(
                ScreeningResult.id == screening_result_id,
                ScreeningResult.tenant_id == tenant_id,
            ).first()
            if not result:
                return False

            narrative = {}
            if result.narrative_json:
                try:
                    narrative = json.loads(result.narrative_json)
                except json.JSONDecodeError:
                    narrative = {}

            narrative["interview_questions"] = interview_questions
            result.narrative_json = json.dumps(narrative, default=str)
            result.interview_kit_status = kit_status

            analysis = {}
            if result.analysis_result:
                try:
                    analysis = json.loads(result.analysis_result)
                except json.JSONDecodeError:
                    analysis = {}
            analysis["interview_questions"] = interview_questions
            merged = _merge_llm_into_result(analysis, narrative)
            result.analysis_result = json.dumps(merged, default=str)
            db.commit()
            log.info(
                "Interview kit merged (status=%s) for screening_result_id=%s",
                kit_status,
                screening_result_id,
            )
            return True
        finally:
            db.close()
    except Exception as err:
        log.warning(
            "Failed to merge interview kit for screening_result_id=%s: %s",
            screening_result_id,
            str(err)[:200],
        )
        return False


async def background_interview_kit(
    screening_result_id: int,
    tenant_id: int,
    llm_context: Dict[str, Any],
    python_result: Dict[str, Any],
) -> None:
    """Background task: generate interview kit and merge into stored report."""
    from app.backend.services.hybrid_pipeline import _build_fallback_narrative

    log.info("Interview kit background task started for screening_result_id=%s", screening_result_id)
    _update_screening_fields(
        screening_result_id,
        tenant_id,
        interview_kit_status="processing",
    )

    kit_status = "fallback"
    interview_questions = None

    try:
        sem = get_ollama_semaphore()
        async with sem:
            kit = await asyncio.wait_for(
                generate_interview_kit_with_llm(llm_context),
                timeout=INTERVIEW_KIT_TIMEOUT,
            )
        interview_questions = kit
        kit_status = "ready"
        log.info("Interview kit LLM succeeded for screening_result_id=%s", screening_result_id)
    except Exception as err:
        log.warning(
            "Interview kit LLM failed for screening_result_id=%s: %s: %s",
            screening_result_id,
            type(err).__name__,
            str(err)[:200],
        )
        fallback = _build_fallback_narrative(python_result, python_result.get("skill_analysis", {}))
        interview_questions = fallback.get("interview_questions", {})
        kit_status = "fallback"

    if interview_questions:
        _merge_interview_kit(screening_result_id, tenant_id, interview_questions, kit_status)


async def background_voice_strategy(
    screening_result_id: int,
    tenant_id: int,
) -> None:
    """Pre-build voice interview strategy for candidates likely to be screened."""
    from app.backend.db.database import SessionLocal
    from app.backend.models.db_models import ScreeningResult
    from app.backend.services.recruiter.context_engine import InterviewContextEngine
    from app.backend.services.recruiter.strategy_agent import InterviewStrategyAgent

    log.info("Voice strategy pre-build started for screening_result_id=%s", screening_result_id)

    db = SessionLocal()
    try:
        row = db.query(ScreeningResult).filter(
            ScreeningResult.id == screening_result_id,
            ScreeningResult.tenant_id == tenant_id,
        ).first()
        if not row or not row.candidate_id or not row.role_template_id:
            log.info("Skipping voice strategy pre-build: missing candidate or JD on screening_result_id=%s", screening_result_id)
            return

        row.voice_strategy_status = "processing"
        db.commit()

        context_engine = InterviewContextEngine()
        agent = InterviewStrategyAgent()
        context = context_engine.build_context(
            db,
            candidate_id=row.candidate_id,
            screening_result_id=screening_result_id,
            jd_id=row.role_template_id,
        )
        config_hash = voice_strategy_config_hash(DEFAULT_VOICE_STRATEGY_CONFIG)

        try:
            sem = get_ollama_semaphore()
            async with sem:
                strategy = await asyncio.wait_for(
                    agent.generate_strategy(context, DEFAULT_VOICE_STRATEGY_CONFIG),
                    timeout=VOICE_STRATEGY_TIMEOUT,
                )
            row.voice_strategy_json = json.dumps(strategy, default=str)
            row.voice_strategy_status = "ready"
            row.voice_strategy_config_hash = config_hash
            db.commit()
            log.info("Voice strategy pre-built for screening_result_id=%s", screening_result_id)
        except Exception as err:
            log.warning(
                "Voice strategy pre-build failed for screening_result_id=%s: %s: %s",
                screening_result_id,
                type(err).__name__,
                str(err)[:200],
            )
            fallback = agent._build_fallback_strategy(context, DEFAULT_VOICE_STRATEGY_CONFIG)
            row.voice_strategy_json = json.dumps(fallback, default=str)
            row.voice_strategy_status = "fallback"
            row.voice_strategy_config_hash = config_hash
            db.commit()
    finally:
        db.close()


def schedule_post_narrative_enrichment(
    screening_result_id: int,
    tenant_id: int,
    llm_context: Dict[str, Any],
    python_result: Dict[str, Any],
    *,
    narrative_status: str,
    narrative_payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Chain background interview kit + voice strategy after narrative is persisted."""
    recommendation = (
        python_result.get("final_recommendation")
        or llm_context.get("scores", {}).get("final_recommendation")
        or ""
    )

    if narrative_status == "fallback" and narrative_payload:
        kit = narrative_payload.get("interview_questions")
        if kit:
            _update_screening_fields(screening_result_id, tenant_id, interview_kit_status="ready")
        else:
            asyncio.create_task(
                background_interview_kit(screening_result_id, tenant_id, llm_context, python_result)
            )
    else:
        _update_screening_fields(screening_result_id, tenant_id, interview_kit_status="pending")
        asyncio.create_task(
            background_interview_kit(screening_result_id, tenant_id, llm_context, python_result)
        )

    if recommendation in ("Shortlist", "Consider"):
        _update_screening_fields(screening_result_id, tenant_id, voice_strategy_status="pending")
        asyncio.create_task(background_voice_strategy(screening_result_id, tenant_id))
    else:
        _update_screening_fields(screening_result_id, tenant_id, voice_strategy_status="skipped")


def load_cached_voice_strategy(
    db,
    screening_result_id: int | None,
    tenant_id: int,
    strategy_config: dict[str, Any],
) -> dict[str, Any] | None:
    """Return pre-built voice strategy if config hash matches."""
    if not screening_result_id:
        return None

    from app.backend.models.db_models import ScreeningResult

    row = db.query(ScreeningResult).filter(
        ScreeningResult.id == screening_result_id,
        ScreeningResult.tenant_id == tenant_id,
    ).first()
    if not row or row.voice_strategy_status not in ("ready", "fallback"):
        return None
    if not row.voice_strategy_json:
        return None

    expected_hash = voice_strategy_config_hash(strategy_config)
    if row.voice_strategy_config_hash and row.voice_strategy_config_hash != expected_hash:
        return None

    try:
        return json.loads(row.voice_strategy_json)
    except json.JSONDecodeError:
        return None
