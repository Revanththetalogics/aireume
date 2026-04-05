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
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User, Candidate, JdCache, Tenant, SubscriptionPlan
from app.backend.models.schemas import (
    AnalysisResponse, BatchAnalysisResponse, BatchAnalysisResult,
    DuplicateCandidateInfo,
)
from app.backend.services.parser_service import parse_resume, extract_jd_text
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.hybrid_pipeline import (
    run_hybrid_pipeline,
    astream_hybrid_pipeline,
    parse_jd_rules,
)
from app.backend.routes.subscription import _ensure_monthly_reset, _get_plan_limits, record_usage

router = APIRouter(prefix="/api", tags=["analysis"])
log    = logging.getLogger("aria.analysis")

ALLOWED_EXTENSIONS = ('.pdf', '.docx', '.doc')


# ─── JD cache helpers ─────────────────────────────────────────────────────────

def _get_or_cache_jd(db: Session, job_description: str) -> dict:
    """Parse the JD or return the cached result. Shared across all workers via DB."""
    jd_hash = hashlib.md5(job_description[:2000].encode()).hexdigest()
    cached = db.query(JdCache).filter(JdCache.hash == jd_hash).first()
    if cached:
        try:
            return json.loads(cached.result_json)
        except Exception:
            pass
    jd_analysis = parse_jd_rules(job_description)
    try:
        db.merge(JdCache(hash=jd_hash, result_json=json.dumps(jd_analysis)))
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
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
        except Exception:
            pass

    return DuplicateCandidateInfo(
        id=candidate.id,
        name=candidate.name,
        email=candidate.email,
        current_role=candidate.current_role,
        current_company=candidate.current_company,
        total_years_exp=candidate.total_years_exp,
        skills_snapshot=skills_snapshot,
        result_count=result_count,
        last_analyzed=last_result.timestamp if last_result else None,
        profile_quality=candidate.profile_quality,
    )


_SNAPSHOT_JSON_MAX = 500_000  # bytes of UTF-8 JSON; keeps row size bounded


def _parser_snapshot_json(parsed_data: dict) -> str | None:
    """Serialize full parser output so DB retains every field (not only pattern-derived columns)."""
    try:
        s = json.dumps(parsed_data, ensure_ascii=False)
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
    candidate.parsed_skills      = json.dumps(parsed_data.get("skills", []))
    candidate.parsed_education   = json.dumps(parsed_data.get("education", []))
    candidate.parsed_work_exp    = json.dumps(work_exp)
    candidate.gap_analysis_json  = json.dumps(gap_analysis)
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
        except Exception:
            pass
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
        except Exception:
            pass

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
        result = _fallback_result(gap_analysis)
        result["pipeline_errors"] = [f"Pipeline error: {str(e)}"]

    result["_parsed_data"]  = parsed_data
    result["_gap_analysis"] = gap_analysis
    return result


# ─── Single resume analysis (non-streaming, JSON response) ────────────────────

def _check_and_increment_usage(db: Session, tenant_id: int, user_id: int, quantity: int = 1) -> tuple[bool, str]:
    """Check usage limits and increment counter. Returns (allowed, message)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return False, "Tenant not found"
    
    # Ensure monthly reset
    _ensure_monthly_reset(tenant)
    
    # Get plan limits
    plan = tenant.plan
    if not plan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "free").first()
    
    if plan:
        limits = _get_plan_limits(plan)
        analyses_limit = limits.get("analyses_per_month", 20)
        
        if analyses_limit >= 0:  # Not unlimited
            if tenant.analyses_count_this_month + quantity > analyses_limit:
                remaining = analyses_limit - tenant.analyses_count_this_month
                return False, f"Monthly analysis limit exceeded. Remaining: {remaining}, Requested: {quantity}. Please upgrade your plan."
    
    # Increment and log
    success = record_usage(db, tenant_id, user_id, "resume_analysis", quantity)
    if not success:
        return False, "Failed to record usage"
    
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
    # Check usage limits before processing
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, 1)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)
    
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        if len(jd_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Job description file too large (max 5MB)")
        jd_name = job_file.filename

    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

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
            result = await run_hybrid_pipeline(
                resume_text=existing.raw_resume_text,
                job_description=job_description,
                parsed_data=parsed_data,
                gap_analysis=gap_analysis,
                scoring_weights=weights,
                jd_analysis=jd_analysis,
            )
            # Save new screening result
            db_result = ScreeningResult(
                tenant_id=current_user.tenant_id,
                candidate_id=existing.id,
                resume_text=existing.raw_resume_text,
                jd_text=job_description,
                parsed_data=json.dumps(parsed_data),
                analysis_result=json.dumps(result),
            )
            db.add(db_result)
            db.commit()
            db.refresh(db_result)
            result["result_id"]      = db_result.id
            result["candidate_id"]   = existing.id
            result["candidate_name"] = existing.name
            return result

    t_start = time.time()
    result      = await _process_single_resume(content, resume.filename, job_description, weights, db)
    parsed_data = result.pop("_parsed_data", {})
    gap_analysis = result.pop("_gap_analysis", {})

    candidate_id, is_dup = _get_or_create_candidate(
        db, parsed_data, current_user.tenant_id,
        file_hash=file_hash,
        gap_analysis=gap_analysis,
        profile_quality=result.get("analysis_quality", "medium"),
        action=action,
    )

    db_result = ScreeningResult(
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
        resume_text=parsed_data.get("raw_text", ""),
        jd_text=job_description,
        parsed_data=json.dumps(parsed_data),
        analysis_result=json.dumps(result),
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    result["result_id"]    = db_result.id
    result["candidate_id"] = candidate_id

    # Resolve name: try multiple sources, skip empty strings
    _cand_row = db.get(Candidate, candidate_id)
    result["candidate_name"] = (
        (parsed_data.get("contact_info", {}).get("name") or "").strip()
        or (result.get("candidate_profile", {}).get("name") or "").strip()
        or (_cand_row.name if _cand_row and _cand_row.name else None)
        or None
    )

    if is_dup and action not in ("update_profile", "create_new"):
        existing = db.get(Candidate, candidate_id)
        if existing:
            result["duplicate_candidate"] = _build_duplicate_info(db, existing)

    log.info(json.dumps({
        "event":       "analysis_complete",
        "tenant_id":   current_user.tenant_id,
        "filename":    resume.filename,
        "skills_found": len(result.get("matched_skills", [])),
        "fit_score":   result.get("fit_score"),
        "llm_used":    not result.get("narrative_pending", False),
        "quality":     result.get("analysis_quality"),
        "total_ms":    int((time.time() - t_start) * 1000),
    }))
    return result


# ─── Single resume analysis (SSE streaming) ───────────────────────────────────

@router.post("/analyze/stream")
async def analyze_stream_endpoint(
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

    Emits:
      data: {"stage": "parsing",  "result": {...Python scores...}}   — within 2s
      data: {"stage": "scoring",  "result": {...LLM narrative...}}   — after ~40s
      data: {"stage": "complete", "result": {...full result...}}
      data: [DONE]
    """
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name  = job_file.filename

    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

    file_hash = hashlib.md5(content).hexdigest()
    tenant_id = current_user.tenant_id
    t_start   = time.time()

    # Parse resume and JD in thread pool before entering the generator
    try:
        parsed_data = await asyncio.to_thread(parse_resume, content, resume.filename)
    except Exception as e:
        async def _error_stream():
            error = {"stage": "error", "result": {"message": str(e)}}
            yield f"data: {json.dumps(error)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(_error_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    gap_analysis = analyze_gaps(parsed_data.get("work_experience", []))
    jd_analysis  = _get_or_cache_jd(db, job_description)

    async def event_stream():
        final_result: dict = {}

        try:
            async for event in astream_hybrid_pipeline(
                resume_text=parsed_data["raw_text"],
                job_description=job_description,
                parsed_data=parsed_data,
                gap_analysis=gap_analysis,
                scoring_weights=weights,
                jd_analysis=jd_analysis,
            ):
                if isinstance(event, str):
                    # SSE heartbeat ping from the generator
                    yield event
                    continue
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("stage") == "complete":
                    final_result = event.get("result", {})
        except Exception as exc:
            error_event = {"stage": "error", "result": {"message": str(exc)}}
            yield f"data: {json.dumps(error_event)}\n\n"
            final_result = _fallback_result(gap_analysis)

        # Persist to DB
        try:
            candidate_id, is_dup = _get_or_create_candidate(
                db, parsed_data, tenant_id,
                file_hash=file_hash,
                gap_analysis=gap_analysis,
                profile_quality=final_result.get("analysis_quality", "medium"),
                action=action,
            )
            db_result = ScreeningResult(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                resume_text=parsed_data.get("raw_text", ""),
                jd_text=job_description,
                parsed_data=json.dumps(parsed_data),
                analysis_result=json.dumps(final_result),
            )
            db.add(db_result)
            db.commit()
            db.refresh(db_result)

            final_result["result_id"]    = db_result.id
            final_result["candidate_id"] = candidate_id
            _cand_row_s = db.get(Candidate, candidate_id)
            final_result["candidate_name"] = (
                (parsed_data.get("contact_info", {}).get("name") or "").strip()
                or (final_result.get("candidate_profile", {}).get("name") or "").strip()
                or (_cand_row_s.name if _cand_row_s and _cand_row_s.name else None)
                or None
            )
            if is_dup and action not in ("update_profile", "create_new"):
                existing = db.get(Candidate, candidate_id)
                if existing:
                    final_result["duplicate_candidate"] = _build_duplicate_info(db, existing).model_dump()
        except Exception as db_exc:
            final_result["pipeline_errors"] = final_result.get("pipeline_errors", []) + [
                f"DB save error: {str(db_exc)}"
            ]

        log.info(json.dumps({
            "event":       "analysis_complete",
            "tenant_id":   tenant_id,
            "filename":    resume.filename,
            "fit_score":   final_result.get("fit_score"),
            "llm_used":    not final_result.get("narrative_pending", False),
            "quality":     final_result.get("analysis_quality"),
            "total_ms":    int((time.time() - t_start) * 1000),
        }))

        complete_payload = {"stage": "complete", "result": final_result}
        yield f"data: {json.dumps(complete_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─── Batch resume analysis ────────────────────────────────────────────────────

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
    
    # Filter valid resumes first to get accurate count
    valid_count = sum(
        1 for f in resumes 
        if f.filename.lower().endswith(ALLOWED_EXTENSIONS)
    )
    
    # Get tenant's plan for batch size limit
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    max_batch_size = 50  # default
    if tenant and tenant.plan:
        limits = _get_plan_limits(tenant.plan)
        plan_batch_limit = limits.get("batch_size", 50)
        max_batch_size = min(max_batch_size, plan_batch_limit)
    
    if valid_count > max_batch_size:
        raise HTTPException(
            status_code=400, 
            detail=f"Your plan allows maximum {max_batch_size} resumes per batch. Please upgrade to process more."
        )
    
    # Check usage limits for batch
    allowed, message = _check_and_increment_usage(db, current_user.tenant_id, current_user.id, valid_count)
    if not allowed:
        raise HTTPException(status_code=429, detail=message)

    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name  = job_file.filename

    job_description = _resolve_jd(job_description, jd_bytes, jd_name)
    _check_jd_length(job_description)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

    # Pre-parse JD once for all resumes in this batch
    _get_or_cache_jd(db, job_description)

    file_data = []
    for f in resumes:
        if not f.filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue
        content = await f.read()
        if len(content) <= 10 * 1024 * 1024:
            file_data.append((content, f.filename))

    if not file_data:
        raise HTTPException(status_code=400, detail="No valid resume files provided")

    tasks = [
        _process_single_resume(content, filename, job_description, weights, db)
        for content, filename in file_data
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    batch_results = []
    for raw, (content, filename) in zip(raw_results, file_data):
        if isinstance(raw, Exception):
            continue
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

    batch_results.sort(key=lambda x: x["result"].get("fit_score") or 0, reverse=True)
    ranked = [
        BatchAnalysisResult(rank=i + 1, filename=r["filename"], result=r["result"])
        for i, r in enumerate(batch_results)
    ]
    return BatchAnalysisResponse(results=ranked, total=len(ranked))


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
    return [
        {
            "id":                   r.id,
            "timestamp":            r.timestamp,
            "status":               r.status,
            "candidate_id":         r.candidate_id,
            "fit_score":            json.loads(r.analysis_result).get("fit_score"),
            "final_recommendation": json.loads(r.analysis_result).get("final_recommendation"),
            "risk_level":           json.loads(r.analysis_result).get("risk_level"),
        }
        for r in results
    ]


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
