import json
import asyncio
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.backend.db.database import get_db
from app.backend.middleware.auth import get_current_user
from app.backend.models.db_models import ScreeningResult, User, Candidate
from app.backend.models.schemas import AnalysisResponse, BatchAnalysisResponse, BatchAnalysisResult
from app.backend.services.parser_service import parse_resume
from app.backend.services.gap_detector import analyze_gaps
from app.backend.services.agent_pipeline import run_agent_pipeline

router = APIRouter(prefix="/api", tags=["analysis"])

ALLOWED_EXTENSIONS     = ('.pdf', '.docx', '.doc')
ALLOWED_JD_EXTENSIONS  = ('.docx',)


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


async def _process_single_resume(
    content: bytes,
    filename: str,
    job_description: str,
    scoring_weights: dict | None,
) -> dict:
    """Core analysis logic extracted for reuse in batch."""
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
        result = {
            "fit_score": 50,
            "strengths": ["Analysis service temporarily unavailable"],
            "weaknesses": ["Unable to complete full analysis"],
            "employment_gaps": gap_analysis.get("employment_gaps", []),
            "education_analysis": "Analysis unavailable at this time.",
            "risk_signals": [f"Pipeline error: {str(e)}"],
            "final_recommendation": "Consider",
            "score_breakdown": {},
            "matched_skills": [],
            "missing_skills": [],
            "risk_level": "Unknown",
            "required_skills_count": 0,
            "interview_questions": None,
        }
    result["_parsed_data"] = parsed_data
    return result


# ─── Single resume analysis ───────────────────────────────────────────────────

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

    if not job_description and not job_file:
        raise HTTPException(status_code=400, detail="Job description (text or file) is required")

    content = await resume.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Resume file too large (max 10MB)")

    if job_file and job_file.filename:
        if not job_file.filename.lower().endswith(ALLOWED_JD_EXTENSIONS):
            raise HTTPException(status_code=400, detail="Job description file must be a .docx file")
        try:
            jd_content = await job_file.read()
            if len(jd_content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Job description file too large (max 5MB)")
            jd_parsed = parse_resume(jd_content, job_file.filename)
            job_description = jd_parsed["raw_text"]
        except HTTPException:
            raise
        except Exception as e:
            # If text was also provided, fall back to it rather than hard-failing
            if job_description and job_description.strip():
                pass  # use the text JD that was sent alongside the file
            else:
                raise HTTPException(status_code=422, detail=f"Failed to parse job description file: {str(e)}")

    weights = None
    if scoring_weights:
        try:
            weights = json.loads(scoring_weights)
        except Exception:
            pass

    result = await _process_single_resume(content, resume.filename, job_description, weights)
    parsed_data = result.pop("_parsed_data", {})

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

    result["result_id"] = db_result.id
    return result


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
    if not job_description and not job_file:
        raise HTTPException(status_code=400, detail="Job description (text or file) is required")

    if job_file and job_file.filename:
        if not job_file.filename.lower().endswith(ALLOWED_JD_EXTENSIONS):
            raise HTTPException(status_code=400, detail="Job description file must be a .docx file")
        try:
            jd_content = await job_file.read()
            jd_parsed  = parse_resume(jd_content, job_file.filename)
            job_description = jd_parsed["raw_text"]
        except HTTPException:
            raise
        except Exception as e:
            if job_description and job_description.strip():
                pass
            else:
                raise HTTPException(status_code=422, detail=f"Failed to parse job description: {str(e)}")

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

    # Process all resumes in parallel
    tasks = [
        _process_single_resume(content, filename, job_description, weights)
        for content, filename in file_data
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Save and rank
    batch_results = []
    for i, (raw, (_, filename)) in enumerate(zip(raw_results, file_data)):
        if isinstance(raw, Exception):
            continue
        parsed_data  = raw.pop("_parsed_data", {})
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

    # Sort by fit_score descending and assign rank
    batch_results.sort(key=lambda x: x["result"].get("fit_score", 0), reverse=True)
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
