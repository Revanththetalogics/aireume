"""
Resume analysis routes — hybrid pipeline (Python scoring + single LLM narrative).

Key changes vs old LangGraph version:
  - Uses run_hybrid_pipeline / astream_hybrid_pipeline instead of agent_pipeline
  - 3-layer candidate deduplication (email → file hash → name+phone)
  - Full candidate profile stored in Candidate row on every new/updated analysis
  - DB-shared JD cache (all 4 workers share the same parsed JD result)
  - JD minimum content check (< 80 words rejected)
  - asyncio.to_thread for blocking PDF parse
  - Structured JSON logging per analysis
"""

import hashlib
import json
import os
import asyncio
import logging
import time
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import update, func

from app.backend.db.database import get_db, SessionLocal
from app.backend.middleware.auth import get_current_user
from app.backend.services.jd_quality_scorer import score_jd_quality
from app.backend.models.db_models import ScreeningResult, User, Candidate, JdCache, Tenant, SubscriptionPlan, OutcomeSkillPattern, SkillTrendSnapshot, TeamSkillProfile
from app.backend.models.schemas import (
    AnalysisResponse, BatchAnalysisResponse, BatchAnalysisResult,
    BatchFailedItem, BatchStreamEvent,
    DuplicateCandidateInfo,
    RescoreRequest,
)
from app.backend.services.constants import (
    GENERIC_SOFT_SKILLS, MUST_HAVE_CUES, NICE_TO_HAVE_CUES,
    JOB_FUNCTION_SKILL_TAXONOMY,
    RECOMMENDATION_THRESHOLDS,
)
from app.backend.services.parser_service import parse_resume, extract_jd_text
from app.backend.services.doc_converter import convert_to_pdf
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.hybrid_pipeline import (
    run_hybrid_pipeline,
    astream_hybrid_pipeline,
    parse_jd_rules,
    shutdown_background_tasks,
    _background_llm_narrative,
    register_background_task,
)
from app.backend.services.fit_scorer import compute_fit_score
from app.backend.services.weight_mapper import convert_to_new_schema
from app.backend.services.skill_matcher import JD_CACHE_VERSION
from app.backend.routes.subscription import _ensure_monthly_reset, _get_plan_limits, record_usage
from app.backend.services.billing.quota import check_quota
from app.backend.services.outcome_service import compute_skill_patterns
from app.backend.services.team_service import get_team_profile
from app.backend.services.skill_trend_service import get_skill_trends

router = APIRouter(prefix="/api", tags=["analysis"])
log    = logging.getLogger("aria.analysis")

ALLOWED_EXTENSIONS = ('.pdf', '.docx', '.doc', '.txt', '.rtf', '.odt')

# Maximum JD size (50KB)
MAX_JD_SIZE = 50 * 1024  # 50KB

# Maximum scoring_weights size (4KB)
MAX_SCORING_WEIGHTS_SIZE = 4 * 1024  # 4KB

# ─── File content (magic bytes) validation ─────────────────────────────────────

FILE_SIGNATURES = {
    '.pdf':  [b'%PDF'],
    '.docx': [b'PK\x03\x04'],          # ZIP-based format
    '.doc':  [b'\xd0\xcf\x11\xe0'],   # OLE2 Compound Document
    '.odt':  [b'PK\x03\x04'],           # ZIP-based format (like DOCX)
    '.rtf':  [b'{\\rtf'],
    '.txt':  None,                        # No signature check for plain text
}


def _validate_file_content(content: bytes, filename: str) -> None:
    """Verify that file content matches its extension via magic-byte signatures.

    Additional layers beyond the existing extension allowlist:
      1. Magic-byte check — the first bytes of the file must match the
         expected signature for the declared extension.
      2. For .txt files — heuristic check that content is not binary.

    Raises HTTPException(400) on validation failure.
    """
    ext = os.path.splitext(filename.lower())[1]
    signatures = FILE_SIGNATURES.get(ext)

    # Extension not in signature table — skip content check
    if signatures is None and ext != '.txt':
        return

    # ── .txt: heuristic binary detection ────────────────────────────────────
    if ext == '.txt':
        if not content:
            return  # empty file is acceptable for .txt
        sample = content[:1000]
        non_printable = sum(
            1 for b in sample
            if b < 0x20 and b not in (0x09, 0x0A, 0x0D)  # TAB, LF, CR
        )
        if len(sample) and non_printable / len(sample) > 0.30:
            log.warning("File signature mismatch for %s: expected %s format", filename, ext)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file content: '{filename}' does not appear to be a valid {ext} file",
            )
        return

    # ── Magic-byte check for binary formats ─────────────────────────────────
    # Empty files or files shorter than the shortest signature automatically fail
    if not content:
        log.warning("File signature mismatch for %s: expected %s format", filename, ext)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file content: '{filename}' does not appear to be a valid {ext} file",
        )

    min_sig_len = min(len(s) for s in signatures)
    if len(content) < min_sig_len:
        log.warning("File signature mismatch for %s: expected %s format", filename, ext)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file content: '{filename}' does not appear to be a valid {ext} file",
        )

    for sig in signatures:
        if content.startswith(sig):
            return  # signature matches

    log.warning("File signature mismatch for %s: expected %s format", filename, ext)
    raise HTTPException(
        status_code=400,
        detail=f"Invalid file content: '{filename}' does not appear to be a valid {ext} file",
    )

# ─── Batch processing concurrency control ───────────────────────────────────────

_BATCH_SEMAPHORE = asyncio.Semaphore(int(os.getenv("BATCH_MAX_CONCURRENT", "30")))
MAX_BATCH_SIZE = 50


# ─── JSON serialization helper ────────────────────────────────────────────────

def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal, bytes)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        import base64
        return base64.b64encode(obj).decode("ascii")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _apply_skill_overrides(jd_analysis: dict, overrides: dict | None) -> dict:
    """Apply user-specified skill overrides to jd_analysis in-place.

    Preserves original skills as ``original_required_skills`` /
    ``original_nice_to_have_skills`` and sets ``skill_overrides_applied``
    so downstream consumers can detect overrides.

    Supports proficiency-aware overrides where each skill can be a dict:
        {"skill": "Python", "proficiency": "advanced"}
    Proficiency data is stored separately in
    ``jd_analysis["skill_proficiency_requirements"]`` for downstream scoring.
    """
    if not overrides:
        return jd_analysis

    proficiency_map: dict[str, str] = {}

    def _extract_skills(skill_list: list) -> list[str]:
        """Normalise a skill list that may contain strings or proficiency dicts."""
        result: list[str] = []
        for item in skill_list:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and "skill" in item:
                result.append(item["skill"])
                prof = item.get("proficiency")
                if isinstance(prof, str) and prof.lower() in (
                    "basic", "intermediate", "advanced", "expert",
                ):
                    proficiency_map[item["skill"].lower()] = prof.lower()
        return result

    if "required_skills" in overrides and isinstance(overrides["required_skills"], list):
        jd_analysis["original_required_skills"] = jd_analysis.get("required_skills", [])
        jd_analysis["required_skills"] = _extract_skills(overrides["required_skills"])
    if "nice_to_have_skills" in overrides and isinstance(overrides["nice_to_have_skills"], list):
        jd_analysis["original_nice_to_have_skills"] = jd_analysis.get("nice_to_have_skills", [])
        jd_analysis["nice_to_have_skills"] = _extract_skills(overrides["nice_to_have_skills"])
    jd_analysis["skill_overrides_applied"] = True

    # Store proficiency requirements separately for downstream scoring
    if proficiency_map:
        jd_analysis["skill_proficiency_requirements"] = proficiency_map
    else:
        jd_analysis.pop("skill_proficiency_requirements", None)

    log.info("Skill overrides applied: required=%d, nice_to_have=%d, proficiency_entries=%d",
             len(overrides.get("required_skills", [])),
             len(overrides.get("nice_to_have_skills", [])),
             len(proficiency_map))
    return jd_analysis


# ─── JD cache helpers ─────────────────────────────────────────────────────────

def _get_or_cache_jd(db: Session, job_description: str) -> dict:
    """Parse the JD or return the cached result. Shared across all workers via DB.

    Cached entries are automatically invalidated when JD_CACHE_VERSION changes,
    ensuring stale skill-extraction results are never reused after logic updates.
    """
    jd_hash = hashlib.md5(job_description[:2000].encode()).hexdigest()
    cached = db.query(JdCache).filter(JdCache.hash == jd_hash).first()
    if cached:
        try:
            parsed = json.loads(cached.result_json)
            if parsed.get("_cache_version") == JD_CACHE_VERSION:
                return parsed
            log.info("JD cache invalidated (version mismatch: cached=%s current=%s)",
                     parsed.get("_cache_version"), JD_CACHE_VERSION)
        except Exception as e:
            log.warning("Non-critical: Failed to parse cached JD JSON, re-parsing: %s", e)
    jd_analysis = parse_jd_rules(job_description)
    jd_analysis["_cache_version"] = JD_CACHE_VERSION
    try:
        db.merge(JdCache(hash=jd_hash, result_json=json.dumps(jd_analysis, default=_json_default)))
        db.commit()
    except Exception as e:
        log.warning("Non-critical: Failed to cache JD analysis: %s", e)
        try:
            db.rollback()
        except Exception as rollback_err:
            log.warning("Non-critical: Rollback also failed: %s", rollback_err)
    return jd_analysis


# ─── Candidate deduplication & profile storage ────────────────────────────────

def _build_duplicate_info(db: Session, candidate: Candidate) -> DuplicateCandidateInfo:
    """Build the DuplicateCandidateInfo payload from an existing Candidate row."""
    last_result = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.candidate_id == candidate.id)
        .order_by(ScreeningResult.timestamp.desc())
        .first()
    )
    result_count = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.candidate_id == candidate.id)
        .count()
    )
    skills_snapshot = []
    if candidate.parsed_skills:
        try:
            skills_snapshot = json.loads(candidate.parsed_skills)[:10]
        except Exception as e:
            log.warning("Non-critical: Failed to parse skills snapshot for candidate %s: %s", candidate.id, e)

    return DuplicateCandidateInfo(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        current_role=candidate.current_role,
        current_company=candidate.current_company,
        total_years_exp=candidate.total_years_exp,
        skills_snapshot=skills_snapshot,
        result_count=result_count,
        last_analyzed=last_result.timestamp.isoformat() if last_result and last_result.timestamp else None,
        profile_quality=candidate.profile_quality,
    )


_SNAPSHOT_JSON_MAX = 500_000  # bytes of UTF-8 JSON; keeps row size bounded


def _parser_snapshot_json(parsed_data: dict) -> str | None:
    """Serialize full parser output so DB retains every field (not only pattern-derived columns)."""
    try:
        s = json.dumps(parsed_data, ensure_ascii=False, default=_json_default)
        return s[:_SNAPSHOT_JSON_MAX]
    except (TypeError, ValueError):
        return None


def _store_candidate_profile(
    candidate: Candidate,
    parsed_data: dict,
    gap_analysis: dict,
    file_hash: str,
    profile_quality: str,
    file_content: bytes | None = None,
    filename: str | None = None,
    converted_pdf_content: bytes | None = None,
) -> None:
    """Write parsed profile data into the Candidate row."""
    work_exp = parsed_data.get("work_experience", [])
    candidate.resume_file_hash   = file_hash
    if filename:
        candidate.resume_filename = filename
    if file_content:
        candidate.resume_file_data = file_content
    if converted_pdf_content:
        candidate.resume_converted_pdf_data = converted_pdf_content
    candidate.raw_resume_text    = parsed_data.get("raw_text", "")[:100000]  # cap at 100k chars
    candidate.parser_snapshot_json = _parser_snapshot_json(parsed_data)
    candidate.parsed_skills      = json.dumps(parsed_data.get("skills", []), default=_json_default)
    candidate.parsed_education   = json.dumps(parsed_data.get("education", []), default=_json_default)
    candidate.parsed_work_exp    = json.dumps(work_exp, default=_json_default)
    candidate.gap_analysis_json  = json.dumps(gap_analysis, default=_json_default)

    # Truncate current_role and current_company to 255 chars to prevent DB truncation errors
    _raw_role = work_exp[0].get("title", "") if work_exp else None
    _raw_company = work_exp[0].get("company", "") if work_exp else None
    if _raw_role and len(_raw_role) > 255:
        log.warning("Truncating current_role from %d to 255 chars", len(_raw_role))
        _raw_role = _raw_role[:255]
    if _raw_company and len(_raw_company) > 255:
        log.warning("Truncating current_company from %d to 255 chars", len(_raw_company))
        _raw_company = _raw_company[:255]
    candidate.current_role       = _raw_role
    candidate.current_company    = _raw_company

    candidate.total_years_exp    = gap_analysis.get("total_years", 0)
    candidate.profile_quality    = profile_quality
    candidate.profile_updated_at = datetime.now(timezone.utc)
    if not candidate.name:
        candidate.name = parsed_data.get("contact_info", {}).get("name")
    if not candidate.email:
        candidate.email = parsed_data.get("contact_info", {}).get("email")
    if not candidate.phone:
        candidate.phone = parsed_data.get("contact_info", {}).get("phone")


def _get_or_create_candidate(
    db: Session,
    parsed_data: dict,
    tenant_id: int,
    file_hash: str | None = None,
    gap_analysis: dict | None = None,
    profile_quality: str = "medium",
    action: str | None = None,
    file_content: bytes | None = None,
    filename: str | None = None,
    converted_pdf_content: bytes | None = None,
) -> tuple[int, bool]:
    """
    3-layer deduplication. Returns (candidate_id, is_duplicate).

    action values:
      None / unrecognised  → deduplicate, return duplicate_info in result
      "use_existing"       → load stored profile, skip re-parse (caller's responsibility)
      "update_profile"     → update existing candidate's stored profile
      "create_new"         → skip all dedup, always create new row
    """
    contact = parsed_data.get("contact_info", {})
    email   = contact.get("email")
    name    = contact.get("name")
    phone   = contact.get("phone")

    existing: Candidate | None = None

    if action != "create_new":
        # Layer 1 — email match
        if email:
            existing = db.query(Candidate).filter(
                Candidate.email    == email,
                Candidate.tenant_id == tenant_id,
            ).first()

        # Layer 2 — file hash match
        if existing is None and file_hash:
            existing = db.query(Candidate).filter(
                Candidate.resume_file_hash == file_hash,
                Candidate.tenant_id        == tenant_id,
            ).first()

        # Layer 3 — name + phone
        if existing is None and name and phone:
            existing = db.query(Candidate).filter(
                Candidate.name      == name,
                Candidate.phone     == phone,
                Candidate.tenant_id == tenant_id,
            ).first()

    if existing is not None:
        # Update profile when explicitly requested
        if action == "update_profile" and gap_analysis is not None:
            _store_candidate_profile(existing, parsed_data, gap_analysis, file_hash or "", profile_quality, file_content, filename, converted_pdf_content)
        return existing.id, True

    # Create new candidate
    candidate = Candidate(
        tenant_id=tenant_id,
        name=name,
        email=email,
        phone=phone,
    )
    db.add(candidate)
    db.flush()  # get the new id

    if gap_analysis is not None:
        _store_candidate_profile(candidate, parsed_data, gap_analysis, file_hash or "", profile_quality, file_content, filename, converted_pdf_content)

    return candidate.id, False


# ─── Misc helpers ─────────────────────────────────────────────────────────────

def _fallback_result(gap_analysis: dict) -> dict:
    return {
        "fit_score": None, "job_role": None,
        "strengths": [], "weaknesses": [],
        "employment_gaps": gap_analysis.get("employment_gaps", []),
        "education_analysis": None,
        "risk_signals": [{"type": "analysis", "severity": "low",
                          "description": "Automated analysis unavailable — manual review required"}],
        "final_recommendation": "Pending",
        "score_breakdown": {}, "matched_skills": [], "missing_skills": [],
        "risk_level": None, "interview_questions": None,
        "required_skills_count": 0, "work_experience": [], "contact_info": {},
        "jd_analysis": {}, "candidate_profile": {}, "skill_analysis": {},
        "edu_timeline_analysis": {}, "explainability": {}, "adjacent_skills": [],
        "pipeline_errors": ["Pipeline unavailable"],
        "analysis_quality": "low", "narrative_pending": False,
        "deterministic_score": None,
        "decision_explanation": None,
        "jd_domain": None,
        "candidate_domain": None,
        "eligibility": None,
        "deterministic_features": None,
    }


def _resolve_jd(
    job_description: str | None,
    job_file_bytes: bytes | None,
    job_filename: str | None,
) -> str:
    if job_file_bytes and job_filename:
        try:
            extracted = extract_jd_text(job_file_bytes, job_filename)
            if extracted.strip():
                return extracted
        except Exception as e:
            log.warning("Non-critical: JD file extraction failed: %s", e)
    if not (job_description and job_description.strip()):
        raise HTTPException(status_code=400, detail="Job description (text or file) is required")
    return job_description


def _check_jd_length(job_description: str) -> None:
    """Reject JD that is too short to produce meaningful analysis."""
    if len(job_description.split()) < 80:
        raise HTTPException(
            status_code=400,
            detail=(
                "Job description is too brief (under 80 words). "
                "Please include the role title, required skills, and years of experience "
                "for accurate matching."
            ),
        )


def _check_jd_size(job_description: str) -> None:
    """Reject JD that exceeds maximum size limit."""
    if job_description and len(job_description.encode('utf-8')) > MAX_JD_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Job description exceeds maximum size of 50KB"
        )


def _build_phase3_context(
    db: Session,
    tenant_id: int,
    jd_analysis: dict,
    team_id: Optional[str] = None,
) -> Optional[dict]:
    """Build Phase 3 scoring context (outcome patterns, skill trends, team gaps).

    Returns None if no Phase 3 data is available, so scoring falls back to
    the default behaviour.  Failures are caught and logged — never break scoring.
    """
    try:
        all_jd_skills = [s.lower().strip() for s in (
            jd_analysis.get("required_skills", []) +
            jd_analysis.get("nice_to_have_skills", [])
        ) if isinstance(s, str)]

        # 1. Outcome patterns
        outcome_patterns = []
        if all_jd_skills:
            patterns = db.query(OutcomeSkillPattern).filter(
                OutcomeSkillPattern.tenant_id == tenant_id,
                OutcomeSkillPattern.skill_name.in_(all_jd_skills),
            ).all()
            for p in patterns:
                outcome_patterns.append({
                    "skill": p.skill_name,
                    "success_rate": (p.present_in_hired_pct / 100) if p.present_in_hired_pct else 0.5,
                    "sample_size": p.total_outcomes or 0,
                })

        # 2. Skill trends
        skill_trends = []
        if all_jd_skills:
            latest_date = db.query(func.max(SkillTrendSnapshot.period_date)).filter(
                SkillTrendSnapshot.tenant_id == tenant_id,
            ).scalar()
            if latest_date:
                snapshots = db.query(SkillTrendSnapshot).filter(
                    SkillTrendSnapshot.tenant_id == tenant_id,
                    SkillTrendSnapshot.period_date == latest_date,
                    SkillTrendSnapshot.skill_name.in_(all_jd_skills),
                ).all()
                for snap in snapshots:
                    skill_trends.append({
                        "skill": snap.skill_name,
                        "direction": snap.trend_direction or "stable",
                        "growth_pct": snap.growth_pct or 0,
                    })

        # 3. Team gaps
        team_gaps = []
        if team_id:
            try:
                profile = get_team_profile(db, int(team_id), tenant_id)
                if profile and profile.skills_json:
                    team_skills_raw = json.loads(profile.skills_json)
                    team_skill_names = set(
                        e.get("skill", "").lower().strip()
                        for e in team_skills_raw
                        if e.get("skill")
                    )
                    team_gaps = [s for s in all_jd_skills if s not in team_skill_names]
            except Exception as exc:
                log.warning("team_gaps query failed in _build_phase3_context: %s", exc)

        # Only return context if there's something useful
        if outcome_patterns or skill_trends or team_gaps:
            return {
                "team_gaps": team_gaps,
                "skill_trends": skill_trends,
                "outcome_patterns": outcome_patterns,
            }
        return None
    except Exception as e:
        log.warning("Phase 3 context retrieval failed: %s", e)
        return None


# ─── JD Parse Preview helpers ────────────────────────────────────────────────

def _enrich_skills_with_confidence(
    skills: list[str],
    jd_text: str,
    is_nice_to_have: bool = False,
    seniority: str = "mid",
) -> list[dict]:
    """Post-process skill list to add confidence/source and proficiency metadata
    based on linguistic cues in the original JD text.

    Heuristic rules:
      - Nice-to-have near preferred/bonus/plus cues  → high / preferred_section
      - Required near must-have/required/essential    → high / explicit_requirement
      - Inferred from Qualifications/Requirements hdr → medium / qualifications_section
      - Default                                         → medium / inferred
    """
    jd_lower = jd_text.lower()

    # Pre-compute section boundaries for "Qualifications" / "Requirements" headers
    _SECTION_HEADERS = [
        "qualifications", "requirements", "what you'll need",
        "what we're looking for", "job requirements",
        "minimum qualifications", "basic qualifications",
        "preferred qualifications", "desired qualifications",
    ]
    section_ranges: list[tuple[int, int]] = []
    for hdr in _SECTION_HEADERS:
        idx = jd_lower.find(hdr)
        if idx >= 0:
            # Section extends to the next header-like line or end of text
            end = len(jd_text)
            for nxt in _SECTION_HEADERS:
                nxt_idx = jd_lower.find(nxt, idx + len(hdr))
                if nxt_idx > idx and nxt_idx < end:
                    end = nxt_idx
            section_ranges.append((idx, end))

    def _skill_in_section(skill_name: str) -> bool:
        """Check if the skill appears within a known section header range."""
        s_lower = skill_name.lower()
        for start, end in section_ranges:
            if s_lower in jd_lower[start:end]:
                return True
        return False

    enriched = []
    for skill in skills:
        skill_lower = skill.lower()

        # Determine surrounding context (±120 chars around the skill mention)
        pos = jd_lower.find(skill_lower)
        context = ""
        if pos >= 0:
            ctx_start = max(0, pos - 120)
            ctx_end = min(len(jd_text), pos + len(skill_lower) + 120)
            context = jd_lower[ctx_start:ctx_end].lower()

        if is_nice_to_have:
            # Nice-to-have: check for preferred/bonus cues
            if any(cue in context for cue in NICE_TO_HAVE_CUES):
                confidence, source = "high", "preferred_section"
            elif _skill_in_section(skill):
                confidence, source = "medium", "qualifications_section"
            else:
                confidence, source = "medium", "inferred"
        else:
            # Required: check for must-have/required/essential cues
            if any(cue in context for cue in MUST_HAVE_CUES):
                confidence, source = "high", "explicit_requirement"
            elif _skill_in_section(skill):
                confidence, source = "medium", "qualifications_section"
            else:
                confidence, source = "medium", "inferred"

        proficiency = _estimate_skill_proficiency(
            skill, seniority, jd_text, is_nice_to_have=is_nice_to_have,
        )
        enriched.append({
            "skill": skill,
            "confidence": confidence,
            "source": source,
            "proficiency_expected": proficiency,
        })

    return enriched


# ─── Proficiency estimation ──────────────────────────────────────────────────

PROFICIENCY_CUE_MAP: dict[str, list[str]] = {
    "expert": [
        "expert in", "deep knowledge of", "mastery of",
        "extensive experience with", "8+ years", "10+ years",
        "expert-level", "deep expertise",
    ],
    "advanced": [
        "proficient in", "solid experience", "strong knowledge",
        "strong background", "5+ years", "6+ years", "7+ years",
        "proven track record with", "advanced knowledge",
        "hands-on experience",
    ],
    "intermediate": [
        "working knowledge of", "experience with", "good understanding",
        "2+ years", "3+ years", "4+ years", "comfortable with",
    ],
    "basic": [
        "basic understanding of", "exposure to", "awareness of",
        "familiarity with", "knowledge of", "1+ year",
        "some experience",
    ],
}

_PROFICIENCY_RANK = {"basic": 0, "intermediate": 1, "advanced": 2, "expert": 3}

_SENIORITY_DEFAULT_PROFICIENCY: dict[str, str] = {
    "junior": "basic",
    "mid": "intermediate",
    "senior": "advanced",
    "lead": "expert",
    "principal": "expert",
}


def _estimate_skill_proficiency(
    skill: str,
    seniority: str,
    jd_text: str,
    is_nice_to_have: bool = False,
) -> str:
    """Estimate the expected proficiency level for a skill based on
    linguistic cues in the JD text and the role's seniority.

    Priority order:
      1. Cue-based detection (±150 chars around skill mention)
      2. Seniority-based default
      3. Nice-to-have cap (one level below seniority default)

    Returns one of: "basic", "intermediate", "advanced", "expert".
    """
    jd_lower = jd_text.lower()
    skill_lower = skill.lower()
    pos = jd_lower.find(skill_lower)

    # --- Step 1: Try cue-based detection around the skill mention ---
    if pos >= 0:
        ctx_start = max(0, pos - 150)
        ctx_end = min(len(jd_text), pos + len(skill_lower) + 150)
        context = jd_lower[ctx_start:ctx_end]

        for level in ("expert", "advanced", "intermediate", "basic"):
            if any(cue in context for cue in PROFICIENCY_CUE_MAP[level]):
                proficiency = level
                break
        else:
            proficiency = None
    else:
        proficiency = None

    # --- Step 2: Fall back to seniority-based default ---
    if proficiency is None:
        proficiency = _SENIORITY_DEFAULT_PROFICIENCY.get(seniority.lower(), "intermediate")

    # --- Step 3: Nice-to-have cap — one level below seniority default ---
    if is_nice_to_have:
        seniority_default = _SENIORITY_DEFAULT_PROFICIENCY.get(
            seniority.lower(), "intermediate"
        )
        cap_rank = max(_PROFICIENCY_RANK[seniority_default] - 1, 0)
        if _PROFICIENCY_RANK[proficiency] > cap_rank:
            proficiency = [k for k, v in _PROFICIENCY_RANK.items() if v == cap_rank][0]

    return proficiency


def _get_excluded_skills(
    jd_text: str,
    required_skills: list[str],
    nice_to_have_skills: list[str],
) -> list[str]:
    """Return skills that were detected in the JD but excluded because they
    are generic soft skills (per GENERIC_SOFT_SKILLS constant)."""
    jd_lower = jd_text.lower()
    excluded: list[str] = []
    for soft in GENERIC_SOFT_SKILLS:
        if soft in jd_lower and soft not in (s.lower() for s in required_skills) and soft not in (s.lower() for s in nice_to_have_skills):
            excluded.append(soft)
    return excluded


def _get_suggested_additions(
    job_function: str,
    required_skills: list[str],
    nice_to_have_skills: list[str],
    role_title: str,
) -> list[str]:
    """Return common skills for the detected job_function that are not already
    in required_skills or nice_to_have_skills.

    Tries O*NET first; falls back to JOB_FUNCTION_SKILL_TAXONOMY mapping.
    """
    existing = {s.lower() for s in required_skills + nice_to_have_skills}

    # ── Attempt O*NET lookup ───────────────────────────────────────────────
    try:
        from app.backend.services.onet.onet_validator import ONETValidator
        validator = ONETValidator()
        if validator.available and role_title:
            occ = validator.resolve_occupation(role_title)
            if occ:
                occ_skills = validator.get_expected_skills(occ["soc_code"])
                hot_skills = [
                    s["skill_name"]
                    for s in occ_skills
                    if s.get("is_hot_technology") or s.get("is_in_demand")
                ]
                suggestions = [
                    s for s in hot_skills
                    if s.lower() not in existing
                ]
                if suggestions:
                    return suggestions[:8]
    except Exception:
        pass  # Fall back to taxonomy mapping

    # ── Fallback: JOB_FUNCTION_SKILL_TAXONOMY mapping ──────────────────────
    taxonomy = JOB_FUNCTION_SKILL_TAXONOMY.get(job_function, {})
    core = taxonomy.get("core_skills", [])
    adjacent = taxonomy.get("adjacent_skills", [])
    candidates = core + adjacent
    suggestions = [s for s in candidates if s.lower() not in existing]
    return suggestions[:8]


def _enrich_skills_with_market_data(
    skills_list: list, role_title: str
) -> tuple[list, dict]:
    """Enrich skills with O*NET market intelligence (hot/demand flags, category).

    Returns (enriched_skills_list, market_summary).
    If O*NET is unavailable, market fields are set to None and market_summary
    contains an error message.
    """
    try:
        from app.backend.services.onet.onet_validator import ONETValidator

        validator = ONETValidator()
        if not validator.available or not role_title:
            raise RuntimeError("O*NET unavailable or no role title")

        # Extract skill names from the enriched skill objects
        skill_names = [
            s["skill"] for s in skills_list if isinstance(s, dict) and s.get("skill")
        ]

        # Batch validate against the role title's occupation
        batch_result = validator.validate_skills_batch(skill_names, role_title)

        # Build a commodity_title lookup from occupation skills
        # (validate_skills_batch doesn't include commodity_title)
        commodity_lookup: dict[str, str] = {}
        soc_code = batch_result.get("soc_code")
        if soc_code:
            occ_skills = validator.get_expected_skills(soc_code)
            for occ_s in occ_skills:
                commodity_lookup[occ_s["skill_name"].lower()] = (
                    occ_s.get("commodity_title") or "Unclassified"
                )

        # Index validation results by skill name (case-insensitive)
        validated_lookup: dict[str, dict] = {}
        for v in batch_result.get("validated", []):
            if v.get("skill"):
                validated_lookup[v["skill"].lower()] = v

        # Enrich each skill with market flags
        hot_count = 0
        in_demand_count = 0
        rare_skills: list[str] = []

        for skill_obj in skills_list:
            skill_name = skill_obj.get("skill", "")
            key = skill_name.lower()

            v = validated_lookup.get(key)
            if v and v.get("recognized"):
                skill_obj["is_hot"] = v["is_hot"]
                skill_obj["is_in_demand"] = v["is_in_demand"]
                skill_obj["category"] = commodity_lookup.get(key, "Unclassified")

                if v["is_hot"]:
                    hot_count += 1
                if v["is_in_demand"]:
                    in_demand_count += 1
            else:
                # Not found in O*NET
                skill_obj["is_hot"] = False
                skill_obj["is_in_demand"] = False
                skill_obj["category"] = "Unclassified"
                rare_skills.append(skill_name)

        # Compute market alignment ratio
        total = max(len(skills_list), 1)
        demand_ratio = in_demand_count / total
        if demand_ratio > 0.7:
            alignment = "high"
        elif demand_ratio >= 0.4:
            alignment = "medium"
        else:
            alignment = "low"

        market_summary = {
            "hot_skills_count": hot_count,
            "in_demand_count": in_demand_count,
            "rare_skills": rare_skills,
            "market_alignment": alignment,
        }

        return skills_list, market_summary

    except Exception:
        # O*NET unavailable — set all market fields to None
        for skill_obj in skills_list:
            skill_obj["is_hot"] = None
            skill_obj["is_in_demand"] = None
            skill_obj["category"] = None

        market_summary = {"error": "Market data unavailable"}
        return skills_list, market_summary


# ─── JD Parse Preview Endpoint ────────────────────────────────────────────────

@router.post("/jd/parse-preview")
async def jd_parse_preview(
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    team_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview parsed JD structure with confidence metadata per skill.

    Accepts either ``job_description`` text or a ``job_file`` upload.
    Reuses the existing JD parser pipeline (with caching via JdCache).
    Returns enriched skill lists with confidence/source, excluded soft skills,
    and suggested additions based on the detected job function.
    """
    # Resolve JD text from form or file
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        if len(jd_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Job description file too large (max 5MB)")
        jd_name = job_file.filename

    jd_text = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(jd_text)
    _check_jd_size(jd_text)

    # Use the same caching logic as /api/analyze
    jd_analysis = _get_or_cache_jd(db, jd_text)

    # Enrich skills with confidence/source metadata
    seniority = jd_analysis.get("seniority", "mid")
    required_skills_enriched = _enrich_skills_with_confidence(
        jd_analysis.get("required_skills", []),
        jd_text,
        is_nice_to_have=False,
        seniority=seniority,
    )
    nice_to_have_enriched = _enrich_skills_with_confidence(
        jd_analysis.get("nice_to_have_skills", []),
        jd_text,
        is_nice_to_have=True,
        seniority=seniority,
    )

    # Compute excluded skills (detected but filtered as generic soft skills)
    excluded_skills = _get_excluded_skills(
        jd_text,
        jd_analysis.get("required_skills", []),
        jd_analysis.get("nice_to_have_skills", []),
    )

    # Compute suggested additions from O*NET or taxonomy fallback
    suggested_additions = _get_suggested_additions(
        job_function=jd_analysis.get("job_function", "other"),
        required_skills=jd_analysis.get("required_skills", []),
        nice_to_have_skills=jd_analysis.get("nice_to_have_skills", []),
        role_title=jd_analysis.get("role_title", ""),
    )

    # Enrich skills with O*NET market intelligence (hot/demand flags, category)
    # Both lists share the same skill objects, so in-place enrichment propagates
    all_enriched_skills = required_skills_enriched + nice_to_have_enriched
    _, market_summary = _enrich_skills_with_market_data(
        all_enriched_skills,
        jd_analysis.get("role_title", ""),
    )

    # Score JD quality (pure Python, no LLM)
    jd_quality = score_jd_quality(jd_text, jd_analysis)

    # ── Phase 3 insights: historical, team context, skill trends ────────────
    tenant_id = current_user.tenant_id
    all_jd_skills = [s.lower().strip() for s in (
        jd_analysis.get("required_skills", []) +
        jd_analysis.get("nice_to_have_skills", [])
    ) if isinstance(s, str)]

    # 1. Historical insights — OutcomeSkillPattern correlations
    historical_insights = {}
    try:
        skill_patterns = db.query(OutcomeSkillPattern).filter(
            OutcomeSkillPattern.tenant_id == tenant_id,
            OutcomeSkillPattern.skill_name.in_(all_jd_skills),
        ).order_by(OutcomeSkillPattern.correlation_score.desc()).limit(20).all()

        patterns_list = []
        for p in skill_patterns:
            # Derive success_rate from present_in_hired_pct (0-100 → 0.0-1.0)
            success_rate = round((p.present_in_hired_pct or 0) / 100, 2) if p.present_in_hired_pct else None
            patterns_list.append({
                "skill": p.skill_name,
                "success_rate": success_rate,
                "sample_size": p.sample_size,
                "correlation": p.correlation_score,
            })
        historical_insights = {"patterns": patterns_list}
    except Exception as exc:
        log.warning("historical_insights query failed: %s", exc)
        historical_insights = {"patterns": []}

    # 2. Team context — team has / gaps if team_id provided
    team_context = None
    if team_id:
        try:
            profile = get_team_profile(db, int(team_id), tenant_id)
            if profile and profile.skills_json:
                team_skills_raw = json.loads(profile.skills_json)
                team_skill_names = set(
                    e.get("skill", "").lower().strip()
                    for e in team_skills_raw
                    if e.get("skill")
                )
                team_has = [
                    s for s in all_jd_skills if s in team_skill_names
                ]
                team_gaps = [
                    s for s in all_jd_skills if s not in team_skill_names
                ]
                team_context = {
                    "team_has": team_has,
                    "team_gaps": team_gaps,
                }
            else:
                team_context = {"team_has": [], "team_gaps": all_jd_skills}
        except Exception as exc:
            log.warning("team_context query failed: %s", exc)
            team_context = {"team_has": [], "team_gaps": []}

    # 3. Skill trends — direction + growth_pct from SkillTrendSnapshot
    skill_trends = []
    try:
        if all_jd_skills:
            # Get latest period date for this tenant
            latest_date = db.query(func.max(SkillTrendSnapshot.period_date)).filter(
                SkillTrendSnapshot.tenant_id == tenant_id,
            ).scalar()

            if latest_date:
                snapshots = db.query(SkillTrendSnapshot).filter(
                    SkillTrendSnapshot.tenant_id == tenant_id,
                    SkillTrendSnapshot.period_date == latest_date,
                    SkillTrendSnapshot.skill_name.in_(all_jd_skills),
                ).all()

                for snap in snapshots:
                    skill_trends.append({
                        "skill": snap.skill_name,
                        "direction": snap.trend_direction or "stable",
                        "growth_pct": snap.growth_pct or 0,
                    })
    except Exception as exc:
        log.warning("skill_trends query failed: %s", exc)
        skill_trends = []

    return {
        "role_title": jd_analysis.get("role_title", ""),
        "seniority": jd_analysis.get("seniority", "mid"),
        "domain": jd_analysis.get("domain", "other"),
        "job_function": jd_analysis.get("job_function", "other"),
        "required_years": jd_analysis.get("required_years", 0),
        "required_skills": required_skills_enriched,
        "nice_to_have_skills": nice_to_have_enriched,
        "excluded_skills": excluded_skills,
        "suggested_additions": suggested_additions,
        "key_responsibilities": jd_analysis.get("key_responsibilities", []),
        "market_summary": market_summary,
        "jd_quality": jd_quality,
        "historical_insights": historical_insights,
        "team_context": team_context,
        "skill_trends": skill_trends,
    }


def _check_scoring_weights_size(scoring_weights: str | None) -> None:
    """Reject scoring_weights that exceeds maximum size limit."""
    if scoring_weights and len(scoring_weights.encode('utf-8')) > MAX_SCORING_WEIGHTS_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Scoring weights exceed maximum size of 4KB"
        )


async def _parse_resume_with_doc_conversion(content: bytes, filename: str) -> tuple[dict, bytes | None]:
    """Parse resume with automatic DOC-to-PDF conversion for better accuracy.

    Returns:
        (parsed_data, converted_pdf_bytes or None)
    """
    ext = os.path.splitext(filename.lower())[1]
    pdf_bytes = None

    if ext == ".doc":
        pdf_bytes = await asyncio.to_thread(convert_to_pdf, content, filename)
        if pdf_bytes:
            log.info("DOC converted to PDF (%d bytes), parsing from PDF for better accuracy", len(pdf_bytes))
            parsed_data = await asyncio.to_thread(parse_resume, pdf_bytes, "converted.pdf")
            return parsed_data, pdf_bytes
        log.warning("DOC-to-PDF conversion failed for %s, falling back to legacy parser", filename)

    parsed_data = await asyncio.to_thread(parse_resume, content, filename)
    return parsed_data, pdf_bytes


async def _process_single_resume(
    content: bytes,
    filename: str,
    job_description: str,
    scoring_weights: dict | None,
    db: Session | None = None,
) -> dict:
    """Core analysis logic — parse in thread, run Python scoring, return result.

    Returns Python scoring results with a fallback narrative. The caller
    (batch endpoint) is responsible for spawning a background LLM task
    after persisting the ScreeningResult to DB.
    """
    # Parse resume in thread pool (blocks event loop otherwise for large PDFs)
    pdf_bytes = None
    try:
        parsed_data, pdf_bytes = await _parse_resume_with_doc_conversion(content, filename)
    except ValueError as e:
        # Scanned PDF or unreadable file — return graceful error
        return {
            **_fallback_result({}),
            "pipeline_errors": [str(e)],
            "analysis_quality": "low",
        }
    except Exception as e:
        log.warning("Resume parse error for %s: %s", filename, e)
        return {
            **_fallback_result({}),
            "pipeline_errors": [f"Parse error: {str(e)}"],
        }

    work_exp     = parsed_data.get("work_experience", [])
    gap_analysis = analyze_gaps(work_exp)

    # Cached JD parse
    jd_analysis = None
    if db is not None:
        try:
            jd_analysis = _get_or_cache_jd(db, job_description)
        except Exception as e:
            log.warning("Non-critical: JD cache fetch failed: %s", e)

    try:
        from app.backend.services.hybrid_pipeline import (
            _run_python_phase,
            _build_fallback_narrative,
            _merge_llm_into_result,
        )
        result = _run_python_phase(
            resume_text=parsed_data["raw_text"],
            job_description=job_description,
            parsed_data=parsed_data,
            gap_analysis=gap_analysis,
            scoring_weights=scoring_weights,
            jd_analysis=jd_analysis,
        )
        # Preserve internal _scores before merge (needed for background LLM spawn)
        _scores = result.get("_scores", {})
        fallback = _build_fallback_narrative(result, result.get("skill_analysis", {}))
        result = _merge_llm_into_result(result, fallback)
        result["_scores"] = _scores
        result["narrative_pending"] = True
        log.info("Fast batch path for %s: fit_score=%s (LLM deferred)",
                 filename, result.get("fit_score"))
    except Exception as e:
        log.warning("Pipeline error for %s: %s", filename, e)
        result = _fallback_result(gap_analysis)
        result["pipeline_errors"] = [f"Pipeline error: {str(e)}"]

    result["_parsed_data"]  = parsed_data
    result["_gap_analysis"] = gap_analysis
    result["_pdf_bytes"]    = pdf_bytes  # DOC-to-PDF conversion result (if applicable)
    return result


# ─── Weight Suggestion Endpoint ───────────────────────────────────────────────

@router.post("/analyze/suggest-weights")
async def suggest_weights_endpoint(
    job_description: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-powered weight suggestion based on job description."""
    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(status_code=400, detail="Job description too short")

    from app.backend.services.weight_suggester import suggest_weights_for_jd, create_fallback_suggestion

    try:
        suggestion = suggest_weights_for_jd(job_description)
        if suggestion is None:
            # Return fallback suggestion instead of error
            suggestion = create_fallback_suggestion(job_description)
        return suggestion
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Weight suggestion failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate weight suggestions")


# ─── Single resume analysis (non-streaming, JSON response) ────────────────────

def _check_and_increment_usage(db: Session, tenant_id: int, user_id: int, quantity: int = 1) -> tuple[bool, str]:
    """Check usage limits and increment counter atomically. Returns (allowed, message).
    
    Uses atomic UPDATE to prevent race conditions:
    - For limited plans: UPDATE ... SET count = count + 1 WHERE count + quantity <= limit
    - Checks affected rows to determine if limit was reached
    """
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return False, "Tenant not found"
    
    # Ensure monthly reset (this modifies tenant in memory, will be committed with usage)
    _ensure_monthly_reset(tenant)
    db.flush()  # Flush reset changes if any
    
    # Get plan limits
    plan = tenant.plan
    if not plan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
    
    analyses_limit = None
    if plan:
        limits = _get_plan_limits(plan)
        analyses_limit = limits.get("analyses_per_month", 20)
    
    # If unlimited, just increment without check
    if analyses_limit is None or analyses_limit < 0:
        success = record_usage(db, tenant_id, user_id, "resume_analysis", quantity)
        if not success:
            return False, "Failed to record usage"
        return True, ""
    
    # Atomic increment with limit check using raw SQL UPDATE
    # This prevents race conditions where two concurrent requests both read the same count
    result = db.execute(
        update(Tenant)
        .where(
            Tenant.id == tenant_id,
            Tenant.analyses_count_this_month + quantity <= analyses_limit
        )
        .values(
            analyses_count_this_month=Tenant.analyses_count_this_month + quantity
        )
        .execution_options(synchronize_session=False)
    )
    
    # Check if the update affected any rows
    if result.rowcount == 0:
        # Limit was reached - get current count for error message
        db.rollback()
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if tenant:
            _ensure_monthly_reset(tenant)
            remaining = analyses_limit - tenant.analyses_count_this_month
            return False, f"Monthly analysis limit exceeded. Remaining: {remaining}, Requested: {quantity}. Please upgrade your plan."
        return False, "Monthly analysis limit exceeded. Please upgrade your plan."
    
    # Log the usage
    from app.backend.models.db_models import UsageLog
    usage_log = UsageLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action="resume_analysis",
        quantity=quantity,
        details=None,
    )
    db.add(usage_log)
    db.commit()
    
    return True, ""


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    skill_overrides: str = Form(None),
    action: str = Form(None),   # use_existing | update_profile | create_new | None
    template_id: Optional[int] = Form(None),
    team_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Non-streaming analysis endpoint.
    
    Returns Python scoring results immediately with narrative_pending=True.
    LLM narrative is generated in background and can be polled via
    GET /api/analysis/{id}/narrative.
    """
    # ─── HARD QUOTA CHECK (before any work) ───────────────────────────────────
    quota = check_quota(current_user.tenant_id, db)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": "Monthly analysis quota exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "plan": quota["plan"],
            },
        )

    # ─── VALIDATE FILES FIRST (before incrementing usage) ─────────────────────
    # Validate file extension
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    # Read and validate resume file size
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    # Validate file content matches extension (magic bytes)
    _validate_file_content(content, resume.filename)

    # Read and validate JD file if provided
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        if len(jd_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Job description file too large (max 5MB)")
        jd_name = job_file.filename

    # Resolve and validate job description
    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)
    _check_jd_size(job_description)
    
    # ─── CHECK AND INCREMENT USAGE (after validation) ─────────────────────────
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, 1)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    # Validate scoring_weights size before parsing
    _check_scoring_weights_size(scoring_weights)

    # Validate skill_overrides size before parsing
    if skill_overrides and len(skill_overrides.encode('utf-8')) > MAX_SCORING_WEIGHTS_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Skill overrides exceed maximum size of 4KB"
        )

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)
    
    # Parse skill_overrides JSON (accepts strings or proficiency dicts)
    parsed_skill_overrides = None
    if skill_overrides:
        try:
            parsed_skill_overrides = json.loads(skill_overrides)
            # Validate structure: must contain lists of strings or proficiency dicts
            if not isinstance(parsed_skill_overrides, dict):
                raise ValueError("skill_overrides must be a JSON object")
            for key in ("required_skills", "nice_to_have_skills"):
                if key in parsed_skill_overrides:
                    if not isinstance(parsed_skill_overrides[key], list):
                        raise ValueError(f"skill_overrides.{key} must be a list")
                    for item in parsed_skill_overrides[key]:
                        if isinstance(item, str):
                            continue  # Plain string — backward compatible
                        if isinstance(item, dict) and isinstance(item.get("skill"), str):
                            prof = item.get("proficiency")
                            if prof is not None and not isinstance(prof, str):
                                raise ValueError(
                                    f"skill_overrides.{key} proficiency must be a string"
                                )
                            continue
                        raise ValueError(
                            f"skill_overrides.{key} items must be strings or "
                            f'{{"skill": "...", "proficiency": "..."}} dicts'
                        )
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("Non-critical: Invalid skill_overrides JSON, ignoring: %s", e)
            parsed_skill_overrides = None
    
    # If no explicit weights provided, load tenant default weights
    if not weights:
        try:
            tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
            if tenant and tenant.scoring_weights:
                weights = json.loads(tenant.scoring_weights)
                log.info("Loaded tenant default weights for tenant %s", current_user.tenant_id)
        except Exception as e:
            log.warning("Non-critical: Failed to load tenant weights, using defaults: %s", e)

    file_hash = hashlib.md5(content).hexdigest()

    # Handle "use_existing" — skip re-analysis if candidate already in DB
    if action == "use_existing":
        existing = (
            db.query(Candidate)
            .filter(
                Candidate.resume_file_hash == file_hash,
                Candidate.tenant_id        == current_user.tenant_id,
            )
            .first()
        ) or (
            db.query(Candidate)
            .filter(
                Candidate.email     == None,
                Candidate.tenant_id == current_user.tenant_id,
            )
            .first()  # fallback — will be refined below
        )
        # If found with stored profile, run scoring-only
        if existing and existing.raw_resume_text and existing.parsed_skills:
            parsed_data = {
                "raw_text":       existing.raw_resume_text,
                "skills":         json.loads(existing.parsed_skills or "[]"),
                "education":      json.loads(existing.parsed_education or "[]"),
                "work_experience": json.loads(existing.parsed_work_exp or "[]"),
                "contact_info":   {"name": existing.name, "email": existing.email,
                                   "phone": existing.phone},
            }
            gap_analysis = json.loads(existing.gap_analysis_json or "{}")
            jd_analysis  = _get_or_cache_jd(db, job_description)
            _apply_skill_overrides(jd_analysis, parsed_skill_overrides)

            # Build Phase 3 context for scoring integration
            phase3_context = _build_phase3_context(
                db, current_user.tenant_id, jd_analysis, team_id=team_id,
            )

            # Create result record first for background LLM
            db_result = ScreeningResult(
                tenant_id=current_user.tenant_id,
                candidate_id=existing.id,
                resume_text=existing.raw_resume_text,
                jd_text=job_description,
                parsed_data=json.dumps(parsed_data, default=_json_default),
                analysis_result="{}",  # Placeholder
                role_template_id=template_id,
            )
            db.add(db_result)
            db.commit()
            db.refresh(db_result)

            result = await run_hybrid_pipeline(
                resume_text=existing.raw_resume_text,
                job_description=job_description,
                parsed_data=parsed_data,
                gap_analysis=gap_analysis,
                scoring_weights=weights,
                jd_analysis=jd_analysis,
                screening_result_id=db_result.id,
                tenant_id=current_user.tenant_id,
                phase3_context=phase3_context,
            )
            
            # Update result with analysis
            db_result.analysis_result = json.dumps(result, default=_json_default)
            db.commit()
            
            result["result_id"]      = db_result.id
            result["analysis_id"]    = db_result.id   # Add this line
            result["candidate_id"]   = existing.id
            result["candidate_name"] = existing.name
            return result

    t_start = time.time()

    # Parse resume first - handle parse errors gracefully
    try:
        parsed_data, pdf_bytes = await _parse_resume_with_doc_conversion(content, resume.filename)
    except ValueError as e:
        # Scanned PDF or unreadable file — return graceful error
        log.warning(f"Resume parse failed for {resume.filename}: {e}")
        parsed_data = {
            "raw_text": "",
            "skills": [],
            "education": [],
            "work_experience": [],
            "contact_info": {},
        }
        pdf_bytes = None
        # Continue with fallback - will set analysis_quality to "low"
    except Exception as e:
        log.warning(f"Resume parse error for {resume.filename}: {e}")
        parsed_data = {
            "raw_text": "",
            "skills": [],
            "education": [],
            "work_experience": [],
            "contact_info": {},
        }
        pdf_bytes = None

    gap_analysis = analyze_gaps(parsed_data.get("work_experience", []))
    jd_analysis  = _get_or_cache_jd(db, job_description)
    _apply_skill_overrides(jd_analysis, parsed_skill_overrides)

    # Build Phase 3 context for scoring integration
    phase3_context = _build_phase3_context(
        db, current_user.tenant_id, jd_analysis, team_id=team_id,
    )

    # Create candidate and result BEFORE pipeline (for background LLM)
    candidate_id, is_dup = _get_or_create_candidate(
        db, parsed_data, current_user.tenant_id,
        file_hash=file_hash,
        gap_analysis=gap_analysis,
        profile_quality="medium",  # Will be updated
        action=action,
        file_content=content,
        filename=resume.filename,
        converted_pdf_content=pdf_bytes,
    )

    db_result = ScreeningResult(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        resume_text=parsed_data.get("raw_text", ""),
        jd_text=job_description,
        parsed_data=json.dumps(parsed_data, default=_json_default),
        analysis_result="{}",  # Placeholder — will be updated
        role_template_id=template_id,
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    # Run pipeline with background LLM
    result = await run_hybrid_pipeline(
        resume_text=parsed_data["raw_text"],
        job_description=job_description,
        parsed_data=parsed_data,
        gap_analysis=gap_analysis,
        scoring_weights=weights,
        jd_analysis=jd_analysis,
        screening_result_id=db_result.id,
        tenant_id=current_user.tenant_id,
        phase3_context=phase3_context,
    )

    # Update result in DB
    db_result.analysis_result = json.dumps(result, default=_json_default)
    
    # Update candidate profile quality
    _store_candidate_profile(
        db.get(Candidate, candidate_id) or db.query(Candidate).filter(Candidate.id == candidate_id).first(),
        parsed_data,
        gap_analysis,
        file_hash,
        result.get("analysis_quality", "medium"),
        file_content=content,
        filename=resume.filename,
    )
    db.commit()

    result["result_id"]    = db_result.id
    result["analysis_id"]  = db_result.id   # Add this line
    result["candidate_id"] = candidate_id

    # Resolve name: candidate.name (possibly edited) takes priority over parsed/analysis data
    _cand_row = db.get(Candidate, candidate_id)
    result["candidate_name"] = (
        (_cand_row.name if _cand_row and _cand_row.name else None)
        or (parsed_data.get("contact_info", {}).get("name") or "").strip()
        or (result.get("candidate_profile", {}).get("name") or "").strip()
        or None
    )

    if is_dup and action not in ("update_profile", "create_new"):
        existing = db.get(Candidate, candidate_id)
        if existing:
            result["duplicate_candidate"] = _build_duplicate_info(db, existing).model_dump(mode='json')

    log.info(json.dumps({
        "event":       "analysis_complete",
        "tenant_id":   current_user.tenant_id,
        "filename":    resume.filename,
        "skills_found": len(result.get("matched_skills", [])),
        "fit_score":   result.get("fit_score"),
        "llm_pending": result.get("narrative_pending", False),
        "quality":     result.get("analysis_quality"),
        "total_ms":    int((time.time() - t_start) * 1000),
    }, default=_json_default))

    # Webhook dispatch — never let webhook failure affect analysis
    try:
        from app.backend.services.webhook_service import dispatch_event_background
        dispatch_event_background(None, current_user.tenant_id, "analysis.completed", {"result_id": db_result.id})
    except Exception:
        pass

    return result


# ─── Single resume analysis (SSE streaming) ───────────────────────────────────

@router.post("/analyze/stream")
async def analyze_stream_endpoint(
    request: Request,
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    skill_overrides: str = Form(None),
    action: str = Form(None),
    template_id: Optional[int] = Form(None),
    team_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE streaming version of /analyze.

    With background LLM processing:
      1. Creates ScreeningResult immediately with Python scores
      2. Yields results with narrative_pending=True and analysis_id for polling
      3. LLM runs in background and writes to DB when done
      4. Frontend polls GET /api/analysis/{id}/narrative for LLM narrative

    Emits:
      data: {"stage": "parsing",  "result": {...Python scores...}}   — within 2s
      data: {"stage": "complete", "result": {...result with analysis_id...}}
      data: [DONE]
    """
    # ─── HARD QUOTA CHECK (before any work) ───────────────────────────────────
    quota = check_quota(current_user.tenant_id, db)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": "Monthly analysis quota exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "plan": quota["plan"],
            },
        )

    # ─── VALIDATE FILES FIRST (before incrementing usage) ─────────────────────
    # Validate file extension
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    # Read and validate resume file size
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    # Validate file content matches extension (magic bytes)
    _validate_file_content(content, resume.filename)

    # Read JD file if provided
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name  = job_file.filename

    # Resolve and validate job description
    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)
    _check_jd_size(job_description)
    
    # ─── CHECK AND INCREMENT USAGE (after validation) ─────────────────────────
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, 1)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    # Validate scoring_weights size before parsing
    _check_scoring_weights_size(scoring_weights)

    # Validate skill_overrides size before parsing
    if skill_overrides and len(skill_overrides.encode('utf-8')) > MAX_SCORING_WEIGHTS_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Skill overrides exceed maximum size of 4KB"
        )

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
            log.info("Received custom weights from frontend: %s", weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)

    # Parse skill_overrides JSON (accepts strings or proficiency dicts)
    parsed_skill_overrides = None
    if skill_overrides:
        try:
            parsed_skill_overrides = json.loads(skill_overrides)
            # Validate structure: must contain lists of strings or proficiency dicts
            if not isinstance(parsed_skill_overrides, dict):
                raise ValueError("skill_overrides must be a JSON object")
            for key in ("required_skills", "nice_to_have_skills"):
                if key in parsed_skill_overrides:
                    if not isinstance(parsed_skill_overrides[key], list):
                        raise ValueError(f"skill_overrides.{key} must be a list")
                    for item in parsed_skill_overrides[key]:
                        if isinstance(item, str):
                            continue  # Plain string — backward compatible
                        if isinstance(item, dict) and isinstance(item.get("skill"), str):
                            prof = item.get("proficiency")
                            if prof is not None and not isinstance(prof, str):
                                raise ValueError(
                                    f"skill_overrides.{key} proficiency must be a string"
                                )
                            continue
                        raise ValueError(
                            f"skill_overrides.{key} items must be strings or "
                            f'{{"skill": "...", "proficiency": "..."}} dicts'
                        )
        except (json.JSONDecodeError, ValueError) as e:
            log.warning("Non-critical: Invalid skill_overrides JSON, ignoring: %s", e)
            parsed_skill_overrides = None
    
    # If no explicit weights provided, load tenant default weights
    if not weights:
        try:
            tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
            if tenant and tenant.scoring_weights:
                weights = json.loads(tenant.scoring_weights)
                log.info("Loaded tenant default weights for tenant %s: %s", current_user.tenant_id, weights)
        except Exception as e:
            log.warning("Non-critical: Failed to load tenant weights, using defaults: %s", e)
    
    if weights:
        log.info("Final weights to be used for scoring: %s", weights)
    else:
        log.info("No custom weights provided, will use system defaults")

    file_hash = hashlib.md5(content).hexdigest()
    tenant_id = current_user.tenant_id
    t_start   = time.time()

    # Parse resume and JD in thread pool before entering the generator
    try:
        parsed_data, pdf_bytes = await _parse_resume_with_doc_conversion(content, resume.filename)
    except Exception as parse_exc:
        error_msg = str(parse_exc)
        async def _error_stream():
            error = {"stage": "error", "result": {"message": error_msg}}
            yield f"data: {json.dumps(error, default=_json_default)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_error_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    gap_analysis = analyze_gaps(parsed_data.get("work_experience", []))
    jd_analysis  = _get_or_cache_jd(db, job_description)
    _apply_skill_overrides(jd_analysis, parsed_skill_overrides)

    # Build Phase 3 context for scoring integration
    phase3_context = _build_phase3_context(
        db, tenant_id, jd_analysis, team_id=team_id,
    )

    # Pre-create candidate and ScreeningResult BEFORE streaming
    # This gives us an ID to pass to the background LLM task
    candidate_id, is_dup = _get_or_create_candidate(
        db, parsed_data, tenant_id,
        file_hash=file_hash,
        gap_analysis=gap_analysis,
        profile_quality="medium",  # Will be updated after pipeline
        action=action,
        file_content=content,
        filename=resume.filename,
        converted_pdf_content=pdf_bytes,
    )
    
    # Create placeholder result to get the ID
    db_result = ScreeningResult(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        resume_text=parsed_data.get("raw_text", ""),
        jd_text=job_description,
        parsed_data=json.dumps(parsed_data, default=_json_default),
        analysis_result="{}",  # Placeholder — will be updated
        role_template_id=template_id,
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    screening_result_id = db_result.id

    async def event_stream():
        final_result: dict = {}
        python_scores_saved = False

        try:
            # Check for client disconnect before starting pipeline
            if await request.is_disconnected():
                log.warning("Client disconnected before streaming analysis started")
                return

            async for event in astream_hybrid_pipeline(
                resume_text=parsed_data["raw_text"],
                job_description=job_description,
                parsed_data=parsed_data,
                gap_analysis=gap_analysis,
                scoring_weights=weights,
                jd_analysis=jd_analysis,
                screening_result_id=screening_result_id,
                tenant_id=tenant_id,
                phase3_context=phase3_context,
            ):
                # Check for client disconnect between stages
                if await request.is_disconnected():
                    log.warning("Client disconnected during streaming analysis")
                    # Early DB save: ensure Python results are preserved
                    # Only save on "parsing" stage which has the full Python results
                    if not python_scores_saved and event.get("stage") in ("parsing", "complete"):
                        try:
                            stage_result = event.get("result", {})
                            if stage_result:
                                stage_result["result_id"] = screening_result_id
                                stage_result["candidate_id"] = candidate_id
                                # Use a dedicated session to avoid detached object issues
                                # The route's db session may be closed before the streaming generator runs
                                from app.backend.db.database import SessionLocal
                                disc_db = SessionLocal()
                                try:
                                    sr = disc_db.query(ScreeningResult).filter(ScreeningResult.id == screening_result_id).first()
                                    if sr:
                                        sr.analysis_result = json.dumps(stage_result, default=_json_default)
                                        disc_db.commit()
                                        python_scores_saved = True
                                        log.info("Early DB save completed after client disconnect (fit_score=%s)", stage_result.get("fit_score"))
                                    else:
                                        log.error("ScreeningResult id=%s not found for disconnect save", screening_result_id)
                                finally:
                                    disc_db.close()
                        except Exception as db_exc:
                            log.warning("Failed to save early DB results: %s", db_exc)
                    return

                if isinstance(event, str):
                    # SSE heartbeat ping from the generator
                    yield event
                    continue
                yield f"data: {json.dumps(event, default=_json_default)}\n\n"

                # Early DB save after Python parsing phase completes (NOT scoring phase)
                # The "parsing" stage contains the full Python results
                if event.get("stage") == "parsing" and not python_scores_saved:
                    try:
                        parsing_result = event.get("result", {})
                        if parsing_result:
                            # Ensure we have the full Python result with all fields
                            parsing_result["result_id"] = screening_result_id
                            parsing_result["candidate_id"] = candidate_id
                            # Use a dedicated session to avoid detached object issues
                            # The route's db session may be closed before the streaming generator runs
                            from app.backend.db.database import SessionLocal
                            early_db = SessionLocal()
                            try:
                                sr = early_db.query(ScreeningResult).filter(ScreeningResult.id == screening_result_id).first()
                                if sr:
                                    sr.analysis_result = json.dumps(parsing_result, default=_json_default)
                                    early_db.commit()
                                    python_scores_saved = True
                                    log.info("Early DB save completed after parsing phase (fit_score=%s)", parsing_result.get("fit_score"))
                                else:
                                    log.error("ScreeningResult id=%s not found for early save", screening_result_id)
                            finally:
                                early_db.close()
                    except Exception as db_exc:
                        log.warning("Failed to save early DB results after parsing: %s", db_exc)

                if event.get("stage") == "complete":
                    final_result = event.get("result", {})

        except Exception as exc:
            log.exception("Streaming analysis failed: %s", exc)
            error_event = {"stage": "error", "result": {"message": str(exc)}}
            yield f"data: {json.dumps(error_event, default=_json_default)}\n\n"
            final_result = _fallback_result(gap_analysis)

        # Update the ScreeningResult with the final analysis_result
        try:
            final_result["result_id"]    = screening_result_id
            final_result["candidate_id"] = candidate_id
            _cand_row_s = db.get(Candidate, candidate_id)
            final_result["candidate_name"] = (
                (_cand_row_s.name if _cand_row_s and _cand_row_s.name else None)
                or (parsed_data.get("contact_info", {}).get("name") or "").strip()
                or (final_result.get("candidate_profile", {}).get("name") or "").strip()
                or None
            )
            if is_dup and action not in ("update_profile", "create_new"):
                existing = db.get(Candidate, candidate_id)
                if existing:
                    final_result["duplicate_candidate"] = _build_duplicate_info(db, existing).model_dump(mode='json')

            # Use a dedicated session for the final save to avoid detached object issues
            # The route's db session may be closed before the streaming generator runs
            from app.backend.db.database import SessionLocal
            save_db = SessionLocal()
            try:
                sr = save_db.query(ScreeningResult).filter(ScreeningResult.id == screening_result_id).first()
                if sr:
                    sr.analysis_result = json.dumps(final_result, default=_json_default)
                    # Also update candidate profile
                    cand = save_db.query(Candidate).filter(Candidate.id == candidate_id).first()
                    if cand:
                        _store_candidate_profile(cand, parsed_data, gap_analysis, file_hash, final_result.get("analysis_quality", "medium"), content, resume.filename)
                    save_db.commit()
                    log.info("Final DB save completed for screening_result_id=%s (fit_score=%s)", screening_result_id, final_result.get("fit_score"))
                else:
                    log.error("ScreeningResult id=%s not found for final save", screening_result_id)
            finally:
                save_db.close()
        except Exception as db_exc:
            log.error("Final DB save failed for screening_result_id=%s: %s", screening_result_id, db_exc)
            final_result["pipeline_errors"] = final_result.get("pipeline_errors", []) + [
                f"DB save error: {str(db_exc)}"
            ]

        log.info(json.dumps({
            "event":       "analysis_complete",
            "tenant_id":   tenant_id,
            "filename":    resume.filename,
            "fit_score":   final_result.get("fit_score"),
            "llm_pending": final_result.get("narrative_pending", False),
            "quality":     final_result.get("analysis_quality"),
            "total_ms":    int((time.time() - t_start) * 1000),
        }, default=_json_default))

        # Webhook dispatch — never let webhook failure affect analysis
        try:
            from app.backend.services.webhook_service import dispatch_event_background
            dispatch_event_background(None, tenant_id, "analysis.completed", {"result_id": screening_result_id})
        except Exception:
            pass

        # Yield final complete with result_id for polling
        complete_payload = {"stage": "complete", "result": final_result}
        yield f"data: {json.dumps(complete_payload, default=_json_default)}\n\n"

    async def event_stream_with_cleanup():
        """Wrapper to ensure [DONE] event and resource cleanup always happen."""
        try:
            async for chunk in event_stream():
                yield chunk
        except Exception as e:
            log.exception("Stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            # Guaranteed [DONE] event
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream_with_cleanup(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Batch resume analysis (chunked upload) ─────────────────────────────────

@router.post("/analyze/batch-chunked", response_model=BatchAnalysisResponse)
async def batch_analyze_chunked_endpoint(
    upload_ids: list[str] = Form(...),
    filenames: list[str] = Form(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    template_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch analysis for chunked uploads.

    Accepts upload_ids from the chunked upload system instead of raw files.
    Reads assembled files from the chunk storage directory and processes
    them through the same analysis pipeline as /analyze/batch.
    """
    # ─── HARD QUOTA CHECK (before any work) ───────────────────────────────────
    quota = check_quota(current_user.tenant_id, db)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": "Monthly analysis quota exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "plan": quota["plan"],
            },
        )

    from app.backend.routes.upload import CHUNK_STORAGE_DIR

    if not upload_ids:
        raise HTTPException(status_code=400, detail="At least one upload_id required")

    if len(upload_ids) != len(filenames):
        raise HTTPException(
            status_code=400,
            detail=f"upload_ids ({len(upload_ids)}) and filenames ({len(filenames)}) must have the same length",
        )

    if len(upload_ids) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum batch size is {MAX_BATCH_SIZE} resumes",
        )

    # Read and validate JD file if provided (before usage check)
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name = job_file.filename

    # Resolve and validate job description (before usage check)
    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)
    _check_jd_size(job_description)

    # Locate assembled files for each upload_id
    assembled_dir = CHUNK_STORAGE_DIR / "assembled"
    file_data = []
    failed_items: list[BatchFailedItem] = []

    for upload_id, filename in zip(upload_ids, filenames):
        # Sanitise to prevent directory traversal
        safe_uid = upload_id.replace("..", "").replace("/", "").replace("\\", "")
        safe_fname = filename.replace("..", "").replace("/", "").replace("\\", "")
        assembled_path = assembled_dir / f"{safe_uid}_{safe_fname}"

        if not assembled_path.exists():
            log.warning("Assembled file not found for upload_id=%s, filename=%s", upload_id, filename)
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Upload {upload_id} not found or expired. Please re-upload.",
            ))
            continue

        try:
            content = assembled_path.read_bytes()
        except Exception as e:
            log.warning("Failed to read assembled file for upload_id=%s: %s", upload_id, e)
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Failed to read assembled file: {str(e)}",
            ))
            continue

        # Validate size and extension
        if len(content) > 10 * 1024 * 1024:
            failed_items.append(BatchFailedItem(
                filename=filename,
                error="Resume file too large (max 10MB)",
            ))
            continue

        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Only {ALLOWED_EXTENSIONS} files are allowed",
            ))
            continue

        file_data.append((content, filename, upload_id))

    # Pre-flight file content validation (magic bytes)
    validated_file_data = []
    for content, filename, upload_id in file_data:
        try:
            _validate_file_content(content, filename)
            validated_file_data.append((content, filename, upload_id))
        except HTTPException as e:
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"File validation failed: {e.detail}",
            ))
    file_data = validated_file_data

    valid_count = len(file_data)

    if valid_count == 0:
        if not failed_items:
            raise HTTPException(status_code=400, detail="No valid resume files provided")
        # All files failed - return empty results with failures
        return BatchAnalysisResponse(
            results=[],
            failed=failed_items,
            total=len(upload_ids),
            successful=0,
            failed_count=len(failed_items),
        )

    # Get tenant's plan for batch size limit
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    max_batch_size = MAX_BATCH_SIZE
    if tenant and tenant.plan:
        limits = _get_plan_limits(tenant.plan)
        plan_batch_limit = limits.get("batch_size", MAX_BATCH_SIZE)
        max_batch_size = min(max_batch_size, plan_batch_limit)

    if valid_count > max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Your plan allows maximum {max_batch_size} resumes per batch. Please upgrade to process more.",
        )

    # CHECK AND INCREMENT USAGE
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, valid_count)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    # Validate scoring_weights size
    _check_scoring_weights_size(scoring_weights)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)

    # Pre-parse JD once
    _get_or_cache_jd(db, job_description)

    # Process all resumes with semaphore-wrapped calls (fast Python scoring)
    tasks = [
        _process_with_semaphore(content, filename, job_description, weights, db)
        for content, filename, _ in file_data
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # SEPARATE SUCCESSES FROM FAILURES
    batch_results = []

    for raw, (content, filename, upload_id) in zip(raw_results, file_data):
        if isinstance(raw, Exception):
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=str(raw),
            ))
            continue

        try:
            parsed_data = raw.pop("_parsed_data", {})
            gap_analysis = raw.pop("_gap_analysis", {})
            file_hash = hashlib.md5(content).hexdigest()

            candidate_id, _ = _get_or_create_candidate(
                db, parsed_data, current_user.tenant_id,
                file_hash=file_hash,
                gap_analysis=gap_analysis,
                profile_quality=raw.get("analysis_quality", "medium"),
                file_content=content,
                filename=filename,
            )

            db_result = ScreeningResult(
                tenant_id=current_user.tenant_id,
                candidate_id=candidate_id,
                resume_text=parsed_data.get("raw_text", ""),
                jd_text=job_description,
                parsed_data=json.dumps(parsed_data),
                analysis_result=json.dumps(raw),
                role_template_id=template_id,
                narrative_status="pending",
            )
            db.add(db_result)
            db.flush()
            db.commit()
            raw["result_id"] = db_result.id

            # Spawn background LLM narrative generation
            _spawn_background_narrative(raw, db_result.id, current_user.tenant_id)

            batch_results.append({"filename": filename, "result": raw})
        except Exception as e:
            db.rollback()
            log.error("Failed to save analysis for %s: %s", filename, e)
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Database error: {str(e)}",
            ))

    # Clean up assembled files after successful processing
    for _content, filename, upload_id in file_data:
        try:
            safe_uid = upload_id.replace("..", "").replace("/", "").replace("\\", "")
            safe_fname = filename.replace("..", "").replace("/", "").replace("\\", "")
            assembled_path = assembled_dir / f"{safe_uid}_{safe_fname}"
            if assembled_path.exists():
                assembled_path.unlink()
                log.info("Cleaned up assembled file: %s", assembled_path)
        except Exception as e:
            log.warning("Non-critical: Failed to clean up assembled file for upload_id=%s: %s", upload_id, e)

    # Sort by fit score
    batch_results.sort(key=lambda x: x["result"].get("fit_score") or 0, reverse=True)
    ranked = [
        BatchAnalysisResult(rank=i + 1, filename=r["filename"], result=r["result"])
        for i, r in enumerate(batch_results)
    ]

    return BatchAnalysisResponse(
        results=ranked,
        failed=failed_items,
        total=len(upload_ids),
        successful=len(ranked),
        failed_count=len(failed_items),
    )


# ─── Batch resume analysis (SSE streaming) ───────────────────────────────────

@router.post("/analyze/batch-stream")
async def batch_analyze_stream_endpoint(
    upload_ids: list[str] = Form(...),
    filenames: list[str] = Form(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    template_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE streaming batch analysis for chunked uploads.

    Processes resumes concurrently and streams each result as an SSE event
    as soon as it completes, instead of waiting for all resumes to finish.

    Emits:
      data: {"event": "failed",  "index": N, ...}   — per pre-flight or runtime failure
      data: {"event": "result", "index": N, ...}   — per successful resume
      data: {"event": "done",   "total": N, ...}   — final summary
      data: [DONE]
    """
    # ─── HARD QUOTA CHECK (before any work) ───────────────────────────────────
    quota = check_quota(current_user.tenant_id, db)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": "Monthly analysis quota exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "plan": quota["plan"],
            },
        )

    from app.backend.routes.upload import CHUNK_STORAGE_DIR

    # ── Input validation ────────────────────────────────────────────────────
    if not upload_ids:
        raise HTTPException(status_code=400, detail="At least one upload_id required")

    if len(upload_ids) != len(filenames):
        raise HTTPException(
            status_code=400,
            detail=f"upload_ids ({len(upload_ids)}) and filenames ({len(filenames)}) must have the same length",
        )

    if len(upload_ids) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum batch size is {MAX_BATCH_SIZE} resumes",
        )

    # Read and validate JD file if provided (before usage check)
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name = job_file.filename

    # Resolve and validate job description (before usage check)
    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)
    _check_jd_size(job_description)

    # Locate assembled files for each upload_id
    assembled_dir = CHUNK_STORAGE_DIR / "assembled"
    file_data = []
    failed_items: list[BatchFailedItem] = []

    for upload_id, filename in zip(upload_ids, filenames):
        # Sanitise to prevent directory traversal
        safe_uid = upload_id.replace("..", "").replace("/", "").replace("\\", "")
        safe_fname = filename.replace("..", "").replace("/", "").replace("\\", "")
        assembled_path = assembled_dir / f"{safe_uid}_{safe_fname}"

        if not assembled_path.exists():
            log.warning("Assembled file not found for upload_id=%s, filename=%s", upload_id, filename)
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Upload {upload_id} not found or expired. Please re-upload.",
            ))
            continue

        try:
            content = assembled_path.read_bytes()
        except Exception as e:
            log.warning("Failed to read assembled file for upload_id=%s: %s", upload_id, e)
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Failed to read assembled file: {str(e)}",
            ))
            continue

        # Validate size and extension
        if len(content) > 10 * 1024 * 1024:
            failed_items.append(BatchFailedItem(
                filename=filename,
                error="Resume file too large (max 10MB)",
            ))
            continue

        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"Only {ALLOWED_EXTENSIONS} files are allowed",
            ))
            continue

        file_data.append((content, filename, upload_id))

    # Pre-flight file content validation (magic bytes)
    validated_file_data = []
    for content, filename, upload_id in file_data:
        try:
            _validate_file_content(content, filename)
            validated_file_data.append((content, filename, upload_id))
        except HTTPException as e:
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=f"File validation failed: {e.detail}",
            ))
    file_data = validated_file_data

    valid_count = len(file_data)

    if valid_count == 0:
        if not failed_items:
            raise HTTPException(status_code=400, detail="No valid resume files provided")
        # All files failed — stream failures then done
        async def _empty_stream():
            total = len(failed_items)
            for i, fail in enumerate(failed_items):
                evt = BatchStreamEvent(
                    event="failed", index=i + 1, total=total,
                    filename=fail.filename, error=fail.error,
                )
                yield f"data: {json.dumps(evt.model_dump(exclude_none=True), default=_json_default)}\n\n"
            done_evt = BatchStreamEvent(
                event="done", index=0, total=total,
                successful=0, failed_count=total,
            )
            yield f"data: {json.dumps(done_evt.model_dump(exclude_none=True), default=_json_default)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(
            _empty_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
        )

    # Get tenant's plan for batch size limit
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    max_batch_size = MAX_BATCH_SIZE
    if tenant and tenant.plan:
        limits = _get_plan_limits(tenant.plan)
        plan_batch_limit = limits.get("batch_size", MAX_BATCH_SIZE)
        max_batch_size = min(max_batch_size, plan_batch_limit)

    if valid_count > max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Your plan allows maximum {max_batch_size} resumes per batch. Please upgrade to process more.",
        )

    # CHECK AND INCREMENT USAGE
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, valid_count)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    # Validate scoring_weights size
    _check_scoring_weights_size(scoring_weights)

    parsed_weights = None
    if scoring_weights:
        try:
            parsed_weights = json.loads(scoring_weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)

    # Pre-parse JD once
    _get_or_cache_jd(db, job_description)

    # Extract tenant_id while session is still active
    tenant_id = current_user.tenant_id
    _template_id = template_id  # Capture for use inside generator

    # ── Tagged wrapper for asyncio.as_completed mapping ──────────────────────
    async def _process_and_tag(
        index: int, content: bytes, filename: str, upload_id: str,
        jd: str, weights: dict | None, db_session: Session,
    ) -> tuple[dict, bytes, str, str]:
        """Wrapper that returns result alongside file metadata."""
        await asyncio.sleep(0.3 * index)  # Stagger to avoid thundering herd
        result = await _process_with_semaphore(
            content, filename, jd, weights, db_session,
        )
        return result, content, filename, upload_id

    total = len(file_data) + len(failed_items)

    # ── SSE generator ────────────────────────────────────────────────────────
    async def event_generator():
        completed = 0
        successful_count = 0
        failed_count = len(failed_items)

        # Emit pre-flight failures first
        for i, fail in enumerate(failed_items):
            evt = BatchStreamEvent(
                event="failed",
                index=i + 1,
                total=total,
                filename=fail.filename,
                error=fail.error,
            )
            yield f"data: {json.dumps(evt.model_dump(exclude_none=True), default=_json_default)}\n\n"

        # Emit processing events so the UI knows which files have started
        for idx, (_, filename, _) in enumerate(file_data):
            processing_evt = BatchStreamEvent(
                event="processing",
                index=idx + 1,
                total=total,
                filename=filename,
            )
            yield f"data: {json.dumps(processing_evt.model_dump(exclude_none=True), default=_json_default)}\n\n"

        # Create tagged tasks
        tasks = [
            _process_and_tag(idx, c, f, uid, job_description, parsed_weights, db)
            for idx, (c, f, uid) in enumerate(file_data)
        ]

        # Process resumes as they complete
        for coro in asyncio.as_completed(tasks):
            try:
                raw, content, filename, upload_id = await coro
            except Exception as e:
                failed_count += 1
                completed += 1
                evt = BatchStreamEvent(
                    event="failed",
                    index=completed + failed_count,
                    total=total,
                    error=str(e),
                )
                yield f"data: {json.dumps(evt.model_dump(exclude_none=True), default=_json_default)}\n\n"
                continue

            # Per-resume DB save using a fresh session to avoid detached object issues
            save_db = SessionLocal()
            try:
                parsed_data = raw.pop("_parsed_data", {})
                gap_analysis = raw.pop("_gap_analysis", {})
                file_hash = hashlib.md5(content).hexdigest()

                candidate_id, _ = _get_or_create_candidate(
                    save_db, parsed_data, tenant_id,
                    file_hash=file_hash,
                    gap_analysis=gap_analysis,
                    profile_quality=raw.get("analysis_quality", "medium"),
                    file_content=content,
                    filename=filename,
                )

                cand = save_db.get(Candidate, candidate_id)
                if cand:
                    _store_candidate_profile(
                        cand, parsed_data, gap_analysis, file_hash,
                        raw.get("analysis_quality", "medium"),
                        file_content=content,
                        filename=filename,
                    )

                db_result = ScreeningResult(
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    resume_text=parsed_data.get("raw_text", ""),
                    jd_text=job_description,
                    parsed_data=json.dumps(parsed_data, default=_json_default),
                    analysis_result=json.dumps(raw, default=_json_default),
                    role_template_id=_template_id,
                    narrative_status="pending",
                )
                save_db.add(db_result)
                save_db.commit()
                save_db.refresh(db_result)

                screening_result_id = db_result.id

                # Spawn background LLM narrative generation
                _spawn_background_narrative(raw, screening_result_id, tenant_id)
            except Exception as e:
                save_db.rollback()
                log.error("Failed to save analysis for %s: %s", filename, e)
                failed_count += 1
                completed += 1
                evt = BatchStreamEvent(
                    event="failed",
                    index=completed + failed_count,
                    total=total,
                    filename=filename,
                    error=f"Database error: {str(e)}",
                )
                yield f"data: {json.dumps(evt.model_dump(exclude_none=True), default=_json_default)}\n\n"
                continue
            finally:
                save_db.close()

            completed += 1
            successful_count += 1

            # Emit result event
            evt = BatchStreamEvent(
                event="result",
                index=completed,
                total=total,
                filename=filename,
                result=raw,
                screening_result_id=screening_result_id,
            )
            yield f"data: {json.dumps(evt.model_dump(exclude_none=True), default=_json_default)}\n\n"

        # Emit done event
        done_evt = BatchStreamEvent(
            event="done",
            index=0,
            total=total,
            successful=successful_count,
            failed_count=failed_count,
        )
        yield f"data: {json.dumps(done_evt.model_dump(exclude_none=True), default=_json_default)}\n\n"
        yield "data: [DONE]\n\n"

        # Clean up assembled files after all processing
        for _content, filename, upload_id in file_data:
            try:
                safe_uid = upload_id.replace("..", "").replace("/", "").replace("\\", "")
                safe_fname = filename.replace("..", "").replace("/", "").replace("\\", "")
                assembled_path = assembled_dir / f"{safe_uid}_{safe_fname}"
                if assembled_path.exists():
                    assembled_path.unlink()
                    log.info("Cleaned up assembled file: %s", assembled_path)
            except Exception as e:
                log.warning("Non-critical: Failed to clean up assembled file for upload_id=%s: %s", upload_id, e)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


# ─── Batch resume analysis ────────────────────────────────────────────────────

async def _process_with_semaphore(
    content: bytes,
    filename: str,
    job_description: str,
    scoring_weights: dict | None,
    db: Session | None = None,
) -> dict:
    """Wrap resume processing with semaphore for concurrency control."""
    async with _BATCH_SEMAPHORE:
        return await _process_single_resume(
            content, filename, job_description, scoring_weights, db,
        )


def _spawn_background_narrative(
    result: dict,
    screening_result_id: int,
    tenant_id: int,
) -> None:
    """Build llm_context from Python result and spawn background LLM narrative task."""
    llm_context = {
        "jd_analysis":       result.get("jd_analysis", {}),
        "candidate_profile": result.get("candidate_profile", {}),
        "skill_analysis":    result.get("skill_analysis", {}),
        "scores": {
            **result.get("_scores", {}),
            "fit_score":            result.get("fit_score"),
            "final_recommendation": result.get("final_recommendation"),
        },
        "score_rationales":  result.get("score_rationales", {}),
        "risk_summary":      result.get("risk_summary", {}),
        "skill_depth":       result.get("skill_depth", {}),
    }
    # Strip internal keys for background task
    python_result = {k: v for k, v in result.items() if not k.startswith("_")}

    task = asyncio.create_task(
        _background_llm_narrative(
            screening_result_id=screening_result_id,
            tenant_id=tenant_id,
            llm_context=llm_context,
            python_result=python_result,
        )
    )
    register_background_task(task)


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def batch_analyze_endpoint(
    resumes: list[UploadFile] = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    template_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ─── HARD QUOTA CHECK (before any work) ───────────────────────────────────
    quota = check_quota(current_user.tenant_id, db)
    if not quota["allowed"]:
        raise HTTPException(
            status_code=403,
            detail={
                "detail": "Monthly analysis quota exceeded",
                "used": quota["used"],
                "limit": quota["limit"],
                "plan": quota["plan"],
            },
        )

    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume required")
    
    # ─── VALIDATE BATCH SIZE FIRST (before reading any files) ─────────────────
    if len(resumes) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"Maximum batch size is {MAX_BATCH_SIZE} resumes"
        )
    
    # Read and validate JD file if provided (before usage check)
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name  = job_file.filename

    # Resolve and validate job description (before usage check)
    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)
    _check_jd_size(job_description)
    
    # ─── VALIDATE FILES (before incrementing usage) ─────────────────────────────
    # Read and validate all files
    file_data = []
    for f in resumes:
        if not f.filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue
        content = await f.read()
        if len(content) <= 10 * 1024 * 1024:
            file_data.append((content, f.filename))
    
    valid_count = len(file_data)
    
    # Get tenant's plan for batch size limit
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    max_batch_size = MAX_BATCH_SIZE  # Use module constant
    if tenant and tenant.plan:
        limits = _get_plan_limits(tenant.plan)
        plan_batch_limit = limits.get("batch_size", MAX_BATCH_SIZE)
        max_batch_size = min(max_batch_size, plan_batch_limit)
    
    if valid_count > max_batch_size:
        raise HTTPException(
            status_code=400, 
            detail=f"Your plan allows maximum {max_batch_size} resumes per batch. Please upgrade to process more."
        )
    
    # ─── CHECK AND INCREMENT USAGE (after validation, before processing) ────────
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, valid_count)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    # Validate scoring_weights size before parsing
    _check_scoring_weights_size(scoring_weights)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)

    # Pre-parse JD once for all resumes in this batch
    _get_or_cache_jd(db, job_description)

    if not file_data:
        raise HTTPException(status_code=400, detail="No valid resume files provided")

    # Process all resumes with semaphore-wrapped calls for concurrency control (fast path)
    tasks = [
        _process_with_semaphore(content, filename, job_description, weights, db)
        for content, filename in file_data
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # ─── SEPARATE SUCCESSES FROM FAILURES ───────────────────────────────────────
    batch_results = []
    failed_items = []
    
    for raw, (content, filename) in zip(raw_results, file_data):
        if isinstance(raw, Exception):
            # Track failure
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=str(raw)
            ))
            continue
        
        # Extract internal data
        parsed_data  = raw.pop("_parsed_data", {})
        gap_analysis = raw.pop("_gap_analysis", {})
        pdf_bytes    = raw.pop("_pdf_bytes", None)
        file_hash    = hashlib.md5(content).hexdigest()

        candidate_id, _ = _get_or_create_candidate(
            db, parsed_data, current_user.tenant_id,
            file_hash=file_hash,
            gap_analysis=gap_analysis,
            profile_quality=raw.get("analysis_quality", "medium"),
            file_content=content,
            filename=filename,
            converted_pdf_content=pdf_bytes,
        )

        db_result = ScreeningResult(
            tenant_id=current_user.tenant_id,
            candidate_id=candidate_id,
            resume_text=parsed_data.get("raw_text", ""),
            jd_text=job_description,
            parsed_data=json.dumps(parsed_data),
            analysis_result=json.dumps(raw),
            role_template_id=template_id,
            narrative_status="pending",
        )
        db.add(db_result)
        db.flush()
        raw["result_id"] = db_result.id

        # Spawn background LLM narrative generation
        _spawn_background_narrative(raw, db_result.id, current_user.tenant_id)

        batch_results.append({"filename": filename, "result": raw})

    db.commit()

    # Sort by fit score
    batch_results.sort(key=lambda x: x["result"].get("fit_score") or 0, reverse=True)
    ranked = [
        BatchAnalysisResult(rank=i + 1, filename=r["filename"], result=r["result"])
        for i, r in enumerate(batch_results)
    ]
    
    return BatchAnalysisResponse(
        results=ranked,
        failed=failed_items,
        total=len(file_data),
        successful=len(ranked),
        failed_count=len(failed_items),
    )


# ─── History ──────────────────────────────────────────────────────────────────

@router.get("/history")
def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    results = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.tenant_id == current_user.tenant_id)
        .order_by(ScreeningResult.timestamp.desc())
        .limit(100)
        .all()
    )
    def _safe_loads(data):
        try:
            return json.loads(data or "{}")
        except (json.JSONDecodeError, TypeError):
            return {}

    output = []
    for r in results:
        analysis = _safe_loads(r.analysis_result)
        parsed = _safe_loads(r.parsed_data)

        # Resolve candidate name: Candidate.name (possibly edited) takes priority
        cand = db.get(Candidate, r.candidate_id) if r.candidate_id else None
        candidate_name = (
            (cand.name or "").strip() if cand and cand.name else None
        ) or (
            (analysis.get("candidate_name") or "").strip() or
            (analysis.get("contact_info", {}).get("name") or "").strip() or
            (analysis.get("candidate_profile", {}).get("name") or "").strip() or
            (parsed.get("contact_info", {}).get("name") or "").strip() or
            None
        )

        job_role = (
            analysis.get("job_role") or
            analysis.get("jd_analysis", {}).get("role_title") or
            None
        )

        output.append({
            "id": r.id,
            "timestamp": r.timestamp,
            "status": r.status,
            "candidate_id": r.candidate_id,
            "fit_score": analysis.get("fit_score"),
            "final_recommendation": analysis.get("final_recommendation"),
            "risk_level": analysis.get("risk_level"),
            "candidate_name": candidate_name,
            "job_role": job_role,
        })

    return output


# ─── Result status update ─────────────────────────────────────────────────────

@router.put("/results/{result_id}/status")
def update_status(
    result_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == result_id,
        ScreeningResult.tenant_id == current_user.tenant_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    allowed_statuses = {"pending", "shortlisted", "rejected", "in-review", "hired"}
    new_status = body.get("status", "")
    if new_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {allowed_statuses}")

    result.status = new_status
    result.status_updated_at = datetime.utcnow()
    db.commit()
    return {"id": result_id, "status": new_status}


# ─── Re-score endpoint (post-analysis skill edit) ────────────────────────────

@router.post("/analyze/{result_id}/rescore")
def rescore_endpoint(
    result_id: int,
    body: RescoreRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-score an existing analysis with overridden skill classification.

    Does NOT re-run the full pipeline or call the LLM — this is a quick
    recalculation using stored data.  Only skill-related scores change
    (skill_match + fit_score).  Changes are persisted to the database.
    """
    # ── 1. Load screening result & verify tenant ownership ───────────────────
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == result_id,
        ScreeningResult.tenant_id == current_user.tenant_id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    # ── 2. Parse stored JSON blobs ────────────────────────────────────────────
    try:
        analysis = json.loads(result.analysis_result)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="Stored analysis_result is corrupt")

    try:
        parsed_data = json.loads(result.parsed_data)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="Stored parsed_data is corrupt")

    # ── 3. Extract candidate skills from parsed_data ──────────────────────────
    # The pipeline stores skills in multiple places; gather them all.
    candidate_skills_raw: list[str] = list(parsed_data.get("skills", []))
    # Also check the candidate_profile / skills_identified path
    cp = analysis.get("candidate_profile", {})
    candidate_skills_raw.extend(cp.get("skills_identified", []))
    # Deduplicate (case-insensitive)
    seen_lower: set[str] = set()
    candidate_skills: list[str] = []
    for s in candidate_skills_raw:
        if isinstance(s, str) and s.lower() not in seen_lower:
            seen_lower.add(s.lower())
            candidate_skills.append(s)

    # ── 4. Apply new skill classification ─────────────────────────────────────
    jd_analysis = analysis.get("jd_analysis", {})
    # Save originals
    jd_analysis.setdefault("original_required_skills", jd_analysis.get("required_skills", []))
    jd_analysis.setdefault("original_nice_to_have_skills", jd_analysis.get("nice_to_have_skills", []))

    # Extract proficiency data and normalise skills to plain strings
    proficiency_map: dict[str, str] = {}
    def _normalise_skill_list(skill_list):
        result = []
        for item in skill_list:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict) and "skill" in item:
                result.append(item["skill"])
                prof = item.get("proficiency")
                if isinstance(prof, str) and prof.lower() in (
                    "basic", "intermediate", "advanced", "expert",
                ):
                    proficiency_map[item["skill"].lower()] = prof.lower()
            else:
                result.append(str(item))
        return result

    required_skills = _normalise_skill_list(body.required_skills)
    nice_to_have_skills = _normalise_skill_list(body.nice_to_have_skills)

    jd_analysis["required_skills"] = required_skills
    jd_analysis["nice_to_have_skills"] = nice_to_have_skills
    jd_analysis["skill_overrides_applied"] = True
    if proficiency_map:
        jd_analysis["skill_proficiency_requirements"] = proficiency_map
    else:
        jd_analysis.pop("skill_proficiency_requirements", None)

    # ── 5. Re-run skill matching (case-insensitive) ──────────────────────────
    req_lower = {s.lower() for s in required_skills if isinstance(s, str)}
    nice_lower = {s.lower() for s in nice_to_have_skills if isinstance(s, str)}
    cand_lower = {s.lower() for s in candidate_skills}

    matched_required = [s for s in required_skills if s.lower() in cand_lower]
    missing_required = [s for s in required_skills if s.lower() not in cand_lower]
    matched_nice_to_have = [s for s in nice_to_have_skills if s.lower() in cand_lower]
    missing_nice_to_have = [s for s in nice_to_have_skills if s.lower() not in cand_lower]

    # Backward-compat unions
    matched_skills = matched_required + matched_nice_to_have
    missing_skills = missing_required + missing_nice_to_have

    required_match_pct = (len(matched_required) / max(len(required_skills), 1)) * 100
    nice_to_have_match_pct = (len(matched_nice_to_have) / max(len(nice_to_have_skills), 1)) * 100

    # ── 5b. Proficiency-aware scoring (if proficiency data provided) ────────
    proficiency_analysis = {}
    prof_factor = None
    if proficiency_map and matched_required:
        from app.backend.services.hybrid_pipeline import (
            _compute_proficiency_score,
            _estimate_candidate_proficiency,
        )
        # Build candidate skills data for proficiency estimation
        candidate_skills_data = {
            "skills_identified": candidate_skills,
            "total_effective_years": analysis.get("candidate_profile", {}).get("total_effective_years", 0),
            "work_experience": parsed_data.get("work_experience", []),
        }
        prof_factor = _compute_proficiency_score(
            matched_required, candidate_skills_data, proficiency_map,
        )
        # Build proficiency_analysis details
        for skill in matched_required:
            req_level = proficiency_map.get(skill.lower())
            if req_level:
                cand_level = _estimate_candidate_proficiency(skill, candidate_skills_data)
                from app.backend.services.hybrid_pipeline import PROFICIENCY_LEVELS
                req_rank = PROFICIENCY_LEVELS.get(req_level, 2)
                cand_rank = PROFICIENCY_LEVELS.get(cand_level, 2)
                if cand_rank >= req_rank:
                    match_factor = 1.0
                elif cand_rank == req_rank - 1:
                    match_factor = 0.6
                else:
                    match_factor = 0.3
                proficiency_analysis[skill] = {
                    "required": req_level,
                    "estimated_candidate": cand_level,
                    "match_factor": match_factor,
                }

    # ── 6. Recalculate skill_score (70/30 weighting) ──────────────────────────
    if nice_to_have_skills:
        req_ratio = required_match_pct
        if prof_factor is not None:
            req_ratio = required_match_pct * prof_factor
        skill_score = round((req_ratio * 0.70) + (nice_to_have_match_pct * 0.30))
    else:
        req_ratio = required_match_pct
        if prof_factor is not None:
            req_ratio = required_match_pct * prof_factor
        skill_score = round(req_ratio)

    # ── 7. Recalculate fit_score using compute_fit_score() ────────────────────
    sb = analysis.get("score_breakdown", {})
    all_scores = {
        "skill_score":     skill_score,
        "exp_score":       sb.get("experience_match", 50),
        "arch_score":      sb.get("architecture", 50),
        "edu_score":       sb.get("education", 60),
        "timeline_score":  sb.get("stability", sb.get("timeline", 85)),
        "domain_score":    sb.get("domain_fit", 60),
        "actual_years":    analysis.get("candidate_profile", {}).get("total_effective_years", 0),
        "required_years":  analysis.get("candidate_profile", {}).get("required_years", 0),
        "matched_skills":  matched_skills,
        "missing_skills":  missing_skills,
        "required_count":  len(required_skills),
        "employment_gaps": analysis.get("edu_timeline_analysis", {}).get("employment_gaps", []),
        "short_stints":    analysis.get("edu_timeline_analysis", {}).get("short_stints", []),
    }

    # Load tenant scoring weights (same pattern as analyze_endpoint)
    scoring_weights = None
    try:
        tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
        if tenant and tenant.scoring_weights:
            scoring_weights = json.loads(tenant.scoring_weights)
    except Exception:
        pass

    # Convert weights to internal schema (mirrors _run_python_phase)
    new_weights = convert_to_new_schema(scoring_weights)
    internal_weights = {
        "skills":       new_weights.get("core_competencies", 0.30),
        "experience":   new_weights.get("experience", 0.20),
        "architecture": new_weights.get("role_excellence", 0.15),
        "education":    new_weights.get("education", 0.10),
        "timeline":     new_weights.get("career_trajectory", 0.10),
        "domain":       new_weights.get("domain_fit", 0.10),
        "risk":         new_weights.get("risk", 0.15),
    }

    jd_for_fit = {
        "required_skills": required_skills,
        "nice_to_have_skills": nice_to_have_skills,
    }

    fit_r = compute_fit_score(all_scores, internal_weights, jd_analysis=jd_for_fit)

    # Preserve deterministic score if it exists — rescore only changes skill components
    # The deterministic engine applies caps based on core_skill_match and domain_match;
    # since we are not re-running domain detection, keep the deterministic score logic
    # but adjust it if the new skill match is worse.
    deterministic_score = analysis.get("deterministic_score", fit_r["fit_score"])
    det_features = analysis.get("deterministic_features", {})
    if det_features:
        # Recompute core_skill_match based on new required match
        new_core_ratio = len(matched_required) / max(len(required_skills), 1)
        det_features = dict(det_features)
        det_features["core_skill_match"] = new_core_ratio
        # Re-derive secondary_skill_match from nice-to-have
        new_secondary_ratio = len(matched_nice_to_have) / max(len(nice_to_have_skills), 1) if nice_to_have_skills else 0
        det_features["secondary_skill_match"] = new_secondary_ratio

        # Re-run deterministic score with updated features
        try:
            from app.backend.services.eligibility_service import check_eligibility
            from app.backend.services.fit_scorer import compute_deterministic_score

            # Use stored domain data — we are NOT re-running domain detection
            jd_domain = analysis.get("jd_domain", {})
            candidate_domain = analysis.get("candidate_domain", {})
            eligibility = check_eligibility(
                jd_domain=jd_domain,
                candidate_domain=candidate_domain,
                core_skill_match=det_features["core_skill_match"],
                relevant_experience=det_features.get("relevant_experience", 0),
            )
            deterministic_score = compute_deterministic_score(det_features, eligibility, new_weights)
        except Exception as e:
            log.warning("Deterministic re-score failed, using fit_score: %s", e)
            deterministic_score = fit_r["fit_score"]

    # Use deterministic score when available, otherwise use compute_fit_score result
    final_fit_score = deterministic_score if det_features else fit_r["fit_score"]
    final_recommendation = fit_r["final_recommendation"]
    # Override recommendation based on deterministic score thresholds
    if det_features:
        if final_fit_score >= RECOMMENDATION_THRESHOLDS["shortlist"]:
            final_recommendation = "Shortlist"
        elif final_fit_score >= RECOMMENDATION_THRESHOLDS["consider"]:
            final_recommendation = "Consider"
        else:
            final_recommendation = "Reject"

    # ── 8. Update analysis_result JSON ────────────────────────────────────────
    # Skill analysis
    skill_analysis = analysis.get("skill_analysis", {})
    skill_analysis.update({
        "matched_skills":        matched_skills,
        "missing_skills":        missing_skills,
        "matched_required":      matched_required,
        "missing_required":      missing_required,
        "matched_nice_to_have":  matched_nice_to_have,
        "missing_nice_to_have":  missing_nice_to_have,
        "required_match_pct":    required_match_pct,
        "nice_to_have_match_pct": nice_to_have_match_pct,
        "skill_score":           skill_score,
        "required_count":        len(required_skills),
    })
    if proficiency_analysis:
        skill_analysis["proficiency_analysis"] = proficiency_analysis

    # Top-level fields
    analysis.update({
        "skill_analysis":        skill_analysis,
        "jd_analysis":          jd_analysis,
        "fit_score":            final_fit_score,
        "final_recommendation": final_recommendation,
        "risk_level":           fit_r["risk_level"],
        "risk_signals":         fit_r["risk_signals"],
        "score_breakdown":      fit_r["score_breakdown"],
        "matched_skills":       matched_skills,
        "missing_skills":       missing_skills,
        "required_skills_count": len(required_skills),
        "deterministic_score":  final_fit_score,
        "deterministic_features": det_features if det_features else analysis.get("deterministic_features"),
    })

    # ── 9. Persist to database ────────────────────────────────────────────────
    result.analysis_result = json.dumps(analysis, default=_json_default)
    db.commit()

    log.info(json.dumps({
        "event":             "rescore_complete",
        "result_id":         result_id,
        "tenant_id":         current_user.tenant_id,
        "new_fit_score":     final_fit_score,
        "new_skill_score":   skill_score,
        "required_matched":  len(matched_required),
        "required_total":    len(required_skills),
        "nice_matched":      len(matched_nice_to_have),
        "nice_total":        len(nice_to_have_skills),
    }))

    return analysis


# ─── Narrative polling endpoint ───────────────────────────────────────────────

@router.get("/analysis/{analysis_id}/narrative")
def get_narrative(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Poll for LLM narrative after Python results are returned.
    
    Returns:
      - {"status": "ready", "narrative": {...}} if narrative is available
      - {"status": "pending"} if LLM is still processing
      - {"status": "failed", "error": "...", "narrative": {...}} if LLM failed (includes fallback)
      - 404 if analysis not found or not owned by user's tenant
    """
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == analysis_id,
        ScreeningResult.tenant_id == current_user.tenant_id,
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Use narrative_status column if available, fall back to checking narrative_json
    status = getattr(result, 'narrative_status', None)
    
    if status == 'failed':
        # Failed — return fallback narrative + error message
        narrative = None
        if result.narrative_json:
            try:
                narrative = json.loads(result.narrative_json)
            except json.JSONDecodeError:
                pass
        return {
            "status": "failed",
            "error": result.narrative_error or "AI analysis encountered an error",
            "narrative": narrative,
        }
    
    if status == 'ready' or (status is None and result.narrative_json):
        # Ready — return narrative
        if result.narrative_json:
            try:
                narrative = json.loads(result.narrative_json)
                return {"status": "ready", "narrative": narrative}
            except json.JSONDecodeError:
                return {"status": "pending"}
    
    # Still pending or processing
    return {"status": "pending"}
