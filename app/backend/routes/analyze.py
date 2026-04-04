import json
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User, Candidate
from app.backend.models.schemas import AnalysisResponse, BatchAnalysisResponse, BatchAnalysisResult
from app.backend.services.parser_service import parse_resume, extract_jd_text
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.agent_pipeline import (
    run_agent_pipeline,
    pipeline,
    STREAMABLE_NODES,
    build_initial_state,
    assemble_result,
)

router = APIRouter(prefix="/api", tags=["analysis"])

ALLOWED_EXTENSIONS = ('.pdf', '.docx', '.doc')


def _get_or_create_candidate(db: Session, parsed_data: dict, tenant_id: int) -> int | None:
    """Find existing candidate by email or create a new one."""
    contact = parsed_data.get("contact_info", {})
    email   = contact.get("email")
    name    = contact.get("name")
    phone   = contact.get("phone")

    if email:
        candidate = db.query(Candidate).filter(
            Candidate.email == email,
            Candidate.tenant_id == tenant_id
        ).first()
        if candidate:
            return candidate.id

    candidate = Candidate(
        tenant_id=tenant_id,
        name=name,
        email=email,
        phone=phone,
    )
    db.add(candidate)
    db.flush()
    return candidate.id


def _fallback_result(gap_analysis: dict) -> dict:
    """Return safe null-state result when the entire pipeline fails."""
    return {
        "fit_score": None,
        "job_role": None,
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
    }


async def _process_single_resume(
    content: bytes,
    filename: str,
    job_description: str,
    scoring_weights: dict | None,
) -> dict:
    """Core analysis logic used by non-streaming single and batch endpoints."""
    parsed_data  = parse_resume(content, filename)
    work_exp     = parsed_data.get("work_experience", [])
    gap_analysis = analyze_gaps(work_exp)

    try:
        result = await run_agent_pipeline(
            resume_text=parsed_data["raw_text"],
            job_description=job_description,
            parsed_data=parsed_data,
            gap_analysis=gap_analysis,
            scoring_weights=scoring_weights,
        )
    except Exception as e:
        result = _fallback_result(gap_analysis)
        result["pipeline_errors"] = [f"Pipeline error: {str(e)}"]

    result["_parsed_data"]  = parsed_data
    result["_gap_analysis"] = gap_analysis
    return result


def _resolve_jd(
    job_description: str | None,
    job_file_bytes: bytes | None,
    job_filename: str | None,
) -> str:
    """Extract JD text from file bytes if provided, otherwise use raw text."""
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


# ─── Single resume analysis (non-streaming, JSON response) ────────────────────

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

    result      = await _process_single_resume(content, resume.filename, job_description, weights)
    parsed_data = result.pop("_parsed_data", {})
    result.pop("_gap_analysis", None)

    candidate_id = _get_or_create_candidate(db, parsed_data, current_user.tenant_id)

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

    result["result_id"]      = db_result.id
    result["candidate_id"]   = candidate_id
    result["candidate_name"] = parsed_data.get("contact_info", {}).get("name")
    return result


# ─── Single resume analysis (SSE streaming) ───────────────────────────────────

@router.post("/analyze/stream")
async def analyze_stream_endpoint(
    resume: UploadFile = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    SSE streaming version of /analyze.

    Emits events:
      data: {"stage": "<node_name>", "result": {...}}   — after each node completes
      data: {"stage": "complete", "result": {...}}       — full assembled result + result_id
      data: [DONE]                                       — stream end marker
    """
    if not resume.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=400, detail=f"Only {ALLOWED_EXTENSIONS} files are allowed")

    # Eager reads — must happen BEFORE returning StreamingResponse
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name  = job_file.filename

    job_description = _resolve_jd(job_description, jd_bytes, jd_name)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

    # Mechanical pre-processing (instant)
    parsed_data  = parse_resume(content, resume.filename)
    gap_analysis = analyze_gaps(parsed_data.get("work_experience", []))
    initial_state = build_initial_state(
        parsed_data["raw_text"], job_description, gap_analysis, weights
    )

    # Capture for use inside the generator closure
    tenant_id = current_user.tenant_id

    async def event_stream():
        accumulated: dict = {}   # accumulate node outputs to reconstruct final state

        try:
            async for event in pipeline.astream_events(initial_state, version="v2"):
                event_type = event.get("event", "")
                node_name  = (
                    event.get("metadata", {}).get("langgraph_node")
                    or event.get("name", "")
                )

                if event_type == "on_chain_end" and node_name in STREAMABLE_NODES:
                    node_output = event.get("data", {}).get("output", {})
                    accumulated.update(node_output)
                    payload = {"stage": node_name, "result": node_output}
                    yield f"data: {json.dumps(payload)}\n\n"

        except Exception as exc:
            error_payload = {"stage": "error", "result": {"message": str(exc)}}
            yield f"data: {json.dumps(error_payload)}\n\n"

        # Assemble final result from accumulated state
        final_state = {**initial_state, **accumulated}
        try:
            result = assemble_result(final_state, parsed_data, gap_analysis)
        except Exception:
            result = _fallback_result(gap_analysis)

        # Persist to DB
        try:
            candidate_id = _get_or_create_candidate(db, parsed_data, tenant_id)
            db_result = ScreeningResult(
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                resume_text=parsed_data.get("raw_text", ""),
                jd_text=job_description,
                parsed_data=json.dumps(parsed_data),
                analysis_result=json.dumps(result),
            )
            db.add(db_result)
            db.commit()
            db.refresh(db_result)

            result["result_id"]      = db_result.id
            result["candidate_id"]   = candidate_id
            result["candidate_name"] = parsed_data.get("contact_info", {}).get("name")
        except Exception as db_exc:
            result["pipeline_errors"] = result.get("pipeline_errors", []) + [
                f"DB save error: {str(db_exc)}"
            ]

        complete_payload = {"stage": "complete", "result": result}
        yield f"data: {json.dumps(complete_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering for SSE
        },
    )


# ─── Batch resume analysis ────────────────────────────────────────────────────

@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def batch_analyze_endpoint(
    resumes: list[UploadFile] = File(...),
    job_description: str = Form(None),
    job_file: UploadFile = File(None),
    scoring_weights: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume required")
    if len(resumes) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 resumes per batch")

    jd_bytes = jd_name = None
    if job_file and job_file.filename:
        jd_bytes = await job_file.read()
        jd_name  = job_file.filename

    job_description = _resolve_jd(job_description, jd_bytes, jd_name)

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

    # Read all file contents before async scatter
    file_data = []
    for f in resumes:
        if not f.filename.lower().endswith(ALLOWED_EXTENSIONS):
            continue
        content = await f.read()
        if len(content) <= 10 * 1024 * 1024:
            file_data.append((content, f.filename))

    if not file_data:
        raise HTTPException(status_code=400, detail="No valid resume files provided")

    # Process all resumes concurrently
    tasks = [
        _process_single_resume(content, filename, job_description, weights)
        for content, filename in file_data
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Save and rank
    batch_results = []
    for raw, (_, filename) in zip(raw_results, file_data):
        if isinstance(raw, Exception):
            continue
        parsed_data  = raw.pop("_parsed_data", {})
        raw.pop("_gap_analysis", None)
        candidate_id = _get_or_create_candidate(db, parsed_data, current_user.tenant_id)

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

    # Sort by fit_score descending, assign rank
    batch_results.sort(
        key=lambda x: x["result"].get("fit_score") or 0, reverse=True
    )
    ranked = [
        BatchAnalysisResult(rank=i + 1, filename=r["filename"], result=r["result"])
        for i, r in enumerate(batch_results)
    ]

    return BatchAnalysisResponse(results=ranked, total=len(ranked))


# ─── History ──────────────────────────────────────────────────────────────────

@router.get("/history")
def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
):
    result = db.query(ScreeningResult).filter(
        ScreeningResult.id == result_id,
        ScreeningResult.tenant_id == current_user.tenant_id
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
