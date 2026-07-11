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
INTERVIEW_KIT_TIMEOUT = float(os.getenv("LLM_INTERVIEW_KIT_TIMEOUT", "180"))
KIT_LLM_MAX_ATTEMPTS = max(1, int(os.getenv("LLM_INTERVIEW_KIT_RETRIES", "2")))
VOICE_STRATEGY_TIMEOUT = float(os.getenv("LLM_VOICE_STRATEGY_TIMEOUT", "180"))


def _prebuild_voice_strategy_enabled() -> bool:
    """Pre-build recruiter voice strategy during analysis (off by default to save LLM calls)."""
    return os.getenv("PREBUILD_VOICE_STRATEGY", "0").strip().lower() in ("1", "true", "yes")


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

    hm_topics = context.get("hm_screen_topics") or []
    hm_lines = []
    for t in hm_topics[:8]:
        if isinstance(t, dict):
            q = (t.get("question") or "").strip()
            cat = (t.get("category") or "hm_focus").strip()
            if q:
                hm_lines.append(f"- [{cat}] {q}")
        elif isinstance(t, str) and t.strip():
            hm_lines.append(f"- [hm_focus] {t.strip()}")
    hm_screen_ctx = "\n".join(hm_lines) if hm_lines else "  None — use calibrated must-haves and skill gaps"

    deal_breakers = context.get("deal_breakers") or []
    deal_text = "; ".join(str(d) for d in deal_breakers[:6]) if deal_breakers else "None specified"

    calibrated_must = context.get("calibrated_must_haves") or []
    cal_text = ", ".join(str(s) for s in calibrated_must[:12]) if calibrated_must else "See must-have skills above"

    hm_notes = (context.get("hm_notes") or "").strip() or "None"
    success_90d = (context.get("success_criteria_90d") or "").strip() or "None"

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
        "hm_screen_ctx": hm_screen_ctx,
        "deal_breakers_text": deal_text,
        "calibrated_must_text": cal_text,
        "hm_notes": hm_notes,
        "success_criteria_90d": success_90d,
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

HM SCREEN-FOCUS TOPICS (PRIMARY — build threads from these first):
{ctx["hm_screen_ctx"]}

CALIBRATED MUST-HAVES: {ctx["calibrated_must_text"]}
DEAL-BREAKERS TO VERIFY: {ctx["deal_breakers_text"]}
HM NOTES: {ctx["hm_notes"]}
90-DAY SUCCESS: {ctx["success_criteria_90d"]}

Generate a recruiter SCREEN PLAYBOOK (not a keyword checklist). Return ONLY this JSON:
{{
  "interview_questions": {{
    "kit_version": 2,
    "screen_objective": "one sentence hiring goal",
    "candidate_briefing": {{
      "profile_snapshot": "2-3 sentence summary",
      "strengths_to_confirm": ["skill 1", "skill 2"],
      "areas_to_probe": ["gap with severity"],
      "context_notes": ["recruiter coaching notes"]
    }},
    "hypotheses": [
      {{"id": "H1", "label": "hiring hypothesis", "priority": "must_have|risk|nice_to_have|gate", "why": "reason"}}
    ],
    "open": {{
      "script": "",
      "listen_for": ["signal 1", "signal 2"],
      "recruiter_owned": true
    }},
    "threads": [
      {{
        "id": "thread_ownership",
        "title": "thread title",
        "kind": "ownership|risk|judgment",
        "hypothesis_ids": ["H1"],
        "time_minutes": 6,
        "priority": "must_have",
        "steps": [
          {{"text": "spoken question", "what_to_listen_for": ["signal"], "follow_ups": ["if vague ask"], "scoring_criteria": {{"strong": "...", "adequate": "...", "weak": "..."}}}}
        ]
      }}
    ],
    "close": {{
      "script": "motivation and next steps",
      "logistics": ["notice period", "travel"]
    }},
    "hm_debrief_template": {{
      "fit_summary_prompt": "prompt for HM summary",
      "must_haves": [{{"requirement": "skill", "status": "pending"}}],
      "hm_focus_if_proceed": ["technical focus 1"],
      "residual_risks": ["risk 1"]
    }},
    "technical_questions": [],
    "behavioral_questions": [],
    "culture_fit_questions": [],
    "experience_deep_dive_questions": []
  }}
}}

RULES:
- HM SCREEN-FOCUS topics are PRIMARY: dedicate the first thread to them when provided.
- 3-4 conversation THREADS (HM focus when present, ownership, risk gap, judgment). Each thread has 1-3 steps (follow-ups inline).
- Leave open.script empty (recruiter_owned) — recruiters use their own opener.
- 8-12 total spoken steps across threads. Also populate technical_questions / experience_deep_dive_questions / behavioral_questions as flattened copies of thread steps for legacy UI.
- Keep every spoken line under 200 characters — recruiters say these live on a call.
- Sound like a senior recruiter: varied phrasing, no repeated stems, no "walk me through one project" more than once.
- Risk thread must target top MISSING must-have. Ownership thread anchors to candidate's latest company/role.
- Behavioral/judgment: max 1 STAR-style question; never inject raw JD text into questions.
- No placeholders, broken grammar, or "isn't on your resume" phrasing.
- Skip culture_fit (empty array). Domain-appropriate language (TA vs SAP vs engineering vs general business).
- Every step needs what_to_listen_for and at least one follow_up for vague answers."""


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

    normalized = {
        "kit_version": iq.get("kit_version", 1),
        "screen_objective": iq.get("screen_objective", ""),
        "candidate_briefing": iq.get("candidate_briefing", {}),
        "hypotheses": iq.get("hypotheses") if isinstance(iq.get("hypotheses"), list) else [],
        "open": iq.get("open") if isinstance(iq.get("open"), dict) else {},
        "threads": iq.get("threads") if isinstance(iq.get("threads"), list) else [],
        "close": iq.get("close") if isinstance(iq.get("close"), dict) else {},
        "hm_debrief_template": iq.get("hm_debrief_template") if isinstance(iq.get("hm_debrief_template"), dict) else {},
        "recruiter_signals": iq.get("recruiter_signals") if isinstance(iq.get("recruiter_signals"), dict) else {},
        "technical_questions": _ensure_question_list(iq.get("technical_questions", [])),
        "behavioral_questions": _ensure_question_list(iq.get("behavioral_questions", [])),
        "culture_fit_questions": _ensure_question_list(iq.get("culture_fit_questions", [])),
        "experience_deep_dive_questions": _ensure_question_list(iq.get("experience_deep_dive_questions", [])),
    }

    # Flatten threads into legacy lists when LLM omitted them
    if normalized["threads"] and not normalized["technical_questions"] and not normalized["experience_deep_dive_questions"]:
        from app.backend.services.interview_kit_generator import _playbook_to_legacy
        legacy = _playbook_to_legacy(normalized["threads"])
        for key, items in legacy.items():
            if items and not normalized.get(key):
                normalized[key] = items

    return normalized


async def generate_interview_kit_with_llm(context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate interview kit JSON only (separate from narrative). Retries on transient failures."""
    from app.backend.services.hybrid_pipeline import _parse_llm_json_response, _is_ollama_cloud
    from app.backend.services.llm_service import use_gemini_for_analysis

    ctx = build_llm_prompt_context(context)
    prompt = _build_interview_kit_prompt(ctx)
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    if use_gemini_for_analysis():
        num_predict = 2500
    else:
        num_predict = 2500 if not _is_ollama_cloud(base_url) else 4000

    last_err: Optional[Exception] = None
    for attempt in range(KIT_LLM_MAX_ATTEMPTS):
        try:
            raw = await _invoke_llm_prompt(prompt, num_predict=num_predict)
            if not raw or len(raw) < 20:
                raise ValueError("Interview kit LLM returned empty response")

            parsed = _parse_llm_json_response(raw)
            if parsed is None:
                raise ValueError("Interview kit LLM returned non-JSON response")

            return _normalize_interview_kit(parsed)
        except Exception as err:
            last_err = err
            if attempt < KIT_LLM_MAX_ATTEMPTS - 1:
                log.warning(
                    "Interview kit LLM attempt %s/%s failed: %s: %s — retrying",
                    attempt + 1,
                    KIT_LLM_MAX_ATTEMPTS,
                    type(err).__name__,
                    str(err)[:160],
                )
                await asyncio.sleep(2 * (attempt + 1))
            else:
                raise last_err from err
    raise RuntimeError("Interview kit LLM failed after retries")


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
    *,
    kit_error: Optional[str] = None,
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
            result.interview_kit_error = kit_error if kit_status == "fallback" else None

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
    from app.backend.db.database import SessionLocal
    from app.backend.services.hybrid_pipeline import _build_fallback_narrative
    from app.backend.services.interview_kit_generator import count_kit_questions
    from app.backend.services.interview_kit_context import load_kit_inputs_for_screening

    log.info("Interview kit background task started for screening_result_id=%s", screening_result_id)
    _update_screening_fields(
        screening_result_id,
        tenant_id,
        interview_kit_status="processing",
        interview_kit_error=None,
    )

    db = SessionLocal()
    try:
        kit_inputs = load_kit_inputs_for_screening(db, screening_result_id, tenant_id)
    finally:
        db.close()

    if kit_inputs:
        llm_context = {**llm_context, **kit_inputs}
        python_result = {**python_result, "kit_inputs": kit_inputs}

    kit_status = "fallback"
    kit_error: Optional[str] = None
    interview_questions = None

    try:
        sem = get_ollama_semaphore()
        async with sem:
            kit = await asyncio.wait_for(
                generate_interview_kit_with_llm(llm_context),
                timeout=INTERVIEW_KIT_TIMEOUT,
            )
        interview_questions = kit
        if count_kit_questions(kit) > 0:
            kit_status = "ready"
            log.info("Interview kit LLM succeeded for screening_result_id=%s", screening_result_id)
        else:
            kit_error = "empty_kit: LLM returned zero questions"
            log.warning(
                "Interview kit LLM returned no questions for screening_result_id=%s — using deterministic fallback",
                screening_result_id,
            )
            fallback = _build_fallback_narrative(python_result, python_result.get("skill_analysis", {}))
            interview_questions = fallback.get("interview_questions", {})
            kit_status = "fallback"
    except asyncio.TimeoutError:
        kit_error = f"timeout: exceeded {INTERVIEW_KIT_TIMEOUT:.0f}s"
        log.warning(
            "Interview kit LLM timed out for screening_result_id=%s after %.0fs",
            screening_result_id,
            INTERVIEW_KIT_TIMEOUT,
        )
        fallback = _build_fallback_narrative(python_result, python_result.get("skill_analysis", {}))
        interview_questions = fallback.get("interview_questions", {})
        kit_status = "fallback"
    except Exception as err:
        kit_error = f"{type(err).__name__}: {str(err)[:200]}"
        log.warning(
            "Interview kit LLM failed for screening_result_id=%s: %s",
            screening_result_id,
            kit_error,
        )
        fallback = _build_fallback_narrative(python_result, python_result.get("skill_analysis", {}))
        interview_questions = fallback.get("interview_questions", {})
        kit_status = "fallback"

    if interview_questions:
        _merge_interview_kit(
            screening_result_id,
            tenant_id,
            interview_questions,
            kit_status,
            kit_error=kit_error,
        )


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
        if not row or not row.candidate_id:
            log.info("Skipping voice strategy pre-build: missing candidate on screening_result_id=%s", screening_result_id)
            return
        jd_id = row.role_template_id
        if not jd_id and row.requisition_id:
            from app.backend.services.requisition_service import resolve_role_picker_id
            _, _, jd_id, _ = resolve_role_picker_id(db, tenant_id, row.requisition_id)
        if not jd_id:
            log.info("Skipping voice strategy pre-build: missing JD on screening_result_id=%s", screening_result_id)
            return

        row.voice_strategy_status = "processing"
        db.commit()

        context_engine = InterviewContextEngine()
        agent = InterviewStrategyAgent()
        context = context_engine.build_context(
            db,
            candidate_id=row.candidate_id,
            screening_result_id=screening_result_id,
            jd_id=jd_id,
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
    from app.backend.services.interview_kit_generator import count_kit_questions

    recommendation = (
        python_result.get("final_recommendation")
        or llm_context.get("scores", {}).get("final_recommendation")
        or ""
    )

    if narrative_status == "fallback" and narrative_payload:
        kit = narrative_payload.get("interview_questions")
        if kit and count_kit_questions(kit) > 0:
            _merge_interview_kit(screening_result_id, tenant_id, kit, "fallback")
        else:
            asyncio.create_task(
                background_interview_kit(screening_result_id, tenant_id, llm_context, python_result)
            )
    else:
        _update_screening_fields(screening_result_id, tenant_id, interview_kit_status="pending")
        asyncio.create_task(
            background_interview_kit(screening_result_id, tenant_id, llm_context, python_result)
        )

    if recommendation in ("Shortlist", "Consider") and _prebuild_voice_strategy_enabled():
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
