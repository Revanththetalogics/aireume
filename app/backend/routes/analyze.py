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
import asyncio
import logging
import time
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User, Candidate, JdCache, Tenant, SubscriptionPlan
from app.backend.models.schemas import (
    AnalysisResponse, BatchAnalysisResponse, BatchAnalysisResult,
    BatchFailedItem,
    DuplicateCandidateInfo,
)
from app.backend.services.parser_service import parse_resume, extract_jd_text
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.hybrid_pipeline import (
    run_hybrid_pipeline,
    astream_hybrid_pipeline,
    parse_jd_rules,
    shutdown_background_tasks,
)
from app.backend.routes.subscription import _ensure_monthly_reset, _get_plan_limits, record_usage

router = APIRouter(prefix="/api", tags=["analysis"])
log    = logging.getLogger("aria.analysis")

ALLOWED_EXTENSIONS = ('.pdf', '.docx', '.doc')

# Maximum JD size (50KB)
MAX_JD_SIZE = 50 * 1024  # 50KB

# Maximum scoring_weights size (4KB)
MAX_SCORING_WEIGHTS_SIZE = 4 * 1024  # 4KB

# ─── Batch processing concurrency control ───────────────────────────────────────

_BATCH_SEMAPHORE = asyncio.Semaphore(5)
MAX_BATCH_SIZE = 50


# ─── JSON serialization helper ────────────────────────────────────────────────

def _json_default(obj):
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ─── JD cache helpers ─────────────────────────────────────────────────────────

def _get_or_cache_jd(db: Session, job_description: str, suggest_weights: bool = False) -> dict:
    """
    Parse the JD or return the cached result. Shared across all workers via DB.
    
    Args:
        db: Database session
        job_description: Job description text
        suggest_weights: If True, include LLM weight suggestions in result
        
    Returns:
        JD analysis dict, optionally with 'weight_suggestion' key
    """
    jd_hash = hashlib.md5(job_description[:2000].encode()).hexdigest()
    cached = db.query(JdCache).filter(JdCache.hash == jd_hash).first()
    if cached:
        try:
            jd_analysis = json.loads(cached.result_json)
            
            # If weights requested but not in cache, generate them now
            if suggest_weights and "weight_suggestion" not in jd_analysis:
                from app.backend.services.weight_suggester import suggest_weights_for_jd
                weight_suggestion = suggest_weights_for_jd(job_description, timeout=30)
                if weight_suggestion:
                    jd_analysis["weight_suggestion"] = weight_suggestion
                    # Update cache with weight suggestion
                    try:
                        cached.result_json = json.dumps(jd_analysis, default=_json_default)
                        db.commit()
                    except Exception as e:
                        log.warning("Non-critical: Failed to update JD cache with weights: %s", e)
                        db.rollback()
            
            return jd_analysis
        except Exception as e:
            log.warning("Non-critical: Failed to parse cached JD JSON, re-parsing: %s", e)
    
    # Parse JD
    jd_analysis = parse_jd_rules(job_description)
    
    # Add weight suggestion if requested
    if suggest_weights:
        from app.backend.services.weight_suggester import suggest_weights_for_jd
        weight_suggestion = suggest_weights_for_jd(job_description, timeout=30)
        if weight_suggestion:
            jd_analysis["weight_suggestion"] = weight_suggestion
            log.info(f"Weight suggestion: {weight_suggestion['role_category']} role, "
                    f"confidence: {weight_suggestion.get('confidence', 0)}")
    
    # Cache result
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
) -> None:
    """Write parsed profile data into the Candidate row."""
    work_exp = parsed_data.get("work_experience", [])
    candidate.resume_file_hash   = file_hash
    candidate.raw_resume_text    = parsed_data.get("raw_text", "")[:100000]  # cap at 100k chars
    candidate.parser_snapshot_json = _parser_snapshot_json(parsed_data)
    candidate.parsed_skills      = json.dumps(parsed_data.get("skills", []), default=_json_default)
    candidate.parsed_education   = json.dumps(parsed_data.get("education", []), default=_json_default)
    candidate.parsed_work_exp    = json.dumps(work_exp, default=_json_default)
    candidate.gap_analysis_json  = json.dumps(gap_analysis, default=_json_default)
    candidate.current_role       = work_exp[0].get("title", "")    if work_exp else None
    candidate.current_company    = work_exp[0].get("company", "")  if work_exp else None
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
            _store_candidate_profile(existing, parsed_data, gap_analysis, file_hash or "", profile_quality)
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
        _store_candidate_profile(candidate, parsed_data, gap_analysis, file_hash or "", profile_quality)

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


def _check_scoring_weights_size(scoring_weights: str | None) -> None:
    """Reject scoring_weights that exceeds maximum size limit."""
    if scoring_weights and len(scoring_weights.encode('utf-8')) > MAX_SCORING_WEIGHTS_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Scoring weights exceed maximum size of 4KB"
        )


async def _process_single_resume(
    content: bytes,
    filename: str,
    job_description: str,
    scoring_weights: dict | None,
    db: Session | None = None,
) -> dict:
    """Core analysis logic — parse in thread, run hybrid pipeline, return result."""
    # Parse resume in thread pool (blocks event loop otherwise for large PDFs)
    try:
        parsed_data = await asyncio.to_thread(parse_resume, content, filename)
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
        result = await run_hybrid_pipeline(
            resume_text=parsed_data["raw_text"],
            job_description=job_description,
            parsed_data=parsed_data,
            gap_analysis=gap_analysis,
            scoring_weights=scoring_weights,
            jd_analysis=jd_analysis,
        )
    except Exception as e:
        log.warning("Pipeline error for %s: %s", filename, e)
        result = _fallback_result(gap_analysis)
        result["pipeline_errors"] = [f"Pipeline error: {str(e)}"]

    result["_parsed_data"]  = parsed_data
    result["_gap_analysis"] = gap_analysis
    return result


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
    action: str = Form(None),   # use_existing | update_profile | create_new | None
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Non-streaming analysis endpoint.
    
    Returns Python scoring results immediately with narrative_pending=True.
    LLM narrative is generated in background and can be polled via
    GET /api/analysis/{id}/narrative.
    """
    # ─── VALIDATE FILES FIRST (before incrementing usage) ─────────────────────
    # Validate file extension
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    # Read and validate resume file size
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

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

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)

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
            
            # Create result record first for background LLM
            db_result = ScreeningResult(
                tenant_id=current_user.tenant_id,
                candidate_id=existing.id,
                resume_text=existing.raw_resume_text,
                jd_text=job_description,
                parsed_data=json.dumps(parsed_data, default=_json_default),
                analysis_result="{}",  # Placeholder
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
        parsed_data = await asyncio.to_thread(parse_resume, content, resume.filename)
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

    gap_analysis = analyze_gaps(parsed_data.get("work_experience", []))
    jd_analysis  = _get_or_cache_jd(db, job_description)

    # Create candidate and result BEFORE pipeline (for background LLM)
    candidate_id, is_dup = _get_or_create_candidate(
        db, parsed_data, current_user.tenant_id,
        file_hash=file_hash,
        gap_analysis=gap_analysis,
        profile_quality="medium",  # Will be updated
        action=action,
    )

    # Extract weight metadata from JD analysis if available
    weight_suggestion = jd_analysis.get("weight_suggestion")
    role_category = None
    weight_reasoning = None
    suggested_weights_json = None
    
    if weight_suggestion:
        role_category = weight_suggestion.get("role_category")
        weight_reasoning = weight_suggestion.get("reasoning")
        suggested_weights_json = json.dumps(weight_suggestion.get("suggested_weights", {}), default=_json_default)
    
    db_result = ScreeningResult(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        resume_text=parsed_data.get("raw_text", ""),
        jd_text=job_description,
        parsed_data=json.dumps(parsed_data, default=_json_default),
        analysis_result="{}",  # Placeholder — will be updated
        is_active=True,
        version_number=1,
        role_category=role_category,
        weight_reasoning=weight_reasoning,
        suggested_weights_json=suggested_weights_json,
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
    )
    db.commit()

    result["result_id"]    = db_result.id
    result["analysis_id"]  = db_result.id   # Add this line
    result["candidate_id"] = candidate_id

    # Resolve name: try multiple sources, skip empty strings
    _cand_row = db.get(Candidate, candidate_id)
    result["candidate_name"] = (
        (parsed_data.get("contact_info", {}).get("name") or "").strip()
        or (result.get("candidate_profile", {}).get("name") or "").strip()
        or (_cand_row.name if _cand_row and _cand_row.name else None)
        or None
    )
    
    # Add contact_info to result for PDF generation
    # This ensures email and phone are available in the frontend
    contact_info = parsed_data.get("contact_info", {})
    if contact_info:
        result["contact_info"] = {
            "name": contact_info.get("name"),
            "email": contact_info.get("email"),
            "phone": contact_info.get("phone"),
        }

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
    return result


# ─── Single resume analysis (SSE streaming) ───────────────────────────────────

@router.post("/analyze/stream")
async def analyze_stream_endpoint(
    request: Request,
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    action: str = Form(None),
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
    # ─── VALIDATE FILES FIRST (before incrementing usage) ─────────────────────
    # Validate file extension
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    # Read and validate resume file size
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

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

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception as e:
            log.warning("Non-critical: Invalid scoring_weights JSON, using defaults: %s", e)

    file_hash = hashlib.md5(content).hexdigest()
    tenant_id = current_user.tenant_id
    t_start   = time.time()

    # Parse resume and JD in thread pool before entering the generator
    try:
        parsed_data = await asyncio.to_thread(parse_resume, content, resume.filename)
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

    # Pre-create candidate and ScreeningResult BEFORE streaming
    # This gives us an ID to pass to the background LLM task
    candidate_id, is_dup = _get_or_create_candidate(
        db, parsed_data, tenant_id,
        file_hash=file_hash,
        gap_analysis=gap_analysis,
        profile_quality="medium",  # Will be updated after pipeline
        action=action,
    )
    
    # Create placeholder result to get the ID
    db_result = ScreeningResult(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        resume_text=parsed_data.get("raw_text", ""),
        jd_text=job_description,
        parsed_data=json.dumps(parsed_data, default=_json_default),
        analysis_result="{}",  # Placeholder — will be updated
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
            ):
                # Check for client disconnect between stages
                if await request.is_disconnected():
                    log.warning("Client disconnected during streaming analysis")
                    # Early DB save: ensure Python results are preserved
                    if not python_scores_saved and event.get("stage") in ("scoring", "complete"):
                        try:
                            stage_result = event.get("result", {})
                            if stage_result:
                                stage_result["result_id"] = screening_result_id
                                stage_result["candidate_id"] = candidate_id
                                db_result.analysis_result = json.dumps(stage_result, default=_json_default)
                                db.commit()
                                python_scores_saved = True
                                log.info("Early DB save completed after client disconnect")
                        except Exception as db_exc:
                            log.warning("Failed to save early DB results: %s", db_exc)
                    return

                if isinstance(event, str):
                    # SSE heartbeat ping from the generator
                    yield event
                    continue
                yield f"data: {json.dumps(event, default=_json_default)}\n\n"

                # Early DB save after Python scoring phase completes
                if event.get("stage") == "scoring":
                    try:
                        scoring_result = event.get("result", {})
                        if scoring_result:
                            scoring_result["result_id"] = screening_result_id
                            scoring_result["candidate_id"] = candidate_id
                            db_result.analysis_result = json.dumps(scoring_result, default=_json_default)
                            db.commit()
                            python_scores_saved = True
                            log.info("Early DB save completed after scoring phase")
                    except Exception as db_exc:
                        log.warning("Failed to save early DB results after scoring: %s", db_exc)

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
                (parsed_data.get("contact_info", {}).get("name") or "").strip()
                or (final_result.get("candidate_profile", {}).get("name") or "").strip()
                or (_cand_row_s.name if _cand_row_s and _cand_row_s.name else None)
                or None
            )
            
            # Add contact_info to final_result for PDF generation
            # This ensures email and phone are available in the frontend
            contact_info = parsed_data.get("contact_info", {})
            if contact_info:
                final_result["contact_info"] = {
                    "name": contact_info.get("name"),
                    "email": contact_info.get("email"),
                    "phone": contact_info.get("phone"),
                }
            
            if is_dup and action not in ("update_profile", "create_new"):
                existing = db.get(Candidate, candidate_id)
                if existing:
                    final_result["duplicate_candidate"] = _build_duplicate_info(db, existing).model_dump(mode='json')

            # Update the analysis_result column
            db_result.analysis_result = json.dumps(final_result, default=_json_default)

            # Update candidate profile quality based on analysis
            _store_candidate_profile(
                db.get(Candidate, candidate_id) or db.query(Candidate).filter(Candidate.id == candidate_id).first(),
                parsed_data,
                gap_analysis,
                file_hash,
                final_result.get("analysis_quality", "medium"),
            )
            db.commit()
        except Exception as db_exc:
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
        return await _process_single_resume(content, filename, job_description, scoring_weights, db)


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def batch_analyze_endpoint(
    resumes: list[UploadFile] = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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

    # Process all resumes with semaphore-wrapped calls for concurrency control
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
        file_hash    = hashlib.md5(content).hexdigest()

        candidate_id, _ = _get_or_create_candidate(
            db, parsed_data, current_user.tenant_id,
            file_hash=file_hash,
            gap_analysis=gap_analysis,
            profile_quality=raw.get("analysis_quality", "medium"),
        )

        db_result = ScreeningResult(
            tenant_id=current_user.tenant_id,
            candidate_id=candidate_id,
            resume_text=parsed_data.get("raw_text", ""),
            jd_text=job_description,
            parsed_data=json.dumps(parsed_data),
            analysis_result=json.dumps(raw),
        )
        db.add(db_result)
        db.flush()
        raw["result_id"] = db_result.id
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


@router.post("/analyze/batch-chunked", response_model=BatchAnalysisResponse)
async def batch_analyze_chunked_endpoint(
    upload_ids: list[str] = Form(...),
    filenames: list[str] = Form(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Batch analysis endpoint for chunked uploads.
    Reads assembled files from /tmp/aria_chunks/assembled/ and processes them.
    """
    from pathlib import Path
    
    if not upload_ids or not filenames:
        raise HTTPException(status_code=400, detail="upload_ids and filenames are required")
    
    if len(upload_ids) != len(filenames):
        raise HTTPException(status_code=400, detail="upload_ids and filenames must have the same length")
    
    # Validate batch size
    if len(upload_ids) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum batch size is {MAX_BATCH_SIZE} resumes"
        )
    
    # Read and validate JD file if provided
    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name = job_file.filename
    
    # Resolve and validate job description
    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)
    _check_jd_size(job_description)
    
    # Read assembled files from disk
    assembled_dir = Path("/tmp/aria_chunks/assembled")
    file_data = []
    
    for upload_id, filename in zip(upload_ids, filenames):
        # Construct the assembled file path
        safe_filename = f"{upload_id}_{filename}"
        file_path = assembled_dir / safe_filename
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Assembled file not found for upload {upload_id}. File may have been cleaned up."
            )
        
        # Validate file extension
        if not filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue
        
        # Read file content
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            if len(content) <= 10 * 1024 * 1024:  # Still validate individual file size
                file_data.append((content, filename))
        except Exception as e:
            log.error(f"Failed to read assembled file {file_path}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read assembled file: {filename}"
            )
    
    valid_count = len(file_data)
    
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
            detail=f"Your plan allows maximum {max_batch_size} resumes per batch. Please upgrade to process more."
        )
    
    # Check and increment usage
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
    
    # Pre-parse JD once for all resumes
    _get_or_cache_jd(db, job_description)
    
    if not file_data:
        raise HTTPException(status_code=400, detail="No valid resume files provided")
    
    # Process all resumes (same logic as regular batch endpoint)
    tasks = [
        _process_with_semaphore(content, filename, job_description, weights, db)
        for content, filename in file_data
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Separate successes from failures
    batch_results = []
    failed_items = []
    
    for raw, (content, filename) in zip(raw_results, file_data):
        if isinstance(raw, Exception):
            failed_items.append(BatchFailedItem(
                filename=filename,
                error=str(raw)
            ))
            continue
        
        parsed_data = raw.pop("_parsed_data", {})
        gap_analysis = raw.pop("_gap_analysis", {})
        file_hash = hashlib.md5(content).hexdigest()
        
        candidate_id, _ = _get_or_create_candidate(
            db, parsed_data, current_user.tenant_id,
            file_hash=file_hash,
            gap_analysis=gap_analysis,
            profile_quality=raw.get("analysis_quality", "medium"),
        )
        
        db_result = ScreeningResult(
            tenant_id=current_user.tenant_id,
            candidate_id=candidate_id,
            resume_text=parsed_data.get("raw_text", ""),
            jd_text=job_description,
            parsed_data=json.dumps(parsed_data),
            analysis_result=json.dumps(raw),
        )
        db.add(db_result)
        db.flush()
        raw["result_id"] = db_result.id
        batch_results.append({"filename": filename, "result": raw})
    
    db.commit()
    
    # Clean up assembled files after processing
    for upload_id, filename in zip(upload_ids, filenames):
        safe_filename = f"{upload_id}_{filename}"
        file_path = assembled_dir / safe_filename
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            log.warning(f"Non-critical: Failed to cleanup assembled file {file_path}: {e}")
    
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
    
    history = []
    for r in results:
        try:
            analysis = json.loads(r.analysis_result)
            parsed = json.loads(r.parsed_data)
        except Exception as e:
            logger.warning("Non-critical: Failed to parse result data for history %s: %s", r.id, e)
            analysis = {}
            parsed = {}
        
        # Resolve candidate name from multiple sources
        candidate_name = (
            (analysis.get("candidate_name") or "").strip() or
            (parsed.get("contact_info", {}).get("name") or "").strip() or
            (parsed.get("candidate_profile", {}).get("name") or "").strip() or
            None
        )
        
        # Fallback to Candidate table if available
        if not candidate_name and r.candidate_id:
            cand = db.get(Candidate, r.candidate_id)
            if cand and cand.name:
                candidate_name = cand.name
        
        history.append({
            "id":                   r.id,
            "timestamp":            r.timestamp,
            "status":               r.status,
            "candidate_id":         r.candidate_id,
            "candidate_name":       candidate_name or f"Result #{r.id}",
            "job_role":             analysis.get("job_role"),
            "fit_score":            analysis.get("fit_score"),
            "final_recommendation": analysis.get("final_recommendation"),
            "risk_level":           analysis.get("risk_level"),
        })
    
    return history


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
    db.commit()
    return {"id": result_id, "status": new_status}


# ─── Weight suggestion endpoint ──────────────────────────────────────────────

@router.post("/analyze/suggest-weights")
async def suggest_weights(
    job_description: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """
    Suggest optimal scoring weights based on job description analysis.
    
    This endpoint analyzes the JD and returns AI-suggested weights without
    performing a full resume analysis. Frontend can use this to show suggested
    weights before the user uploads a resume.
    
    Returns:
        {
            "role_category": "technical|sales|hr|marketing|etc",
            "seniority_level": "junior|mid|senior|lead|executive",
            "suggested_weights": {...},
            "role_excellence_label": "...",
            "reasoning": "...",
            "confidence": 0.0-1.0
        }
    """
    from app.backend.services.weight_suggester import suggest_weights_for_jd, create_fallback_suggestion
    
    # Validate JD length
    if not job_description or len(job_description.strip()) < 50:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short. Please provide at least 50 characters."
        )
    
    if len(job_description.split()) < 80:
        raise HTTPException(
            status_code=400,
            detail="Job description is too brief (under 80 words). Please include role details for accurate weight suggestions."
        )
    
    # Get weight suggestions from LLM
    try:
        suggestion = suggest_weights_for_jd(job_description, timeout=30)
        
        if suggestion:
            return suggestion
        else:
            # LLM failed, return fallback
            log.warning("LLM weight suggestion failed, using fallback")
            return create_fallback_suggestion(job_description)
            
    except Exception as e:
        log.exception(f"Error in weight suggestion endpoint: {e}")
        # Return fallback on error
        return create_fallback_suggestion(job_description)


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
      - {"status": "ready", "narrative": {...}, "generated_at": "..."} if narrative is available
      - {"status": "processing"} if LLM is currently generating
      - {"status": "pending"} if LLM hasn't started yet
      - {"status": "failed", "error": "...", "narrative": {...}, "generated_at": "..."} if LLM failed (includes fallback)
      - 404 if analysis not found or not owned by user's tenant
    """
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == analysis_id,
        ScreeningResult.tenant_id == current_user.tenant_id,
    ).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Use narrative_status column if available, fall back to checking narrative_json
    status = getattr(result, 'narrative_status', None) or 'pending'
    
    # Get timestamp if available
    generated_at = None
    if hasattr(result, 'narrative_generated_at') and result.narrative_generated_at:
        generated_at = result.narrative_generated_at.isoformat()
    
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
            "generated_at": generated_at,
        }
    
    if status == 'ready' or (status is None and result.narrative_json):
        # Ready — return narrative
        if result.narrative_json:
            try:
                narrative = json.loads(result.narrative_json)
                return {
                    "status": "ready",
                    "narrative": narrative,
                    "generated_at": generated_at,
                }
            except json.JSONDecodeError:
                return {"status": "pending"}
    
    # Return current status (pending or processing)
    return {"status": status}
