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
from sqlalchemy import update

from app.backend.db.database import get_db, SessionLocal
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User, Candidate, JdCache, Tenant, SubscriptionPlan
from app.backend.models.schemas import (
    AnalysisResponse, BatchAnalysisResponse, BatchAnalysisResult,
    BatchFailedItem, BatchStreamEvent,
    DuplicateCandidateInfo,
)
from app.backend.services.parser_service import parse_resume, extract_jd_text
from app.backend.services.doc_converter import convert_to_pdf
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.hybrid_pipeline import (
    run_hybrid_pipeline,
    astream_hybrid_pipeline,
    parse_jd_rules,
    shutdown_background_tasks,
)
from app.backend.routes.subscription import _ensure_monthly_reset, _get_plan_limits, record_usage
from app.backend.services.billing.quota import check_quota

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
    """Handle non-serializable types for json.dumps (datetime, date, Decimal)."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ─── JD cache helpers ─────────────────────────────────────────────────────────

def _get_or_cache_jd(db: Session, job_description: str) -> dict:
    """Parse the JD or return the cached result. Shared across all workers via DB."""
    jd_hash = hashlib.md5(job_description[:2000].encode()).hexdigest()
    cached = db.query(JdCache).filter(JdCache.hash == jd_hash).first()
    if cached:
        try:
            return json.loads(cached.result_json)
        except Exception as e:
            log.warning("Non-critical: Failed to parse cached JD JSON, re-parsing: %s", e)
    jd_analysis = parse_jd_rules(job_description)
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
    """Core analysis logic — parse in thread, run hybrid pipeline, return result."""
    # Parse resume in thread pool (blocks event loop otherwise for large PDFs)
    try:
        parsed_data, _ = await _parse_resume_with_doc_conversion(content, filename)
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
    action: str = Form(None),   # use_existing | update_profile | create_new | None
    template_id: Optional[int] = Form(None),
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
    action: str = Form(None),
    template_id: Optional[int] = Form(None),
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

    # Process all resumes with semaphore-wrapped calls
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
            )
            db.add(db_result)
            db.flush()
            db.commit()
            raw["result_id"] = db_result.id
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
        await asyncio.sleep(0.3 * index)  # Stagger to avoid LLM thundering herd
        result = await _process_with_semaphore(content, filename, jd, weights, db_session)
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
                )
                save_db.add(db_result)
                save_db.commit()
                save_db.refresh(db_result)

                screening_result_id = db_result.id
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
        return await _process_single_resume(content, filename, job_description, scoring_weights, db)


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
